"""Payroll blueprint — salary config, reports, payslips, hikes, bonuses."""
import calendar
import csv
import datetime
import html as _html
import io
import openpyxl
import os

from flask import (Blueprint, session, request, redirect, render_template,
                   flash, url_for, jsonify, send_file, abort, Response)

from extensions import app_log
from database import get_db_connection
from utils.auth import admin_required, employee_required, api_required, employee_api_required
from utils.helpers import (_audit, get_company_settings, decrypt_pii, _db)
from utils.email_utils import get_email_config, send_email_smtp, send_email_async
from utils.attendance_utils import (
    infer_type_legacy, fetch_holidays_set, get_working_days, get_billable_past_days,
)
from utils.config import (load_salary_rules, load_default_shift,
                          LATE_DEDUCTION_RATE, HALF_DAY_RATE,
                          HOLIDAY_PAY, LEAVE_PAY)

payroll_bp = Blueprint("payroll", __name__)

_VALID_CFS_COLS = frozenset({
    "face_auth_enabled", "geo_enabled", "geo_radius", "qr_enabled", "pin_enabled",
    "fingerprint_enabled", "biometric_enabled", "notify_leave", "notify_payslip",
    "notify_resignation", "notify_doc_expiry", "session_timeout",
    "late_deduction_pct", "half_day_deduction_pct", "grace_minutes",
    "shift_start", "shift_half", "shift_end", "holiday_pay", "leave_pay",
})

def _upsert_co_features(company_id, fields_dict):
    """Insert or update multiple fields in company_feature_settings."""
    if not company_id or not fields_dict:
        return
    if not all(k in _VALID_CFS_COLS for k in fields_dict.keys()):
        app_log.error("_upsert_co_features: rejected unknown columns %s", list(fields_dict.keys()))
        return
    try:
        cols   = ", ".join(fields_dict.keys())
        vals   = list(fields_dict.values())
        placeholders = ", ".join(["%s"] * len(vals))
        updates = ", ".join(f"{k}=EXCLUDED.{k}" for k in fields_dict.keys())
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute(f"""
            INSERT INTO company_feature_settings (company_id, {cols})
            VALUES (%s, {placeholders})
            ON CONFLICT (company_id) DO UPDATE SET {updates}
        """, [company_id] + vals)
        db.commit(); cur.close(); db.close()
    except Exception:
        pass


def build_salary_slip_html(emp_name, emp_id, emp_email, month_name, year, month, salary_data,
                           company_name="", emp_designation="", emp_dept="",
                           pan="", uan="", bank_account="", bank_name="",
                           payroll_cfg=None):
    e = salary_data
    pc = payroll_cfg or {}

    # ── Salary structure ──────────────────────────────────────────
    monthly_ctc  = float(e.get("monthly_ctc", 0))
    basic_pct    = int(e.get("basic_pct", 50))
    if monthly_ctc <= 0 and float(e.get("spd", 0)) > 0:
        monthly_ctc = round(float(e["spd"]) * 26, 2)

    basic        = round(monthly_ctc * basic_pct / 100, 2)
    hra          = round(monthly_ctc * 0.20, 2)
    # Cap conveyance so gross never exceeds CTC
    conveyance   = round(min(1600.0, max(0, monthly_ctc - basic - hra)), 2)
    special_all  = round(max(0, monthly_ctc - basic - hra - conveyance), 2)
    gross_salary = round(basic + hra + conveyance + special_all, 2)

    # ── LOP: standard 26-day denominator (Indian payroll norm) ───
    full_d  = int(e.get("full_days", 0))
    late_d  = int(e.get("late_days", 0))
    half_d  = int(e.get("half_days", 0))
    lop_days     = float(e.get("absent", 0))
    paid_days_display = full_d + late_d + half_d   # integer count for display
    lop_ded      = round(gross_salary / 26 * lop_days, 2)
    gross_earned = round(gross_salary - lop_ded, 2)

    # ── Statutory deductions ─────────────────────────────────────
    pf_pct        = float(pc.get("pf_employee_pct", 12))
    pf_er_pct     = float(pc.get("pf_employer_pct", 12))
    pf_cap_basic  = float(pc.get("pf_basic_cap", 15000))
    pt_monthly    = float(pc.get("professional_tax", 200))
    tds_ann_pct   = float(pc.get("tds_annual_pct", 0))

    # PF on capped basic; TDS = annual taxable (CTC×12) × rate ÷ 12
    pf_ded        = round(min(basic, pf_cap_basic) * pf_pct / 100, 2)
    pf_er_ded     = round(min(basic, pf_cap_basic) * pf_er_pct / 100, 2)
    annual_ctc    = monthly_ctc * 12
    tds_ded       = round(annual_ctc * tds_ann_pct / 100 / 12, 2)
    # Cap statutory deductions to gross earned (net cannot go below 0)
    stat_ded      = pf_ded + pt_monthly + tds_ded
    if stat_ded > gross_earned:
        ratio     = gross_earned / stat_ded if stat_ded > 0 else 0
        pf_ded    = round(pf_ded * ratio, 2)
        pt_monthly = round(pt_monthly * ratio, 2)
        tds_ded   = round(tds_ded * ratio, 2)
    total_ded     = round(lop_ded + pf_ded + pt_monthly + tds_ded, 2)
    net_pay       = max(0, round(gross_earned - pf_ded - pt_monthly - tds_ded, 2))

    emp_row_extra = ""
    if emp_designation: emp_row_extra += f"<tr><td>Designation</td><td>{_html.escape(str(emp_designation))}</td></tr>"
    if emp_dept:        emp_row_extra += f"<tr><td>Department</td><td>{_html.escape(str(emp_dept))}</td></tr>"
    if pan:             emp_row_extra += f"<tr><td>PAN</td><td>{_html.escape(str(pan))}</td></tr>"
    if uan:             emp_row_extra += f"<tr><td>UAN</td><td>{_html.escape(str(uan))}</td></tr>"
    if bank_account:
        masked = '*'*len(bank_account[:-4]) + bank_account[-4:]
        emp_row_extra += f"<tr><td>Bank A/C</td><td>{_html.escape(masked)}</td></tr>"
    if bank_name:       emp_row_extra += f"<tr><td>Bank</td><td>{_html.escape(str(bank_name))}</td></tr>"

    incentive_row = ""
    if e.get("incentive", 0) > 0:
        incentive_row = f'<tr><td>Incentive / Bonus</td><td class="green">+ Rs. {e["incentive"]:.2f}</td><td></td><td></td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:"Segoe UI",Arial,sans-serif;background:#f0f4ff;color:#1e293b}}
  .wrap{{max-width:800px;margin:20px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.12)}}
  .hdr{{background:linear-gradient(135deg,#0f2460,#1e3a8a);padding:28px 32px;color:#fff;display:flex;justify-content:space-between;align-items:center}}
  .hdr-left h1{{font-size:20px;font-weight:800;margin-bottom:4px}}
  .hdr-left p{{font-size:13px;opacity:.75}}
  .hdr-right{{text-align:right}}
  .hdr-right .slip-num{{font-size:12px;opacity:.7;margin-bottom:4px}}
  .hdr-right .month{{font-size:18px;font-weight:700}}
  .emp-bar{{background:#dbeafe;padding:16px 32px;display:grid;grid-template-columns:1fr 1fr;gap:4px 40px;font-size:13px}}
  .emp-bar td:first-child{{font-weight:700;color:#1e3a8a;white-space:nowrap}}
  .emp-bar td{{padding:3px 6px;color:#1e293b}}
  .att-strip{{display:grid;grid-template-columns:repeat(6,1fr);gap:0;border-bottom:1px solid #e2e8f0}}
  .att-cell{{text-align:center;padding:14px 8px;border-right:1px solid #e2e8f0}}
  .att-cell:last-child{{border-right:none}}
  .att-cell .num{{font-size:22px;font-weight:800}}
  .att-cell .lbl{{font-size:10px;color:#64748b;margin-top:2px;text-transform:uppercase;letter-spacing:.3px}}
  .body{{padding:24px 32px}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:16px}}
  .sec-title{{font-size:12px;font-weight:800;color:#1e3a8a;text-transform:uppercase;letter-spacing:.5px;padding-bottom:7px;border-bottom:2px solid #dbeafe;margin-bottom:10px}}
  table.pay-tbl{{width:100%;border-collapse:collapse;font-size:13px}}
  table.pay-tbl td{{padding:7px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
  table.pay-tbl td:last-child{{text-align:right;font-weight:600;white-space:nowrap}}
  table.pay-tbl tr.tot td{{background:#f8fafc;font-weight:800;border-top:2px solid #dbeafe;border-bottom:2px solid #dbeafe;font-size:14px}}
  .net-box{{background:linear-gradient(135deg,#0f2460,#1e3a8a);color:#fff;border-radius:12px;padding:18px 24px;display:flex;justify-content:space-between;align-items:center;margin-top:16px}}
  .net-box .lbl{{font-size:13px;opacity:.8}}
  .net-box .amt{{font-size:28px;font-weight:900}}
  .footer{{background:#f8fafc;padding:14px 32px;text-align:center;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}}
  .print-btn{{display:flex;gap:10px;margin:18px 32px 4px;justify-content:flex-end}}
  .btn{{padding:9px 20px;border:none;border-radius:9px;font-size:13px;font-weight:700;cursor:pointer}}
  .btn-print{{background:#0f2460;color:#fff}}
  .btn-back{{background:#f1f5f9;color:#64748b}}
  .green{{color:#16a34a}} .red{{color:#ef4444}} .yellow{{color:#f59e0b}}
  @media print{{
    body{{background:#fff}}
    .wrap{{box-shadow:none;margin:0;border-radius:0}}
    .print-btn{{display:none}}
    .btn{{display:none}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="print-btn">
    <button class="btn btn-back" onclick="history.back()">&#8592; Back</button>
    <button class="btn btn-print" onclick="window.print()">&#128438; Download / Print PDF</button>
  </div>

  <div class="hdr">
    <div class="hdr-left">
      <h1>{_html.escape(str(company_name)) if company_name else "Payslip"}</h1>
      <p>Salary Slip — {month_name}</p>
    </div>
    <div class="hdr-right">
      <div class="slip-num">Slip ID: {_html.escape(str(emp_id))}-{year}{month:02d}</div>
      <div class="month">{month_name}</div>
    </div>
  </div>

  <div class="emp-bar">
    <table>
      <tr><td>Employee Name</td><td>{_html.escape(str(emp_name))}</td></tr>
      <tr><td>Employee ID</td><td>{_html.escape(str(emp_id))}</td></tr>
      <tr><td>Email</td><td>{_html.escape(str(emp_email)) if emp_email else 'N/A'}</td></tr>
      {emp_row_extra}
    </table>
    <table>
      <tr><td>Pay Period</td><td>{month_name}</td></tr>
      <tr><td>Working Days (Standard)</td><td>26</td></tr>
      <tr><td>Days Present</td><td>{paid_days_display}</td></tr>
      <tr><td>LOP Days</td><td>{int(lop_days)}</td></tr>
      <tr><td>Monthly CTC</td><td>Rs. {monthly_ctc:,.2f}</td></tr>
    </table>
  </div>

  <div class="att-strip">
    <div class="att-cell"><div class="num green">{full_d}</div><div class="lbl">Full Days</div></div>
    <div class="att-cell"><div class="num yellow">{late_d}</div><div class="lbl">Late Days</div></div>
    <div class="att-cell"><div class="num yellow">{half_d}</div><div class="lbl">Half Days</div></div>
    <div class="att-cell"><div class="num red">{int(lop_days)}</div><div class="lbl">LOP / Absent</div></div>
    <div class="att-cell"><div class="num" style="color:#3b82f6">{e.get('holiday_days',0)}</div><div class="lbl">Holidays</div></div>
    <div class="att-cell"><div class="num" style="color:#9333ea">{e.get('leave_days',0)}</div><div class="lbl">Leave (Paid)</div></div>
  </div>

  <div class="body">
    <div class="two-col">
      <div>
        <div class="sec-title">Earnings (Monthly)</div>
        <table class="pay-tbl">
          <tr><td>Basic Salary ({basic_pct}% of CTC)</td><td>Rs. {basic:,.2f}</td></tr>
          <tr><td>House Rent Allowance (HRA)</td><td>Rs. {hra:,.2f}</td></tr>
          <tr><td>Conveyance Allowance</td><td>Rs. {conveyance:,.2f}</td></tr>
          <tr><td>Special Allowance</td><td>Rs. {special_all:,.2f}</td></tr>
          {incentive_row}
          <tr class="tot"><td>Gross Salary</td><td>Rs. {gross_salary:,.2f}</td></tr>
        </table>
        <div style="margin-top:10px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 12px;font-size:12px;color:#15803d;">
          <b>PF — Employer Contribution ({pf_er_pct:.0f}%)</b>: Rs. {pf_er_ded:,.2f}
          <div style="color:#64748b;margin-top:2px;font-size:11px;">Company's share — not deducted from your pay</div>
        </div>
      </div>
      <div>
        <div class="sec-title">Deductions</div>
        <table class="pay-tbl">
          <tr><td>Loss of Pay — LOP ({int(lop_days)} days × Rs.{gross_salary/26:,.2f})</td><td class="red">Rs. {lop_ded:,.2f}</td></tr>
          <tr><td>PF — Employee Contribution ({pf_pct:.0f}% of Basic)</td><td class="red">Rs. {pf_ded:,.2f}</td></tr>
          <tr><td>Professional Tax</td><td class="red">Rs. {pt_monthly:,.2f}</td></tr>
          {"<tr><td>TDS — Income Tax (annual " + f"{tds_ann_pct:.1f}%" + ")</td><td class='red'>Rs. " + f"{tds_ded:,.2f}</td></tr>" if tds_ded > 0 else ""}
          <tr class="tot"><td>Total Deductions</td><td>Rs. {total_ded:,.2f}</td></tr>
        </table>
        <div style="margin-top:10px;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:10px 12px;font-size:12px;color:#92400e;">
          <b>Gross Earned</b> (after LOP): Rs. {gross_earned:,.2f}
          <div style="color:#64748b;margin-top:2px;font-size:11px;">Gross Salary − LOP before other deductions</div>
        </div>
      </div>
    </div>

    <div class="net-box">
      <div>
        <div class="lbl">Net Take-Home Pay</div>
        <div style="font-size:11px;opacity:.65;margin-top:4px;">
          Rs.{gross_salary:,.2f} − LOP Rs.{lop_ded:,.2f} − PF Rs.{pf_ded:,.2f} − PT Rs.{pt_monthly:,.2f}{f" − TDS Rs.{tds_ded:,.2f}" if tds_ded > 0 else ""}
        </div>
      </div>
      <div class="amt">Rs. {net_pay:,.2f}</div>
    </div>
  </div>

  <div class="footer">
    <span>This is a system-generated payslip. Contact HR for any discrepancies.</span>
    <span>Generated on {datetime.date.today().strftime('%d %B %Y')}</span>
  </div>
</div>
</body>
</html>"""


def compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                         holidays_set=None, leave_dates=None):
    if holidays_set is None:
        holidays_set = set()
    if leave_dates is None:
        leave_dates = set()

    emp_att = att_map.get(emp_id, {})
    full_days = half_days = late_days = absent_days = 0
    holiday_days = leave_days_count = 0

    for d in billable_past:
        if d in holidays_set:
            if HOLIDAY_PAY == 'paid':
                full_days += 1
            else:
                absent_days += 1   # unpaid holiday = counts as absent deduction
            holiday_days += 1
        elif d in leave_dates:
            if LEAVE_PAY == 'absent':
                absent_days += 1   # count approved leave as absent
            else:
                leave_days_count += 1  # exclude from working days, no pay/no deduction
        else:
            row = emp_att.get(d)
            if row:
                _, _, login_t, logout_t, status, _logout_status, att_type = row
                final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
                if final == "Full Day":
                    full_days += 1
                elif final == "Late - Full Day":
                    late_days += 1
                elif final in ("Half Day", "Present"):
                    half_days += 1
                else:
                    absent_days += 1
            else:
                absent_days += 1

    effective_billable = len(billable_past) - leave_days_count

    spd_f      = float(spd)
    full_earn  = round(full_days  * spd_f, 2)
    late_earn  = round(late_days  * spd_f * (1 - LATE_DEDUCTION_RATE), 2)
    half_earn  = round(half_days  * spd_f * (1 - HALF_DAY_RATE), 2)
    net        = round(full_earn + late_earn + half_earn, 2)
    gross      = round(spd_f * effective_billable, 2)
    deduction  = round(gross - net, 2)

    return {
        "emp_id":        emp_id,
        "name":          name,
        "spd":           round(spd_f, 2),
        "billable":      effective_billable,
        "present":       full_days + half_days + late_days,
        "holiday_days":  holiday_days,
        "leave_days":    leave_days_count,
        "full_days":     full_days,
        "half_days":     half_days,
        "late_days":     late_days,
        "absent":        absent_days,
        "full_earn":     full_earn,
        "late_earn":     late_earn,
        "half_earn":     half_earn,
        "gross":         gross,
        "absent_ded":    round(absent_days * spd_f, 2),
        "half_ded":      round(half_days   * spd_f * HALF_DAY_RATE, 2),
        "late_ded":      round(late_days   * spd_f * LATE_DEDUCTION_RATE, 2),
        "deduction":     deduction,
        "net":           net,
    }



@payroll_bp.route("/save_salary_rules", methods=["POST"])
@admin_required
def save_salary_rules():
    try:
        late_pct  = max(0.0, min(100.0, float(request.form.get("late_deduction_pct",  10))))
        half_pct  = max(0.0, min(100.0, float(request.form.get("half_day_deduction_pct", 50))))
        grace_min = max(0,   min(120,   int(request.form.get("grace_minutes", 15))))
    except (ValueError, TypeError):
        flash("Invalid values.", "error")
        return redirect("/settings?tab=salary")
    holiday_pay = request.form.get("holiday_pay", "paid")
    leave_pay   = request.form.get("leave_pay",   "exclude")
    if holiday_pay not in ("paid", "unpaid"):
        holiday_pay = "paid"
    if leave_pay not in ("exclude", "absent"):
        leave_pay = "exclude"
    shift_start_raw = request.form.get("shift_start", "").strip()
    shift_half_raw  = request.form.get("shift_half",  "").strip()
    shift_end_raw   = request.form.get("shift_end",   "").strip()
    active_cid = session.get("active_company_id")
    if active_cid:
        _fields = {
            "late_deduction_pct": late_pct, "half_day_deduction_pct": half_pct,
            "grace_minutes": grace_min, "holiday_pay": holiday_pay, "leave_pay": leave_pay,
        }
        if shift_start_raw and shift_half_raw and shift_end_raw:
            _fields.update({"shift_start": shift_start_raw, "shift_half": shift_half_raw,
                            "shift_end": shift_end_raw})
        _upsert_co_features(active_cid, _fields)
    else:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "UPDATE company_settings SET late_deduction_pct=%s, half_day_deduction_pct=%s, "
            "grace_minutes=%s, holiday_pay=%s, leave_pay=%s",
            (late_pct, half_pct, grace_min, holiday_pay, leave_pay)
        )
        if shift_start_raw and shift_half_raw and shift_end_raw:
            cursor.execute(
                "UPDATE company_settings SET shift_start=%s, shift_half=%s, shift_end=%s",
                (shift_start_raw, shift_half_raw, shift_end_raw)
            )
        db.commit()
        cursor.close(); db.close()
        load_salary_rules()
        load_default_shift()
    flash("Salary rules saved.", "success")
    return redirect("/settings?tab=salary")


@payroll_bp.route("/view_salary")
@admin_required
def view_salary():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    active_cid = session.get("active_company_id")
    if active_cid:
        cursor.execute("""
            SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0), e.role, s.last_revised,
                   COALESCE(e.phone,''), COALESCE(e.email,'')
            FROM employees e
            LEFT JOIN salary_config s ON e.employee_id = s.employee_id
            WHERE e.company_id = %s
            ORDER BY e.name
        """, (active_cid,))
    else:
        cursor.execute("""
            SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0), e.role, s.last_revised,
                   COALESCE(e.phone,''), COALESCE(e.email,'')
            FROM employees e
            LEFT JOIN salary_config s ON e.employee_id = s.employee_id
            ORDER BY e.name
        """)
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("salary.html", salaries=data,
        active_nav="salary",
    )


@payroll_bp.route("/update_salary", methods=["POST"])
@admin_required
def update_salary():
    emp_id     = request.form["emp_id"]
    salary     = request.form["salary"]
    hike_date  = request.form.get("hike_date") or None
    db         = get_db_connection()
    cursor     = db.cursor(buffered=True)
    cursor.execute("SELECT 1 FROM salary_config WHERE employee_id=%s", (emp_id,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE salary_config SET salary_per_day=%s, last_revised=%s WHERE employee_id=%s",
            (salary, hike_date or datetime.date.today(), emp_id)
        )
    else:
        cursor.execute(
            "INSERT INTO salary_config (employee_id, salary_per_day, last_revised) VALUES (%s,%s,%s)",
            (emp_id, salary, hike_date or datetime.date.today())
        )
    db.commit()
    cursor.close()
    db.close()
    _audit("update_salary", "salary_config", emp_id, f"salary_per_day set to {salary}")
    return redirect("/settings?tab=salary")


@payroll_bp.route("/salary_report")
@admin_required
def salary_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    active_cid = session.get("active_company_id")
    if active_cid:
        cursor.execute("""
            SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0),
                   COALESCE(e.role,''), COALESCE(e.phone,'')
            FROM employees e
            LEFT JOIN salary_config s ON e.employee_id = s.employee_id
            WHERE e.company_id = %s
            ORDER BY e.name
        """, (active_cid,))
    else:
        cursor.execute("""
            SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0),
                   COALESCE(e.role,''), COALESCE(e.phone,'')
            FROM employees e
            LEFT JOIN salary_config s ON e.employee_id = s.employee_id
            ORDER BY e.name
        """)
    employees = cursor.fetchall()

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance
        WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))

    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    cursor.execute("""
        SELECT employee_id, leave_date FROM leave_requests
        WHERE status = 'Approved' AND leave_date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    leave_map = {}
    for eid, ld in cursor.fetchall():
        leave_map.setdefault(eid, set()).add(ld)

    cursor.execute(
        "SELECT processed_at, processed_by, email_count FROM payroll_runs WHERE year=%s AND month=%s",
        (year, month)
    )
    lock_row = cursor.fetchone()
    is_locked = lock_row is not None
    lock_info = {"at": lock_row[0], "by": lock_row[1], "count": lock_row[2]} if lock_row else None

    cursor.close()
    db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)

    # Fetch all incentives for this month in one query
    try:
        db2     = get_db_connection()
        cursor2 = db2.cursor(buffered=True)
        cursor2.execute(
            "SELECT employee_id, COALESCE(SUM(amount),0) FROM employee_incentives WHERE year=%s AND month=%s GROUP BY employee_id",
            (year, month)
        )
        incentive_map = {r[0]: float(r[1]) for r in cursor2.fetchall()}
        cursor2.close(); db2.close()
    except Exception:
        incentive_map = {}

    salary_data = []
    for emp_id, name, email, spd, role, phone in employees:
        entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                     holidays_set=holidays_set,
                                     leave_dates=leave_map.get(emp_id, set()))
        inc = incentive_map.get(emp_id, 0.0)
        entry["incentive"] = inc
        entry["net"]       = round(entry["net"] + inc, 2)
        entry["email"] = email
        entry["role"]  = role
        entry["phone"] = phone
        salary_data.append(entry)

    months = [(i, datetime.date(year, i, 1).strftime("%B")) for i in range(1, 13)]
    years  = list(range(datetime.date.today().year - 2, datetime.date.today().year + 1))

    email_cfg = get_email_config()

    return render_template("salary_report.html",
        salary_data=salary_data,
        month_name=datetime.date(year, month, 1).strftime("%B %Y"),
        active_nav="salary",
        year=year, month=month,
        months=months, years=years,
        late_rate=int(LATE_DEDUCTION_RATE * 100),
        half_rate=int(HALF_DAY_RATE * 100),
        email_configured=email_cfg is not None,
        is_locked=is_locked,
        lock_info=lock_info,
    )


@payroll_bp.route("/salary_report_export")
@admin_required
def salary_report_export():
    from flask import send_file
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0),
               COALESCE(e.role,''), COALESCE(e.department,'')
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    employees = cursor.fetchall()

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    cursor.execute("""
        SELECT employee_id, leave_date FROM leave_requests
        WHERE status='Approved' AND leave_date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    leave_map = {}
    for eid, ld in cursor.fetchall():
        leave_map.setdefault(eid, set()).add(ld)

    cursor2 = db.cursor(buffered=True)
    cursor2.execute(
        "SELECT employee_id, COALESCE(SUM(amount),0) FROM employee_incentives WHERE year=%s AND month=%s GROUP BY employee_id",
        (year, month)
    )
    incentive_map = {r[0]: float(r[1]) for r in cursor2.fetchall()}
    cursor.close(); cursor2.close(); db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)

    wb = openpyxl.Workbook()
    ws = wb.active
    month_name = datetime.date(year, month, 1).strftime("%B %Y")
    ws.title = f"Salary {month_name}"

    hdr_fill   = PatternFill("solid", fgColor="1E3A8A")
    hdr_font   = Font(bold=True, color="FFFFFF", size=11)
    alt_fill   = PatternFill("solid", fgColor="EFF6FF")
    center     = Alignment(horizontal="center", vertical="center")
    thin_side  = Side(style="thin", color="CCCCCC")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    headers = ["#", "Employee ID", "Name", "Role", "Department",
               "Salary/Day", "Billable Days", "Present", "Absent",
               "Deduction", "Incentive", "Net Salary"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = center; cell.border = thin_border

    col_widths = [5, 16, 22, 16, 16, 12, 14, 10, 10, 12, 12, 14]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    for idx, (emp_id, name, email, spd, role, dept) in enumerate(employees, 1):
        entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                     holidays_set=holidays_set,
                                     leave_dates=leave_map.get(emp_id, set()))
        inc = incentive_map.get(emp_id, 0.0)
        net = round(entry["net"] + inc, 2)
        row_data = [
            idx, emp_id, name, role, dept,
            float(spd), entry["billable"], entry["present"],
            entry["absent"], entry["deduction"], inc, net
        ]
        fill = alt_fill if idx % 2 == 0 else None
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=idx + 1, column=col, value=val)
            cell.border = thin_border
            cell.alignment = center
            if fill:
                cell.fill = fill

    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Salary_Report_{month_name.replace(' ', '_')}.xlsx"
    return send_file(buf, as_attachment=True,
                     download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@payroll_bp.route("/send_salary_email", methods=["POST"])
@admin_required
def send_salary_email():
    emp_id = request.form["emp_id"]
    year   = int(request.form["year"])
    month  = int(request.form["month"])

    config = get_email_config()
    if not config:
        return jsonify({"ok": False, "msg": "Email not configured. Go to Email Settings first."})

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT e.name, e.email, COALESCE(s.salary_per_day,0),
               COALESCE(s.monthly_ctc,0), COALESCE(s.basic_pct,50),
               COALESCE(e.role,''), COALESCE(e.department,'')
        FROM employees e LEFT JOIN salary_config s ON e.employee_id=s.employee_id
        WHERE e.employee_id=%s
    """, (emp_id,))
    emp = cursor.fetchone()
    if not emp:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found."})

    name, email, spd, monthly_ctc, basic_pct, designation, dept = emp
    if not email:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": f"No email address set for {name}."})

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE employee_id=%s AND date BETWEEN %s AND %s
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))

    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    _, last_day2 = calendar.monthrange(year, month)
    cursor.execute(
        "SELECT leave_date FROM leave_requests "
        "WHERE status='Approved' AND employee_id=%s AND leave_date BETWEEN %s AND %s",
        (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day2))
    )
    leave_dates = {row[0] for row in cursor.fetchall()}

    # Fetch payroll config
    db2 = get_db_connection()
    cur2 = db2.cursor(buffered=True)
    cur2.execute("SELECT pf_employee_pct,pf_employer_pct,professional_tax,tds_annual_pct,pf_basic_cap FROM payroll_config LIMIT 1")
    pc_row = cur2.fetchone()
    payroll_cfg = {"pf_employee_pct": float(pc_row[0] or 12), "pf_employer_pct": float(pc_row[1] or 12),
                   "professional_tax": float(pc_row[2] or 200), "tds_annual_pct": float(pc_row[3] or 0),
                   "pf_basic_cap": float(pc_row[4] or 15000)} if pc_row else {}
    cur2.close(); db2.close()
    cursor.close(); db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)
    entry         = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                         holidays_set=holidays_set, leave_dates=leave_dates)
    entry["monthly_ctc"] = float(monthly_ctc) if float(monthly_ctc) > 0 else float(spd) * 26
    entry["basic_pct"]   = int(basic_pct)
    month_name    = datetime.date(year, month, 1).strftime("%B %Y")
    html_body     = build_salary_slip_html(name, emp_id, email, month_name, year, month, entry,
                                           emp_designation=designation, emp_dept=dept,
                                           payroll_cfg=payroll_cfg)

    try:
        send_email_smtp(email, f"Salary Slip - {month_name}", html_body, config)
        return jsonify({"ok": True, "msg": f"Salary slip sent to {email}"})
    except Exception:
        app_log.error("Failed to send salary slip email to %s", email, exc_info=True)
        return jsonify({"ok": False, "msg": "Failed to send email. Check email settings."})


@payroll_bp.route("/send_all_salary_emails", methods=["POST"])
@admin_required
def send_all_salary_emails():
    year  = int(request.form["year"])
    month = int(request.form["month"])

    config = get_email_config()
    if not config:
        return jsonify({"ok": False, "msg": "Email not configured. Go to Email Settings first."})

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    employees = cursor.fetchall()

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))

    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    _, last_day_all = calendar.monthrange(year, month)
    cursor.execute(
        "SELECT employee_id, leave_date FROM leave_requests "
        "WHERE status='Approved' AND leave_date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, last_day_all))
    )
    leave_map_all = {}
    for eid, ld in cursor.fetchall():
        leave_map_all.setdefault(eid, set()).add(ld)

    cursor.close(); db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)
    month_name    = datetime.date(year, month, 1).strftime("%B %Y")

    sent = skipped = failed = 0
    errors = []

    for emp_id, name, email, spd in employees:
        if not email:
            skipped += 1
            continue
        entry     = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                         holidays_set=holidays_set,
                                         leave_dates=leave_map_all.get(emp_id, set()))
        html_body = build_salary_slip_html(name, emp_id, email, month_name, year, month, entry)
        try:
            send_email_smtp(email, f"Salary Slip - {month_name}", html_body, config)
            sent += 1
        except Exception:
            app_log.error("Failed to send salary slip to %s", name, exc_info=True)
            failed += 1
            errors.append(f"{name}: email delivery failed")

    if sent > 0:
        try:
            db2 = get_db_connection(); cur2 = db2.cursor()
            actor = session.get("admin_username", "admin")
            cur2.execute("""
                INSERT INTO payroll_runs (year, month, processed_by, email_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (year, month) DO UPDATE SET processed_at=NOW(), processed_by=%s, email_count=%s
            """, (year, month, actor, sent, actor, sent))
            db2.commit(); cur2.close(); db2.close()
            _audit("lock_payroll", "payroll_runs", f"{year}-{month:02d}",
                   f"Payroll locked for {year}-{month:02d} after sending {sent} payslips")
        except Exception as _le:
            app_log.warning("Could not record payroll lock for %d-%02d: %s", year, month, _le)

    msg = f"Sent: {sent}, Skipped (no email): {skipped}, Failed: {failed}"
    if errors:
        msg += " | " + "; ".join(errors[:3])
    return jsonify({"ok": failed == 0, "msg": msg, "locked": sent > 0})


@payroll_bp.route("/lock_payroll", methods=["POST"])
@admin_required
def lock_payroll():
    year  = int(request.form["year"])
    month = int(request.form["month"])
    actor = session.get("admin_username", "admin")
    db = get_db_connection(); cursor = db.cursor()
    cursor.execute("""
        INSERT INTO payroll_runs (year, month, processed_by, email_count)
        VALUES (%s, %s, %s, 0)
        ON CONFLICT (year, month) DO UPDATE SET processed_at=NOW(), processed_by=%s
    """, (year, month, actor, actor))
    db.commit(); cursor.close(); db.close()
    _audit("lock_payroll", "payroll_runs", f"{year}-{month:02d}", f"Manually locked by {actor}")
    return jsonify({"ok": True, "msg": f"Payroll for {year}-{month:02d} locked."})


@payroll_bp.route("/unlock_payroll", methods=["POST"])
@admin_required
def unlock_payroll():
    year  = int(request.form["year"])
    month = int(request.form["month"])
    actor = session.get("admin_username", "admin")
    db = get_db_connection(); cursor = db.cursor()
    cursor.execute("DELETE FROM payroll_runs WHERE year=%s AND month=%s", (year, month))
    db.commit(); cursor.close(); db.close()
    _audit("unlock_payroll", "payroll_runs", f"{year}-{month:02d}", f"Unlocked by {actor}")
    return jsonify({"ok": True, "msg": f"Payroll for {year}-{month:02d} unlocked."})


@payroll_bp.route("/my_payslip_summary/<int:year>/<int:month>")
@employee_required
def my_payslip_summary(year, month):
    import json as _json
    emp_id = session["employee_id"]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT COALESCE(salary_per_day,0) FROM salary_config WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    spd = float(row[0]) if row else 0.0

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE employee_id=%s AND date BETWEEN %s AND %s
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_rows = cursor.fetchall()

    # Incentive total for this employee/month
    try:
        cursor.execute(
            "SELECT COALESCE(SUM(amount),0) FROM employee_incentives WHERE employee_id=%s AND year=%s AND month=%s",
            (emp_id, year, month)
        )
        incentive = float(cursor.fetchone()[0])
        cursor.execute("""
            SELECT ig.title, ei.amount, ei.notes
            FROM employee_incentives ei
            JOIN incentive_goals ig ON ei.goal_id = ig.id
            WHERE ei.employee_id=%s AND ei.year=%s AND ei.month=%s
        """, (emp_id, year, month))
        incentive_details = [{"title": r[0], "amount": float(r[1]), "notes": r[2] or ""} for r in cursor.fetchall()]
    except Exception:
        incentive = 0.0
        incentive_details = []

    try:
        cursor.execute(
            "SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s AND status='Approved'",
            (emp_id, month, year)
        )
        ot_pay = float(cursor.fetchone()[0])
    except Exception:
        ot_pay = 0.0

    cursor.close(); db.close()

    att_map = {r[0]: r for r in att_rows}
    billable = get_billable_past_days(year, month)
    full = late = half = 0
    for d in billable:
        r = att_map.get(d)
        if r:
            final = r[5] if r[5] else infer_type_legacy(r[3], r[1], r[2])
            if final == "Full Day":          full += 1
            elif final == "Late - Full Day": late += 1
            elif final in ("Half Day","Present"): half += 1

    full_earn = round(full * spd, 2)
    late_earn = round(late * spd, 2)
    half_earn = round(half * spd * 0.5, 2)
    gross = full_earn + late_earn + half_earn
    pf = round(gross * 0.12, 2)
    net = round(gross - pf + incentive + ot_pay, 2)

    return _json.dumps({
        "salary_per_day": spd,
        "full_days": full, "late_days": late, "half_days": half,
        "full_earn": full_earn, "late_earn": late_earn, "half_earn": half_earn,
        "gross": gross, "pf": pf, "incentive": incentive,
        "incentive_details": incentive_details, "ot_pay": ot_pay, "net": net
    }), 200, {"Content-Type": "application/json"}


@payroll_bp.route("/apply_hike", methods=["POST"])
@admin_required
def apply_hike():
    q   = int(request.form.get("quarter", 1))
    yr  = int(request.form.get("year", datetime.date.today().year))
    emp_ids = request.form.getlist("emp_ids")
    if not emp_ids:
        flash("No employees selected.", "error")
        return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT min_rating, max_rating, hike_pct FROM hike_config ORDER BY min_rating DESC")
    bands = cursor.fetchall()

    today = datetime.date.today()
    updated = 0
    for emp_id in emp_ids:
        cursor.execute(
            "SELECT COALESCE(overall_rating,0) FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s",
            (emp_id, q, yr)
        )
        row = cursor.fetchone()
        if not row or float(row[0]) == 0:
            continue
        rating = float(row[0])
        hike_pct = 0.0
        for (mn, mx, hp) in bands:
            if float(mn) <= rating <= float(mx):
                hike_pct = float(hp)
                break
        if hike_pct <= 0:
            continue
        cursor.execute(
            "SELECT COALESCE(monthly_ctc,0), last_hike_quarter, last_hike_year FROM salary_config WHERE employee_id=%s",
            (emp_id,)
        )
        sc = cursor.fetchone()
        if not sc or float(sc[0]) == 0:
            continue
        # Idempotency: skip if this quarter's hike was already applied
        if sc[1] == q and sc[2] == yr:
            continue
        current_ctc = float(sc[0])
        new_ctc = round(current_ctc * (1 + hike_pct / 100), 2)
        new_spd = round(new_ctc / 26, 2)
        cursor.execute(
            "UPDATE salary_config SET monthly_ctc=%s, salary_per_day=%s, last_revised=%s, "
            "last_hike_quarter=%s, last_hike_year=%s WHERE employee_id=%s",
            (new_ctc, new_spd, today, q, yr, emp_id)
        )
        updated += 1

    db.commit()
    cursor.close(); db.close()
    flash(f"Hike applied to {updated} employee(s) successfully.", "success")
    return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")


@payroll_bp.route("/award_performance_bonus", methods=["POST"])
@admin_required
def award_performance_bonus():
    q   = int(request.form.get("quarter", 1))
    yr  = int(request.form.get("year", datetime.date.today().year))
    emp_ids = request.form.getlist("emp_ids")
    if not emp_ids:
        flash("No employees selected.", "error")
        return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("SELECT id FROM incentive_goals WHERE title='Performance Bonus' LIMIT 1")
    row = cursor.fetchone()
    if row:
        goal_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO incentive_goals (title, description, incentive_amount, is_active) VALUES (%s,%s,%s,%s) RETURNING id",
            ("Performance Bonus", "Quarterly performance-based incentive", 0, 1)
        )
        goal_id = cursor.fetchone()[0]
        db.commit()

    cursor.execute("SELECT min_rating, max_rating, incentive_pct FROM hike_config ORDER BY min_rating DESC")
    bands = cursor.fetchall()

    bonus_month = {1: 3, 2: 6, 3: 9, 4: 12}.get(q, q * 3)
    awarded = 0
    for emp_id in emp_ids:
        cursor.execute(
            "SELECT COALESCE(overall_rating,0) FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s",
            (emp_id, q, yr)
        )
        row = cursor.fetchone()
        if not row or float(row[0]) == 0:
            continue
        rating = float(row[0])
        inc_pct = 0.0
        for (mn, mx, ip) in bands:
            if float(mn) <= rating <= float(mx):
                inc_pct = float(ip)
                break
        if inc_pct <= 0:
            continue
        cursor.execute("SELECT COALESCE(monthly_ctc,0) FROM salary_config WHERE employee_id=%s", (emp_id,))
        sc = cursor.fetchone()
        if not sc or float(sc[0]) == 0:
            continue
        bonus_amount = round(float(sc[0]) * inc_pct / 100, 2)
        if bonus_amount <= 0:
            continue
        # Skip if this bonus was already awarded for this employee/quarter/year
        cursor.execute(
            "SELECT id FROM employee_incentives WHERE employee_id=%s AND goal_id=%s AND month=%s AND year=%s",
            (emp_id, goal_id, bonus_month, yr)
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO employee_incentives (employee_id, goal_id, month, year, amount, notes) VALUES (%s,%s,%s,%s,%s,%s)",
            (emp_id, goal_id, bonus_month, yr, bonus_amount, f"Performance bonus Q{q} {yr} — Rating: {rating}/5")
        )
        awarded += 1

    db.commit()
    cursor.close(); db.close()
    flash(f"Performance bonus awarded to {awarded} employee(s).", "success")
    return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")


@payroll_bp.route("/save_hike_config", methods=["POST"])
@admin_required
def save_hike_config():
    q  = request.form.get("quarter", "1")
    yr = request.form.get("year", str(datetime.date.today().year))
    ids       = request.form.getlist("band_id")
    labels    = request.form.getlist("band_label")
    min_rats  = request.form.getlist("band_min")
    max_rats  = request.form.getlist("band_max")
    hike_pcts = request.form.getlist("band_hike")
    inc_pcts  = request.form.getlist("band_inc")

    n = min(len(ids), len(labels), len(min_rats), len(max_rats), len(hike_pcts), len(inc_pcts))
    if n == 0:
        flash("No band data received.", "error")
        return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    for i in range(n):
        try:
            cursor.execute(
                "UPDATE hike_config SET label=%s, min_rating=%s, max_rating=%s, hike_pct=%s, incentive_pct=%s WHERE id=%s",
                (labels[i], float(min_rats[i]), float(max_rats[i]), float(hike_pcts[i]), float(inc_pcts[i]), int(ids[i]))
            )
        except (ValueError, TypeError):
            continue
    db.commit()
    cursor.close(); db.close()
    flash("Hike band configuration saved.", "success")
    return redirect(f"/performance?tab=hike&quarter={q}&year={yr}")


@payroll_bp.route("/api/salary_config", methods=["GET"])
@api_required
def api_salary_config_get():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "salaries": [
        {"employee_id": r[0], "name": r[1], "salary_per_day": float(r[2])} for r in rows
    ]})


@payroll_bp.route("/api/salary_config", methods=["POST"])
@api_required
def api_salary_config_post():
    data   = request.get_json() or {}
    emp_id = data.get("employee_id")
    salary = data.get("salary_per_day")
    if not emp_id or salary is None:
        return jsonify({"ok": False, "msg": "employee_id and salary_per_day required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT 1 FROM salary_config WHERE employee_id=%s", (emp_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE salary_config SET salary_per_day=%s WHERE employee_id=%s", (salary, emp_id))
    else:
        cursor.execute("INSERT INTO salary_config (employee_id, salary_per_day) VALUES (%s,%s)", (emp_id, salary))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@payroll_bp.route("/api/salary_report", methods=["GET"])
@api_required
def api_salary_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    employees = cursor.fetchall()
    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row
    cursor.close(); db.close()
    billable_past = get_billable_past_days(year, month)
    salary_data   = []
    for emp_id, name, email, spd in employees:
        entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past)
        entry["email"] = email
        salary_data.append(entry)
    return jsonify({"ok": True, "salary_data": salary_data,
                    "month_name": datetime.date(year, month, 1).strftime("%B %Y"),
                    "year": year, "month": month})


@payroll_bp.route("/api/send_salary_email", methods=["POST"])
@api_required
def api_send_salary_email():
    data   = request.get_json() or {}
    emp_id = data.get("emp_id")
    year   = int(data.get("year",  datetime.date.today().year))
    month  = int(data.get("month", datetime.date.today().month))
    config = get_email_config()
    if not config:
        return jsonify({"ok": False, "msg": "Email not configured."})
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT name, email, COALESCE(s.salary_per_day,0) FROM employees e "
        "LEFT JOIN salary_config s ON e.employee_id=s.employee_id WHERE e.employee_id=%s",
        (emp_id,)
    )
    emp = cursor.fetchone()
    if not emp:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found."})
    name, email, spd = emp
    if not email:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": f"No email for {name}."})
    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE employee_id=%s AND date BETWEEN %s AND %s
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row
    cursor.close(); db.close()
    billable_past = get_billable_past_days(year, month)
    entry         = compute_salary_entry(emp_id, name, spd, att_map, billable_past)
    month_name    = datetime.date(year, month, 1).strftime("%B %Y")
    html_body     = build_salary_slip_html(name, emp_id, email, month_name, year, month, entry)
    send_email_async(email, f"Salary Slip - {month_name}", html_body, config)
    return jsonify({"ok": True, "msg": f"Queued for {email}"})


@payroll_bp.route("/api/employee/salary", methods=["GET"])
@employee_api_required
def api_employee_salary():
    import calendar as cal
    from flask import g as _g
    emp_id = _g.api_emp_id
    try:
        year  = int(request.args.get("year",  datetime.date.today().year))
        month = int(request.args.get("month", datetime.date.today().month))
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid year/month"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name, email FROM employees WHERE employee_id=%s", (emp_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    cursor.execute("SELECT salary_per_day FROM salary_config WHERE employee_id=%s", (emp_id,))
    spd_row  = cursor.fetchone()
    spd      = float(spd_row[0]) if spd_row else 0.0
    cursor.execute("SELECT date FROM holidays WHERE EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s", (month, year))
    holiday_set = {r[0] for r in cursor.fetchall()}
    _, days_in_month = cal.monthrange(year, month)
    billable = sum(
        1 for d in range(1, days_in_month + 1)
        # weekday() != 6 excludes only Sunday, matching get_working_days() —
        # the real payroll engine treats Saturday as a billable working day.
        if datetime.date(year, month, d).weekday() != 6
        and datetime.date(year, month, d) not in holiday_set
    )
    cursor.execute("""
        SELECT attendance_type FROM attendance
        WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s
    """, (emp_id, month, year))
    att_rows = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*) FROM leave_requests
        WHERE employee_id=%s AND EXTRACT(MONTH FROM leave_date)=%s AND EXTRACT(YEAR FROM leave_date)=%s AND status='Approved'
    """, (emp_id, month, year))
    leave_days = cursor.fetchone()[0]
    cursor.close(); db.close()
    full_days = half_days = late_days = 0
    for (att_type,) in att_rows:
        if att_type == 'Full Day':          full_days += 1
        elif att_type == 'Late - Full Day': full_days += 1; late_days += 1
        elif att_type in ('Half Day', 'Late - Half Day'): half_days += 1
    absent    = max(0, billable - full_days - half_days - leave_days)
    gross     = spd * billable
    deduction = spd * (absent + half_days * 0.5)
    net       = gross - deduction
    return jsonify({
        "ok": True,
        "month_name": datetime.date(year, month, 1).strftime("%B %Y"),
        "year": year, "month": month,
        "salary": {
            "emp_id": emp_id, "name": emp_row[0], "email": emp_row[1],
            "spd": spd, "billable": billable,
            "full_days": full_days, "half_days": half_days,
            "late_days": late_days, "absent": absent, "leave_days": leave_days,
            "gross": gross, "deduction": deduction, "net": net,
        }
    })


@payroll_bp.route("/view_payslip/<emp_id>/<int:year>/<int:month>")
def view_payslip(emp_id, year, month):
    is_admin = session.get("admin_logged_in")
    is_own   = session.get("employee_id") == emp_id
    if not is_admin and not is_own:
        return redirect("/employee_login")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.name, e.email, COALESCE(s.salary_per_day, 0),
               COALESCE(s.monthly_ctc, 0), COALESCE(s.basic_pct, 50),
               COALESCE(e.role,''), COALESCE(e.department,''),
               COALESCE(e.pan_number,''), COALESCE(e.uan_number,''),
               COALESCE(e.bank_account,''), COALESCE(e.bank_name,'')
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        WHERE e.employee_id = %s
    """, (emp_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return "Employee not found", 404
    name, email, spd, monthly_ctc, basic_pct, designation, dept, pan, uan, bank_acct, bank_nm = row
    pan = decrypt_pii(pan); uan = decrypt_pii(uan); bank_acct = decrypt_pii(bank_acct)

    # Payroll config
    cursor.execute("SELECT pf_employee_pct, pf_employer_pct, professional_tax, tds_annual_pct, pf_basic_cap FROM payroll_config LIMIT 1")
    pc_row = cursor.fetchone()
    payroll_cfg = {}
    if pc_row:
        payroll_cfg = {
            "pf_employee_pct": float(pc_row[0] or 12),
            "pf_employer_pct": float(pc_row[1] or 12),
            "professional_tax": float(pc_row[2] or 200),
            "tds_annual_pct": float(pc_row[3] or 0),
            "pf_basic_cap": float(pc_row[4] or 15000),
        }

    cursor.execute("SELECT COALESCE(company_name,'') FROM company_settings LIMIT 1")
    co_row = cursor.fetchone()
    company_name = co_row[0] if co_row else ""

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, employee_id, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance
        WHERE employee_id=%s AND date BETWEEN %s AND %s
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_map = {}
    for r in cursor.fetchall():
        att_map.setdefault(r[1], {})[r[0]] = r

    cursor.execute(
        "SELECT leave_date FROM leave_requests "
        "WHERE status='Approved' AND employee_id=%s AND leave_date BETWEEN %s AND %s",
        (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day))
    )
    leave_dates = {r[0] for r in cursor.fetchall()}
    cursor.close(); db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)
    entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                 holidays_set=holidays_set, leave_dates=leave_dates)
    entry["monthly_ctc"] = float(monthly_ctc) if float(monthly_ctc) > 0 else float(spd) * 26
    entry["basic_pct"]   = int(basic_pct)

    month_name = calendar.month_name[month] + f" {year}"
    return build_salary_slip_html(
        name, emp_id, email, month_name, year, month, entry,
        company_name=company_name,
        emp_designation=designation, emp_dept=dept,
        pan=pan, uan=uan, bank_account=bank_acct, bank_name=bank_nm,
        payroll_cfg=payroll_cfg
    )


@payroll_bp.route("/download_payslip/<emp_id>/<int:year>/<int:month>")
def download_payslip(emp_id, year, month):
    html = view_payslip(emp_id, year, month)
    if not isinstance(html, str):
        return html  # redirect or error response
    from flask import Response
    filename = f"payslip_{emp_id}_{year}_{month:02d}.html"
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

