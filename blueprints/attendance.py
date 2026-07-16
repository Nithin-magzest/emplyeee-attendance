"""Attendance blueprint — check-in/out, shifts, monthly reports, face recognition."""
import base64
import calendar
import csv
import datetime
import io
import json
import os
import math

from flask import (Blueprint, session, request, redirect, render_template,
                   flash, url_for, jsonify, send_file, abort, Response)

from extensions import app_log, limiter
from database import get_db_connection
from utils.auth import (admin_required, employee_required,
                        api_required, employee_api_required)
from utils.helpers import (_audit, get_company_settings, get_auth_config, _db)
from utils.email_utils import get_email_config, send_email_smtp, send_email_async
from utils.attendance_utils import (
    _td_to_time, get_employee_shift, infer_type_legacy,
    classify_by_worked_minutes, detect_overtime,
    fetch_holidays_set, get_working_days, get_billable_past_days,
)
from utils.config import (
    SHIFT_START, SHIFT_HALF, SHIFT_END,
    GRACE_MINUTES, OFFICE_LAT, OFFICE_LON, OFFICE_RADIUS_M,
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset")

_WA_FP_VERIFY_WINDOW_SEC    = 120
_MOBILE_BIO_VERIFY_WINDOW_SEC = 120

try:
    import face_recognition as face_recognition
    _face_recognition_available = True
except Exception:
    face_recognition = None
    _face_recognition_available = False

_face_enc_cache: dict = {}

attendance_bp = Blueprint("attendance", __name__)

def _get_known_face_encoding(emp_id: str, face_path: str):
    """Return the cached face encoding for an employee, recomputing only when the file changes."""
    try:
        mtime = os.path.getmtime(face_path)
    except OSError:
        return None
    cached = _face_enc_cache.get(emp_id)
    if cached and cached[0] == mtime:
        return cached[1]
    img  = face_recognition.load_image_file(face_path)
    encs = face_recognition.face_encodings(img)
    enc  = encs[0] if encs else None
    _face_enc_cache[emp_id] = (mtime, enc)
    return enc


def _safe_referrer_redirect(referrer: str, fallback: str) -> str:
    """Like _safe_redirect, but also accepts an absolute Referer header as long
    as it points back at this same app (scheme+host), reducing it to a
    relative path first. Referer is client-supplied and can be forged by
    non-browser HTTP clients, so it's never trusted as-is."""
    if not referrer:
        return fallback
    from urllib.parse import urlparse as _urlparse
    p = _urlparse(referrer)
    if not p.scheme and not p.netloc:
        return _safe_redirect(referrer, fallback)
    if p.netloc == request.host:
        path = p.path or "/"
        return _safe_redirect(path + (("?" + p.query) if p.query else ""), fallback)
    return fallback


def is_within_range(user_lat, user_lon, office_lat, office_lon):
    R       = 6371000
    phi1    = math.radians(user_lat)
    phi2    = math.radians(office_lat)
    dphi    = math.radians(office_lat - user_lat)
    dlambda = math.radians(office_lon - user_lon)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return (R * c) <= OFFICE_RADIUS_M


def _fmt_t(t):
    if t is None: return None
    if hasattr(t, 'strftime'): return t.strftime("%H:%M:%S")
    total = int(t.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)


def _wa_fingerprint_recently_verified(emp_id):
    """One-time, employee-bound check: did this employee just complete a real
    WebAuthn signature verification in this session? Consumes the proof."""
    emp_id = (emp_id or "").strip().upper()
    verified_emp = session.pop("wa_fp_verified_emp_id", None)
    verified_at  = session.pop("wa_fp_verified_at", 0)
    return bool(emp_id) and verified_emp == emp_id and (time.time() - verified_at) <= _WA_FP_VERIFY_WINDOW_SEC


def _mobile_biometric_recently_verified(emp_id):
    """One-time, employee-bound check mirroring _wa_fingerprint_recently_verified,
    but DB-backed (mobile has no Flask session) and gated by a real employee
    Bearer token at both the nonce-issue and attest steps above."""
    emp_id = (emp_id or "").strip().upper()
    if not emp_id:
        return False
    with _db() as (cursor, conn):
        cursor.execute(
            "SELECT verified_at FROM mobile_biometric_proofs WHERE employee_id=%s",
            (emp_id,)
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return False
        verified_at = row[0]
        cursor.execute(
            "UPDATE mobile_biometric_proofs SET verified_at=NULL WHERE employee_id=%s",
            (emp_id,)
        )
        conn.commit()
    return (datetime.datetime.now() - verified_at).total_seconds() <= _MOBILE_BIO_VERIFY_WINDOW_SEC



@attendance_bp.route("/api/attendance_chart_data")
@admin_required
def attendance_chart_data():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()

    active_cid = session.get("active_company_id")
    _co_filter = "AND e.company_id=%s" if active_cid else ""
    _co_sub    = "AND a.employee_id IN (SELECT employee_id FROM employees WHERE company_id=%s)" if active_cid else ""
    _co_args   = (active_cid,) if active_cid else ()

    # Last 30 days: present count per day
    cursor.execute(f"""
        SELECT a.date, COUNT(DISTINCT a.employee_id)
        FROM attendance a
        WHERE a.date >= %s AND a.date <= %s AND a.login_time IS NOT NULL {_co_sub}
        GROUP BY a.date ORDER BY a.date
    """, (today - datetime.timedelta(days=29), today) + _co_args)
    present_by_day = {str(r[0]): r[1] for r in cursor.fetchall()}

    if active_cid:
        cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id=%s", _co_args)
    else:
        cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]

    trend_labels, trend_present, trend_absent = [], [], []
    for i in range(29, -1, -1):
        d   = today - datetime.timedelta(days=i)
        key = str(d)
        p   = present_by_day.get(key, 0)
        trend_labels.append(d.strftime("%d %b"))
        trend_present.append(p)
        trend_absent.append(max(total - p, 0))

    # Today by department
    cursor.execute(f"""
        SELECT COALESCE(e.department, 'Unassigned'),
               COUNT(DISTINCT CASE WHEN a.login_time IS NOT NULL THEN e.employee_id END),
               COUNT(DISTINCT e.employee_id)
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s
        WHERE 1=1 {_co_filter}
        GROUP BY COALESCE(e.department, 'Unassigned')
        ORDER BY COALESCE(e.department, 'Unassigned')
    """, (today,) + _co_args)
    dept_labels, dept_present, dept_absent = [], [], []
    for dept, p, tot in cursor.fetchall():
        dept_labels.append(dept)
        dept_present.append(p or 0)
        dept_absent.append(max((tot or 0) - (p or 0), 0))

    cursor.close(); db.close()
    return jsonify({
        "trend":  {"labels": trend_labels, "present": trend_present, "absent": trend_absent},
        "dept":   {"labels": dept_labels,  "present": dept_present,  "absent": dept_absent},
    })


@attendance_bp.route("/shifts", methods=["GET"])
@admin_required
def shifts():
    return redirect("/settings?tab=shifts")


@attendance_bp.route("/add_shift", methods=["POST"])
@admin_required
def add_shift():
    name  = (request.form.get("shift_name") or request.form.get("name", "")).strip()
    start = request.form.get("start_time", "").strip()
    half  = request.form.get("half_time",  "").strip()
    end   = request.form.get("end_time",   "").strip()
    dest  = request.form.get("redirect") or ("/settings?tab=shifts" if request.form.get("redirect_to") == "settings" else "/settings?tab=shifts")
    cid_raw = request.form.get("company_id", "").strip()
    company_id = int(cid_raw) if cid_raw.isdigit() else None
    if not all([name, start, half, end]):
        return redirect(dest)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        if company_id:
            cursor.execute(
                "INSERT INTO shifts (name, start_time, half_time, end_time, company_id) VALUES (%s,%s,%s,%s,%s)",
                (name, start, half, end, company_id)
            )
        else:
            cursor.execute(
                "INSERT INTO shifts (name, start_time, half_time, end_time) VALUES (%s,%s,%s,%s)",
                (name, start, half, end)
            )
        db.commit()
    except Exception:
        pass
    cursor.close(); db.close()
    return redirect(dest)


@attendance_bp.route("/delete_shift", methods=["POST"])
@admin_required
def delete_shift_form():
    sid = request.form.get("shift_id", "").strip()
    dest = request.form.get("redirect") or "/settings?tab=shifts"
    if not sid:
        return redirect(dest)
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("UPDATE break_config SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("DELETE FROM shifts WHERE id=%s", (sid,))
    db.commit(); cursor.close(); db.close()
    return redirect(dest)


@attendance_bp.route("/delete_shift/<int:sid>", methods=["POST"])
@admin_required
def delete_shift(sid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("UPDATE break_config SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("DELETE FROM shifts WHERE id=%s", (sid,))
    db.commit()
    cursor.close(); db.close()
    dest = request.form.get("redirect") or "/settings?tab=shifts"
    return redirect(dest)


@attendance_bp.route("/edit_shift", methods=["POST"])
@attendance_bp.route("/edit_shift/<int:sid>", methods=["POST"])
@admin_required
def edit_shift(sid=None):
    if sid is None:
        try: sid = int(request.form.get("shift_id", ""))
        except: return redirect("/employees?tab=schedule")
    name  = (request.form.get("shift_name") or request.form.get("name", "")).strip()
    start = request.form.get("start_time", "").strip()
    half  = request.form.get("half_time",  "").strip()
    end   = request.form.get("end_time",   "").strip()
    dest  = request.form.get("redirect") or "/settings?tab=shifts"
    if not all([name, start, half, end]):
        return redirect(dest)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE shifts SET name=%s, start_time=%s, half_time=%s, end_time=%s WHERE id=%s",
        (name, start, half, end, sid)
    )
    db.commit()
    cursor.close(); db.close()
    return redirect(dest)


@attendance_bp.route("/bulk_assign_shift", methods=["POST"])
@admin_required
def bulk_assign_shift():
    shift_id    = request.form.get("shift_id", "").strip()
    emp_ids     = request.form.getlist("emp_ids")
    dept_filter = request.form.get("dept_filter", "").strip()
    dest        = request.form.get("redirect") or "/employees?tab=schedule"
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if emp_ids:
        for emp_id in emp_ids:
            cursor.execute(
                "UPDATE employees SET shift_id=%s WHERE employee_id=%s",
                (shift_id if shift_id else None, emp_id)
            )
    elif dept_filter:
        cursor.execute(
            "UPDATE employees SET shift_id=%s WHERE department=%s",
            (shift_id if shift_id else None, dept_filter)
        )
    else:
        cursor.execute("UPDATE employees SET shift_id=%s", (shift_id if shift_id else None,))
    db.commit()
    cursor.close(); db.close()
    return redirect(dest)


@attendance_bp.route("/update_default_shift", methods=["POST"])
@admin_required
def update_default_shift():
    global SHIFT_START, SHIFT_HALF, SHIFT_END
    start = request.form.get("shift_start", "").strip()
    half  = request.form.get("shift_half",  "").strip()
    end   = request.form.get("shift_end",   "").strip()
    if not all([start, half, end]):
        return redirect("/shifts?error=All+fields+required")
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE company_settings SET shift_start=%s, shift_half=%s, shift_end=%s",
        (start, half, end)
    )
    db.commit()
    cursor.close(); db.close()
    load_default_shift()
    return redirect("/shifts?default_saved=1")


@attendance_bp.route("/assign_shift", methods=["POST"])
@admin_required
def assign_shift():
    emp_id   = request.form.get("emp_id",   "").strip()
    shift_id = request.form.get("shift_id", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE employees SET shift_id=%s WHERE employee_id=%s",
        (shift_id if shift_id else None, emp_id)
    )
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@attendance_bp.route("/submit_shift_swap", methods=["POST"])
@employee_required
def submit_shift_swap():
    requester_id = session["employee_id"]
    target_id    = request.form.get("target_id", "").strip()
    reason       = request.form.get("reason", "").strip()
    if not target_id or target_id == requester_id:
        return redirect("/employee_portal?swap_error=invalid_target#shift-swap")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    # Fetch both employees' current shift_id (must both have shifts assigned)
    cursor.execute("SELECT shift_id FROM employees WHERE employee_id=%s", (requester_id,))
    row_r = cursor.fetchone()
    cursor.execute("SELECT shift_id FROM employees WHERE employee_id=%s", (target_id,))
    row_t = cursor.fetchone()
    if not row_r or not row_t or row_r[0] is None or row_t[0] is None:
        cursor.close(); db.close()
        return redirect("/employee_portal?swap_error=no_shift#shift-swap")
    if row_r[0] == row_t[0]:
        cursor.close(); db.close()
        return redirect("/employee_portal?swap_error=same_shift#shift-swap")
    # Check no open request already exists between them
    cursor.execute("""
        SELECT id FROM shift_swap_requests
        WHERE requester_id=%s AND target_id=%s
          AND status IN ('Pending_Target','Pending_Admin')
    """, (requester_id, target_id))
    if cursor.fetchone():
        cursor.close(); db.close()
        return redirect("/employee_portal?swap_error=duplicate#shift-swap")
    cursor.execute("""
        INSERT INTO shift_swap_requests
            (requester_id, target_id, requester_shift_id, target_shift_id, reason)
        VALUES (%s, %s, %s, %s, %s)
    """, (requester_id, target_id, row_r[0], row_t[0], reason))
    db.commit()
    cursor.close(); db.close()
    return redirect("/employee_portal?swap_sent=1#shift-swap")


@attendance_bp.route("/respond_shift_swap/<int:req_id>", methods=["POST"])
@employee_required
def respond_shift_swap(req_id):
    emp_id   = session["employee_id"]
    action   = request.form.get("action", "")
    response = request.form.get("response", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT id, requester_id, target_id, status
        FROM shift_swap_requests WHERE id=%s AND target_id=%s AND status='Pending_Target'
    """, (req_id, emp_id))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return redirect("/employee_portal?swap_error=not_found#shift-swap")
    if action == "accept":
        cursor.execute("""
            UPDATE shift_swap_requests SET status='Pending_Admin', target_response=%s WHERE id=%s
        """, (response or "Accepted", req_id))
    else:
        cursor.execute("""
            UPDATE shift_swap_requests SET status='Rejected', target_response=%s WHERE id=%s
        """, (response or "Rejected by employee", req_id))
    db.commit()
    cursor.close(); db.close()
    return redirect("/employee_portal?swap_responded=1#shift-swap")


@attendance_bp.route("/admin_shift_swap/<int:req_id>", methods=["POST"])
@admin_required
def admin_shift_swap(req_id):
    action   = request.form.get("action", "")
    response = request.form.get("admin_response", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT requester_id, target_id, requester_shift_id, target_shift_id
        FROM shift_swap_requests WHERE id=%s AND status='Pending_Admin'
    """, (req_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return redirect("/admin_shift_swaps?error=not_found")
    requester_id, target_id, req_shift, tgt_shift = row
    if action == "approve":
        # Swap actual shift assignments
        cursor.execute("UPDATE employees SET shift_id=%s WHERE employee_id=%s", (tgt_shift, requester_id))
        cursor.execute("UPDATE employees SET shift_id=%s WHERE employee_id=%s", (req_shift, target_id))
        cursor.execute("""
            UPDATE shift_swap_requests SET status='Approved', admin_response=%s WHERE id=%s
        """, (response or "Approved by admin", req_id))
    else:
        cursor.execute("""
            UPDATE shift_swap_requests SET status='Rejected_Admin', admin_response=%s WHERE id=%s
        """, (response or "Rejected by admin", req_id))
    db.commit()
    cursor.close(); db.close()
    return redirect("/admin_shift_swaps?ok=1")


@attendance_bp.route("/admin_shift_swaps")
@admin_required
def admin_shift_swaps():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT ssr.id, ssr.requester_id, er.name, ssr.target_id, et.name,
               sr.name AS req_shift, st.name AS tgt_shift,
               ssr.reason, ssr.status, ssr.target_response, ssr.admin_response, ssr.created_at
        FROM shift_swap_requests ssr
        JOIN employees er ON er.employee_id = ssr.requester_id
        JOIN employees et ON et.employee_id = ssr.target_id
        JOIN shifts sr ON sr.id = ssr.requester_shift_id
        JOIN shifts st ON st.id = ssr.target_shift_id
        ORDER BY ssr.created_at DESC LIMIT 100
    """)
    swap_rows = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("admin_shift_swaps.html", swap_rows=swap_rows,
                           ok=request.args.get("ok"),
                           active_nav="employees",
                           error=request.args.get("error"))


@attendance_bp.route("/monthly_report")
@admin_required
def monthly_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    active_cid = session.get("active_company_id")
    if active_cid:
        cursor.execute("SELECT employee_id, name, COALESCE(role,''), COALESCE(phone,''), COALESCE(email,'') FROM employees WHERE company_id=%s ORDER BY name", (active_cid,))
    else:
        cursor.execute("SELECT employee_id, name, COALESCE(role,''), COALESCE(phone,''), COALESCE(email,'') FROM employees ORDER BY name")
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

    holidays     = fetch_holidays_set(year, month)
    working_days = get_working_days(year, month)
    today        = datetime.date.today()

    report = []
    for emp_id, name, role, phone, email in employees:
        emp_att   = att_map.get(emp_id, {})
        full_days = half_days = late_days = absent = 0

        for d in working_days:
            if d > today or d in holidays:
                continue
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
                    absent += 1
            else:
                absent += 1

        billable      = len([d for d in working_days if d <= today and d not in holidays])
        present_equiv = full_days + late_days + half_days * 0.5
        pct           = round(present_equiv / billable * 100, 1) if billable > 0 else 0

        report.append({
            "emp_id":    emp_id,
            "name":      name,
            "role":      role,
            "phone":     phone,
            "email":     email,
            "full_days": full_days,
            "half_days": half_days,
            "late_days": late_days,
            "absent":    absent,
            "billable":  billable,
            "pct":       pct,
        })

    cursor.close()
    db.close()

    months = [(i, datetime.date(year, i, 1).strftime("%B")) for i in range(1, 13)]
    years  = list(range(datetime.date.today().year - 2, datetime.date.today().year + 1))

    return render_template("monthly_report.html",
        report=report,
        month_name=datetime.date(year, month, 1).strftime("%B %Y"),
        active_nav="attendance",
        year=year, month=month,
        months=months, years=years,
        holiday_count=len(holidays),
        total_working=len([d for d in working_days if d <= today and d not in holidays]),
    )


@attendance_bp.route("/employee_attendance_detail/<emp_id>/<int:year>/<int:month>")
@admin_required
def employee_attendance_detail(emp_id, year, month):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute(
        "SELECT employee_id, name, COALESCE(role,''), COALESCE(phone,''), COALESCE(email,'') "
        "FROM employees WHERE employee_id = %s", (emp_id,)
    )
    emp = cursor.fetchone()
    if not emp:
        cursor.close(); db.close()
        return "Employee not found", 404

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance
        WHERE employee_id = %s AND date BETWEEN %s AND %s
        ORDER BY date
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    att_map = {row[0]: row for row in cursor.fetchall()}

    holidays_set = fetch_holidays_set(year, month)
    today = datetime.date.today()

    days = []
    full_days = half_days = late_days = absent = 0
    for d in range(1, last_day + 1):
        date = datetime.date(year, month, d)
        is_sunday  = date.weekday() == 6
        is_holiday = date in holidays_set
        is_future  = date > today
        row = att_map.get(date)

        if row:
            _, login_t, logout_t, status, logout_status, att_type = row
            final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
            login_str  = _td_to_time(login_t).strftime("%I:%M %p")  if login_t  else "—"
            logout_str = _td_to_time(logout_t).strftime("%I:%M %p") if logout_t else "—"
            if not is_future:
                if final == "Full Day":   full_days += 1
                elif final == "Late - Full Day": late_days += 1
                elif final in ("Half Day", "Present"): half_days += 1
                else: absent += 1
        else:
            final      = "—"
            login_str  = "—"
            logout_str = "—"
            if not is_sunday and not is_holiday and not is_future:
                absent += 1

        days.append({
            "date":       date,
            "day_name":   date.strftime("%a"),
            "login":      login_str,
            "logout":     logout_str,
            "status":     final,
            "is_sunday":  is_sunday,
            "is_holiday": is_holiday,
            "is_future":  is_future,
        })

    cursor.close(); db.close()

    months = [(i, datetime.date(year, i, 1).strftime("%B")) for i in range(1, 13)]
    years  = list(range(datetime.date.today().year - 2, datetime.date.today().year + 1))

    return render_template("employee_attendance_detail.html",
        emp=emp,
        days=days,
        month_name=datetime.date(year, month, 1).strftime("%B %Y"),
        active_nav="attendance",
        year=year, month=month,
        months=months, years=years,
        full_days=full_days,
        late_days=late_days,
        half_days=half_days,
        absent=absent,
    )


@attendance_bp.route("/correct_attendance", methods=["POST"])
@admin_required
def correct_attendance():
    emp_id       = request.form.get("emp_id", "").strip()
    date_str     = request.form.get("date", "").strip()
    login_str    = request.form.get("login_time", "").strip()
    logout_str   = request.form.get("logout_time", "").strip()
    att_type     = request.form.get("attendance_type", "").strip()
    year         = request.form.get("year", "")
    month        = request.form.get("month", "")

    if not emp_id or not date_str or not att_type:
        flash("Missing required fields.", "error")
        return redirect(_safe_referrer_redirect(request.referrer or "", "/monthly_report"))

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        flash("Invalid date.", "error")
        return redirect(_safe_referrer_redirect(request.referrer or "", "/monthly_report"))

    login_time  = login_str  if login_str  else None
    logout_time = logout_str if logout_str else None

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, date_obj)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE attendance SET login_time=%s, logout_time=%s, attendance_type=%s, "
            "status='Manual', logout_status='Manual' WHERE employee_id=%s AND date=%s",
            (login_time, logout_time, att_type, emp_id, date_obj)
        )
    else:
        cursor.execute(
            "INSERT INTO attendance (employee_id, date, login_time, logout_time, "
            "attendance_type, status, logout_status) VALUES (%s,%s,%s,%s,%s,'Manual','Manual')",
            (emp_id, date_obj, login_time, logout_time, att_type)
        )
    db.commit()
    cursor.close()
    db.close()

    flash(f"Attendance updated for {date_obj.strftime('%d %b %Y')}.", "success")
    return redirect(f"/employee_attendance_detail/{emp_id}/{year}/{month}")


@attendance_bp.route("/bulk_mark_attendance", methods=["GET", "POST"])
@admin_required
def bulk_mark_attendance():
    today = datetime.date.today()

    if request.method == "POST":
        date_str = request.form.get("date", "").strip()
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            flash("Invalid date.", "error")
            return redirect("/bulk_mark_attendance")

        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT employee_id FROM employees WHERE is_active=1")
        emp_ids = [r[0] for r in cursor.fetchall()]

        saved = 0
        for eid in emp_ids:
            att_type = request.form.get(f"att_{eid}", "").strip()
            if not att_type:
                continue
            login_t  = request.form.get(f"login_{eid}", "").strip() or None
            logout_t = request.form.get(f"logout_{eid}", "").strip() or None
            cursor.execute("SELECT id FROM attendance WHERE employee_id=%s AND date=%s", (eid, date_obj))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE attendance SET login_time=%s, logout_time=%s, attendance_type=%s, "
                    "status='Manual', logout_status='Manual' WHERE employee_id=%s AND date=%s",
                    (login_t, logout_t, att_type, eid, date_obj)
                )
            else:
                cursor.execute(
                    "INSERT INTO attendance (employee_id, date, login_time, logout_time, "
                    "attendance_type, status, logout_status) VALUES (%s,%s,%s,%s,%s,'Manual','Manual')",
                    (eid, date_obj, login_t, logout_t, att_type)
                )
            saved += 1
        db.commit()
        cursor.close(); db.close()
        flash(f"Attendance saved for {saved} employee(s) on {date_obj.strftime('%d %b %Y')}.", "success")
        return redirect(f"/bulk_mark_attendance?date={date_str}")

    date_str = request.args.get("date", today.isoformat())
    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        date_obj = today
        date_str = today.isoformat()

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    base_select = (
        "SELECT e.employee_id, e.name, COALESCE(e.department,''), COALESCE(e.designation,''), "
        "COALESCE(s.name,''), COALESCE(TO_CHAR(s.start_time,'HH24:MI'),''), "
        "COALESCE(TO_CHAR(s.end_time,'HH24:MI'),''), "
        "COALESCE(e.phone,''), COALESCE(e.email,''), "
        "COALESCE(e.work_mode,'office'), COALESCE(TO_CHAR(e.date_of_joining,'YYYY-MM-DD'),''), "
        "COALESCE(e.gender,''), COALESCE(e.role,'') "
        "FROM employees e LEFT JOIN shifts s ON s.id=e.shift_id "
    )
    active_cid = session.get("active_company_id")
    if active_cid:
        cursor.execute(base_select + "WHERE e.is_active=1 AND e.company_id=%s ORDER BY e.name", (active_cid,))
    else:
        cursor.execute(base_select + "WHERE e.is_active=1 ORDER BY e.name")
    employees = cursor.fetchall()

    cursor.execute(
        "SELECT employee_id, login_time, logout_time, attendance_type "
        "FROM attendance WHERE date=%s", (date_obj,)
    )
    att_map = {r[0]: r for r in cursor.fetchall()}

    # Monthly summary for the selected date's month
    cursor.execute(
        """SELECT employee_id,
             SUM(CASE WHEN attendance_type IN ('Full Day','Late - Full Day') THEN 1 ELSE 0 END) AS present_days,
             SUM(CASE WHEN attendance_type = 'Half Day' THEN 1 ELSE 0 END) AS half_days,
             SUM(CASE WHEN attendance_type = 'Absent' THEN 1 ELSE 0 END) AS absent_days,
             SUM(CASE WHEN attendance_type = 'Leave' THEN 1 ELSE 0 END) AS leave_days,
             COUNT(*) AS total_marked
           FROM attendance
           WHERE EXTRACT(YEAR FROM date)=%s AND EXTRACT(MONTH FROM date)=%s
           GROUP BY employee_id""",
        (date_obj.year, date_obj.month)
    )
    month_summary = {r[0]: r for r in cursor.fetchall()}

    co = get_company_settings()
    pending_leaves      = 0
    pending_resignations = 0
    pending_tickets     = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'"); pending_leaves = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'"); pending_resignations = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'"); pending_tickets = cursor.fetchone()[0]
    except Exception:
        pass
    cursor.close(); db.close()

    return render_template("bulk_attendance.html",
        co=co, employees=employees, att_map=att_map,
        month_summary=month_summary,
        date_str=date_str, date_obj=date_obj,
        today=today, pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    
        active_nav="attendance",
    )


@attendance_bp.route("/monthly_report_export")
@admin_required
def monthly_report_export():
    from flask import send_file
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
    employees = cursor.fetchall()

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT employee_id, date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))

    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    holidays     = fetch_holidays_set(year, month)
    working_days = get_working_days(year, month)
    today        = datetime.date.today()
    cursor.close(); db.close()

    report = []
    for emp_id, name in employees:
        emp_att   = att_map.get(emp_id, {})
        full_days = half_days = late_days = absent = 0
        for d in working_days:
            if d > today or d in holidays:
                continue
            row = emp_att.get(d)
            if row:
                _, _, login_t, logout_t, status, _ls, att_type = row
                final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
                if final == "Full Day":       full_days += 1
                elif final == "Late - Full Day": late_days += 1
                elif final in ("Half Day", "Present"): half_days += 1
                else: absent += 1
            else:
                absent += 1
        billable      = len([d for d in working_days if d <= today and d not in holidays])
        present_equiv = full_days + late_days + half_days * 0.5
        pct           = round(present_equiv / billable * 100, 1) if billable > 0 else 0
        report.append({"emp_id": emp_id, "name": name, "full_days": full_days,
                        "late_days": late_days, "half_days": half_days,
                        "absent": absent, "billable": billable, "pct": pct})

    month_name = datetime.date(year, month, 1).strftime("%B %Y")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    # ── styles ──
    hdr_fill   = PatternFill("solid", fgColor="1E3A8A")
    hdr_font   = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(bold=True, size=13, color="1E3A8A")
    center     = Alignment(horizontal="center", vertical="center")
    thin       = Side(style="thin", color="DBEAFE")
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill   = PatternFill("solid", fgColor="EFF6FF")

    # ── title row ──
    ws.merge_cells("A1:H1")
    ws["A1"] = f"Monthly Attendance Report — {month_name}"
    ws["A1"].font      = title_font
    ws["A1"].alignment = center
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Working Days: {len([d for d in working_days if d <= today and d not in holidays])}   |   Holidays: {len(holidays)}   |   Employees: {len(report)}"
    ws["A2"].alignment = center
    ws["A2"].font = Font(size=10, color="64748B")
    ws.row_dimensions[2].height = 18

    # ── header row ──
    headers = ["Emp ID", "Name", "Full Days", "Late Days", "Half Days", "Absent", "Working Days", "Attendance %"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.fill      = hdr_fill
        cell.font      = hdr_font
        cell.alignment = center
        cell.border    = border
    ws.row_dimensions[3].height = 22

    # ── data rows ──
    for i, r in enumerate(report, 4):
        row_fill = alt_fill if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        values = [r["emp_id"], r["name"], r["full_days"], r["late_days"],
                  r["half_days"], r["absent"], r["billable"], r["pct"]]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.fill      = row_fill
            cell.alignment = center if col != 2 else Alignment(horizontal="left", vertical="center")
            cell.border    = border
            if col == 8:  # Attendance %
                pct_val = val
                if pct_val >= 90:   cell.font = Font(color="15803D", bold=True)
                elif pct_val >= 70: cell.font = Font(color="D97706", bold=True)
                else:               cell.font = Font(color="DC2626", bold=True)

    # ── column widths ──
    col_widths = [12, 24, 12, 12, 12, 10, 14, 14]
    for col, w in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = w

    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"attendance_{year}_{month:02d}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@attendance_bp.route("/send_absentee_report", methods=["POST"])
@admin_required
def send_absentee_report():
    cfg = get_email_config()
    if not cfg:
        return jsonify({"ok": False, "msg": "Email not configured. Go to Email Settings first."})

    today  = datetime.date.today()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
    all_emp = cursor.fetchall()

    cursor.execute("SELECT DISTINCT employee_id FROM attendance WHERE date=%s", (today,))
    present_ids = {r[0] for r in cursor.fetchall()}
    cursor.close(); db.close()

    absentees = [(eid, nm) for eid, nm in all_emp if eid not in present_ids]
    total     = len(all_emp)
    absent    = len(absentees)
    present   = total - absent

    rows_html = "".join(
        f"<tr><td style='padding:8px 14px;border-bottom:1px solid #e2e8f0;'>{eid}</td>"
        f"<td style='padding:8px 14px;border-bottom:1px solid #e2e8f0;'>{nm}</td></tr>"
        for eid, nm in absentees
    ) or "<tr><td colspan='2' style='padding:14px;text-align:center;color:#16a34a;'>All employees present!</td></tr>"

    html = f"""
<div style="font-family:Segoe UI,sans-serif;max-width:600px;margin:auto;background:#f8fafc;border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:#1e3a8a;padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">&#127970; Daily Absentee Report</div>
    <div style="font-size:13px;opacity:0.75;margin-top:4px;">{today.strftime('%A, %d %B %Y')}</div>
  </div>
  <div style="padding:24px;">
    <div style="display:flex;gap:16px;margin-bottom:24px;">
      <div style="flex:1;background:#dcfce7;border-radius:10px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:700;color:#15803d;">{present}</div>
        <div style="font-size:12px;color:#166534;">Present</div>
      </div>
      <div style="flex:1;background:#fee2e2;border-radius:10px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:700;color:#dc2626;">{absent}</div>
        <div style="font-size:12px;color:#991b1b;">Absent</div>
      </div>
      <div style="flex:1;background:#dbeafe;border-radius:10px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:700;color:#1d4ed8;">{total}</div>
        <div style="font-size:12px;color:#1e40af;">Total</div>
      </div>
    </div>
    <table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;border:1px solid #dbeafe;">
      <thead>
        <tr style="background:#dbeafe;">
          <th style="padding:10px 14px;text-align:left;color:#1e3a8a;font-size:13px;">Employee ID</th>
          <th style="padding:10px 14px;text-align:left;color:#1e3a8a;font-size:13px;">Name</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""

    try:
        send_email_smtp(cfg.get("from_email", cfg["user"]), f"Daily Absentee Report — {today.strftime('%d %b %Y')}", html, cfg)
        return jsonify({"ok": True, "msg": f"Report sent! {absent} absent out of {total} employees."})
    except Exception:
        app_log.error("Failed to send absentee report email", exc_info=True)
        return jsonify({"ok": False, "msg": "Failed to send email. Check email settings."})


@attendance_bp.route("/location", methods=["POST"])
def location():
    data = request.get_json()
    session["lat"] = data["lat"]
    session["lon"] = data["lon"]
    return jsonify({"status": "ok"})


@attendance_bp.route("/attendance", methods=["POST"])
def attendance():
    import base64, io
    import numpy as np
    from PIL import Image

    data       = request.get_json() or {}
    emp_id     = data.get("employee_id", "").strip()
    face_b64   = data.get("face_image", "")
    user_lat   = data.get("lat")
    user_lon   = data.get("lon")
    auth_combo = data.get("auth_combo", "qr_face")

    if auth_combo not in ("qr_face", "qr_only", "qr_fingerprint", "fingerprint_only"):
        return jsonify({"ok": False, "msg": "Invalid auth combination."})

    if not emp_id:
        err_msg = "Employee ID is required." if auth_combo == "fingerprint_only" else "No QR code data received."
        return jsonify({"ok": False, "msg": err_msg})

    cfg = get_auth_config()

    if auth_combo in ("qr_fingerprint", "fingerprint_only"):
        if not cfg["fingerprint_enabled"]:
            return jsonify({"ok": False, "msg": "Fingerprint not enabled. Ask your admin to enable it in Settings."}), 403
        # Real, server-verified, one-time, employee-bound proof from
        # /api/employee/webauthn-verify-challenge — not a client-supplied flag.
        if not _wa_fingerprint_recently_verified(emp_id):
            return jsonify({"ok": False, "msg": "Fingerprint verification failed. Please try again."}), 401

    needs_face = (auth_combo == "qr_face")
    if needs_face and not face_b64:
        return jsonify({"ok": False, "msg": "Face photo not captured."})

    frame = None
    if needs_face:
        try:
            img_bytes = base64.b64decode(face_b64)
            pil_img   = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            frame     = np.array(pil_img)
        except Exception:
            return jsonify({"ok": False, "msg": "Invalid face image data."})

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT face_image, name, email, work_mode, work_lat, work_lon "
        "FROM employees WHERE employee_id=%s", (emp_id,))
    result = cursor.fetchone()

    if not result:
        cursor.close(); db.close()
        not_found_msg = ("Employee ID not found. Please check your ID and try again."
                         if auth_combo == "fingerprint_only"
                         else "Employee not found. Please check your QR code.")
        return jsonify({"ok": False, "msg": not_found_msg})

    face_path, employee_name, employee_email, emp_work_mode, emp_work_lat, emp_work_lon = result

    # Location check
    if cfg["location_enabled"] and (not user_lat or not user_lon):
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Location not captured. Please allow location access."})
    if cfg["location_enabled"] and user_lat and user_lon:
        if emp_work_mode == 'wfh':
            if emp_work_lat and emp_work_lon:
                if not is_within_range(float(user_lat), float(user_lon), float(emp_work_lat), float(emp_work_lon)):
                    cursor.close(); db.close()
                    return jsonify({"ok": False, "msg": "You are outside your registered home location."})
        else:
            if not is_within_range(float(user_lat), float(user_lon), OFFICE_LAT, OFFICE_LON):
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "You are outside the office premises."})

    # Face recognition (only for qr_face combo)
    known_encoding = None
    if needs_face:
        if not _face_recognition_available:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face recognition is currently unavailable on this server. Contact your admin."})
        if not os.path.exists(face_path):
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face image missing. Please re-register."})
        known_encoding = _get_known_face_encoding(emp_id, face_path)
        if known_encoding is None:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Stored face image is invalid. Please re-register."})

    if needs_face:
        locs = face_recognition.face_locations(frame)
        encs = face_recognition.face_encodings(frame, locs)
        if not encs:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "No face detected in photo. Look directly at the camera."})
        matched = any(
            True in face_recognition.compare_faces([known_encoding], enc)
            for enc in encs
        )
        if not matched:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face does not match. Please try again."})

    now          = datetime.datetime.now()
    today        = now.date()
    current_time = now.time()

    cursor.execute(
        "SELECT login_time, logout_time, status, worked_minutes, last_relogin "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record              = cursor.fetchone()
    login_time          = record[0] if record else None
    logout_time         = record[1] if record else None
    login_status_stored = record[2] if record else None
    worked_mins_stored  = (record[3] or 0) if record else 0
    last_relogin_stored = record[4] if record else None

    # Use employee's assigned shift, or global defaults
    s_start, s_half, s_end, shift_name = get_employee_shift(emp_id, cursor)

    if not login_time:
        grace_time = (datetime.datetime.combine(today, s_start) + datetime.timedelta(minutes=GRACE_MINUTES)).time()
        if current_time <= grace_time:
            login_status = "Full Day Login"
        elif current_time <= s_half:
            login_status = "Late Login"
        else:
            login_status = "Half Day Login"
        cursor.execute(
            "INSERT INTO attendance (employee_id, date, login_time, status) VALUES (%s,%s,%s,%s)",
            (emp_id, today, current_time, login_status)
        )
        db.commit(); cursor.close(); db.close()
        time_str = current_time.strftime("%H:%M:%S")
        return jsonify({"ok": True, "type": "login", "name": employee_name,
                        "status": login_status, "time": time_str, "shift": shift_name,
                        "work_mode": emp_work_mode})

    elif not logout_time:
        # Determine session start (re-login time if present, else first login)
        session_start = last_relogin_stored if last_relogin_stored else login_time
        if not isinstance(session_start, datetime.time):
            session_start = _td_to_time(session_start)
        cur_dt    = datetime.datetime.combine(today, current_time)
        start_dt  = datetime.datetime.combine(today, session_start)
        session_m = max(0, int((cur_dt - start_dt).total_seconds() / 60))
        total_m   = worked_mins_stored + session_m

        if current_time < s_half:
            logout_status = "Half Day Logout"
        elif current_time < s_end:
            logout_status = "Early Logout"
        else:
            logout_status = "Completed"
        # Overtime: minutes beyond shift end
        now_mins   = current_time.hour * 60 + current_time.minute
        end_mins   = s_end.hour * 60 + s_end.minute
        overtime_m = max(0, now_mins - end_mins)
        att_type = classify_by_worked_minutes(login_status_stored, total_m, s_start, s_end)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s, worked_minutes=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, logout_status, att_type, total_m, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        detect_overtime(emp_id, today, current_time)
        time_str = current_time.strftime("%H:%M:%S")
        resp = {"ok": True, "type": "logout", "name": employee_name,
                "status": logout_status, "att_type": att_type,
                "time": time_str, "shift": shift_name, "work_mode": emp_work_mode}
        if overtime_m > 0:
            resp["overtime"] = f"{overtime_m // 60}h {overtime_m % 60}m" if overtime_m >= 60 else f"{overtime_m}m"
        return jsonify(resp)

    else:
        # Re-login after a break — re-open the session
        # worked_minutes was already saved on the previous logout, so just set last_relogin
        cursor.execute(
            "UPDATE attendance SET logout_time=NULL, last_relogin=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        time_str = current_time.strftime("%H:%M:%S")
        return jsonify({"ok": True, "type": "relogin", "name": employee_name,
                        "status": "Re-Login", "time": time_str, "shift": shift_name,
                        "work_mode": emp_work_mode})


@attendance_bp.route("/my_attendance_pdf")
@employee_required
def my_attendance_pdf():
    emp_id = session["employee_id"]
    year   = int(request.args.get("year",  datetime.date.today().year))
    month  = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name, role, email FROM employees WHERE employee_id=%s", (emp_id,))
    emp = cursor.fetchone()

    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE employee_id=%s AND date BETWEEN %s AND %s ORDER BY date
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    monthly_att = cursor.fetchall()
    cursor.close(); db.close()

    billable_past = get_billable_past_days(year, month)
    att_by_date   = {r[0]: r for r in monthly_att}
    full_days = half_days = late_days = absent_days = total_sec = 0
    for d in billable_past:
        row = att_by_date.get(d)
        if row:
            _, login_t, logout_t, status, _ls, att_type = row
            final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
            if   final == "Full Day":               full_days   += 1
            elif final == "Late - Full Day":        late_days   += 1
            elif final in ("Half Day", "Present"):  half_days   += 1
            else:                                   absent_days += 1
            if login_t and logout_t:
                li = login_t.total_seconds()  if hasattr(login_t,  "total_seconds") else login_t.hour*3600+login_t.minute*60+login_t.second
                lo = logout_t.total_seconds() if hasattr(logout_t, "total_seconds") else logout_t.hour*3600+logout_t.minute*60+logout_t.second
                if lo > li: total_sec += int(lo - li)
        else:
            absent_days += 1

    def fmt(t):
        if t is None: return "--"
        if hasattr(t, "strftime"): return t.strftime("%H:%M")
        s = int(t.total_seconds()); return f"{s//3600:02d}:{(s%3600)//60:02d}"

    rows_html = ""
    for d in sorted(att_by_date.keys()):
        row = att_by_date[d]
        _, lt, lot, ls, _lo, at = row
        final = at if at else infer_type_legacy(ls, lt, lot)
        color = {"Full Day":"#16a34a","Late - Full Day":"#d97706","Half Day":"#dc2626","Present":"#d97706"}.get(final,"#6b7280")
        rows_html += f"<tr><td>{d.strftime('%d %b %Y')}</td><td>{d.strftime('%A')}</td><td>{fmt(lt)}</td><td>{fmt(lot)}</td><td style='color:{color};font-weight:600;'>{final or 'Absent'}</td></tr>"

    billable = len(billable_past)
    pct = round((full_days + late_days + half_days*0.5) / billable * 100, 1) if billable else 0
    month_name = datetime.date(year, month, 1).strftime("%B %Y")
    total_h = f"{total_sec//3600}h {(total_sec%3600)//60}m"

    html = f"""<!doctype html><html><head><meta charset="UTF-8">
<title>Attendance Report — {emp[1]} — {month_name}</title>
<style>
  body {{ font-family: "Segoe UI", sans-serif; margin: 0; padding: 32px; color: #1e293b; background: white; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; border-bottom: 2px solid #1e3a8a; padding-bottom: 18px; }}
  .title {{ font-size: 22px; font-weight: 700; color: #1e3a8a; }}
  .sub {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
  .meta {{ text-align: right; font-size: 13px; color: #64748b; }}
  .stats {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 24px; }}
  .stat {{ background: #f8fafc; border: 1px solid #dbeafe; border-radius: 10px; padding: 12px; text-align: center; }}
  .stat .n {{ font-size: 24px; font-weight: 700; }}
  .stat .l {{ font-size: 11px; color: #64748b; margin-top: 3px; }}
  .c-green {{ color: #16a34a; }} .c-yellow {{ color: #d97706; }} .c-red {{ color: #dc2626; }} .c-blue {{ color: #2563eb; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #1e3a8a; color: white; padding: 10px 12px; text-align: left; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #e2e8f0; }}
  tr:last-child td {{ border-bottom: none; }}
  .footer {{ margin-top: 24px; font-size: 11px; color: #94a3b8; text-align: center; }}
  @media print {{ body {{ padding: 16px; }} button {{ display: none; }} }}
</style></head><body>
<div class="header">
  <div><div class="title">Attendance Report</div>
    <div class="sub">{emp[1]} &nbsp;·&nbsp; {emp[0]} &nbsp;·&nbsp; {emp[2] or 'Employee'}</div>
    <div class="sub">{month_name}</div></div>
  <div class="meta">Generated: {datetime.date.today().strftime('%d %b %Y')}<br>
    <button onclick="window.print()" style="margin-top:8px;padding:8px 16px;background:#1e3a8a;color:white;border:none;border-radius:8px;cursor:pointer;font-size:13px;">🖨️ Print / Save PDF</button>
  </div>
</div>
<div class="stats">
  <div class="stat"><div class="n c-green">{full_days}</div><div class="l">Full Days</div></div>
  <div class="stat"><div class="n c-yellow">{late_days}</div><div class="l">Late Days</div></div>
  <div class="stat"><div class="n c-yellow">{half_days}</div><div class="l">Half Days</div></div>
  <div class="stat"><div class="n c-red">{absent_days}</div><div class="l">Absent</div></div>
  <div class="stat"><div class="n c-blue">{pct}%</div><div class="l">Attendance</div></div>
  <div class="stat"><div class="n c-blue">{total_h}</div><div class="l">Total Hours</div></div>
</div>
<table><thead><tr><th>Date</th><th>Day</th><th>Login</th><th>Logout</th><th>Status</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<div class="footer">Employee Attendance System &nbsp;·&nbsp; {emp[1]} &nbsp;·&nbsp; {month_name}</div>
</body></html>"""
    return html


@attendance_bp.route("/api/monthly_report", methods=["GET"])
@api_required
def api_monthly_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
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
    holidays     = fetch_holidays_set(year, month)
    working_days = get_working_days(year, month)
    today        = datetime.date.today()
    report = []
    for emp_id, name in employees:
        emp_att   = att_map.get(emp_id, {})
        full_days = half_days = late_days = absent = 0
        for d in working_days:
            if d > today or d in holidays:
                continue
            row = emp_att.get(d)
            if row:
                _, _, login_t, logout_t, status, _logout_status, att_type = row
                final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
                if final in ("Full Day", "Approved Leave"): full_days += 1
                elif final == "Late - Full Day": late_days += 1
                elif final in ("Half Day", "Present"): half_days += 1
                else: absent += 1
            else:
                absent += 1
        billable      = len([d for d in working_days if d <= today and d not in holidays])
        present_equiv = full_days + late_days + half_days * 0.5
        pct           = round(present_equiv / billable * 100, 1) if billable > 0 else 0
        report.append({"employee_id": emp_id, "name": name, "full_days": full_days,
                        "half_days": half_days, "late_days": late_days, "absent": absent,
                        "billable": billable, "pct": pct})
    return jsonify({"ok": True, "report": report,
                    "month_name": datetime.date(year, month, 1).strftime("%B %Y"),
                    "year": year, "month": month,
                    "holiday_count": len(holidays),
                    "total_working": len([d for d in working_days if d <= today and d not in holidays])})


@attendance_bp.route("/api/attendance/checkin", methods=["POST"])
@api_required
def api_checkin():
    data   = request.get_json() or {}
    emp_id = data.get("employee_id")
    lat    = data.get("lat")
    lon    = data.get("lon")
    if not emp_id:
        return jsonify({"ok": False, "msg": "employee_id required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT name, work_mode, work_lat, work_lon FROM employees WHERE employee_id=%s", (emp_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found."})
    employee_name, emp_work_mode, emp_work_lat, emp_work_lon = result
    if lat and lon:
        if emp_work_mode == 'wfh':
            if emp_work_lat and emp_work_lon:
                if not is_within_range(float(lat), float(lon), float(emp_work_lat), float(emp_work_lon)):
                    cursor.close(); db.close()
                    return jsonify({"ok": False, "msg": "You are outside your registered home location."})
        else:
            if not is_within_range(float(lat), float(lon), OFFICE_LAT, OFFICE_LON):
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "You are outside the office premises."})
    now           = datetime.datetime.now()
    today         = now.date()
    current_time  = now.time()
    cursor.execute(
        "SELECT login_time, logout_time, status, worked_minutes, last_relogin "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record              = cursor.fetchone()
    login_time          = record[0] if record else None
    logout_time         = record[1] if record else None
    login_status_stored = record[2] if record else None
    worked_mins_stored  = (record[3] or 0) if record else 0
    last_relogin_stored = record[4] if record else None
    if not login_time:
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=GRACE_MINUTES)).time()
        if current_time <= grace_time:
            login_status = "Full Day Login"
        elif current_time <= SHIFT_HALF:
            login_status = "Late Login"
        else:
            login_status = "Half Day Login"
        cursor.execute(
            "INSERT INTO attendance (employee_id, date, login_time, status) VALUES (%s,%s,%s,%s)",
            (emp_id, today, current_time, login_status)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "type": "login", "name": employee_name,
                        "status": login_status, "time": current_time.strftime("%H:%M:%S")})
    elif not logout_time:
        session_start = last_relogin_stored if last_relogin_stored else login_time
        if not isinstance(session_start, datetime.time):
            session_start = _td_to_time(session_start)
        cur_dt    = datetime.datetime.combine(today, current_time)
        start_dt  = datetime.datetime.combine(today, session_start)
        session_m = max(0, int((cur_dt - start_dt).total_seconds() / 60))
        total_m   = worked_mins_stored + session_m
        if current_time < SHIFT_HALF:
            logout_status = "Half Day Logout"
        elif current_time < SHIFT_END:
            logout_status = "Early Logout"
        else:
            logout_status = "Completed"
        att_type = classify_by_worked_minutes(login_status_stored, total_m, SHIFT_START, SHIFT_END)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s, worked_minutes=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, logout_status, att_type, total_m, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        detect_overtime(emp_id, today, current_time)
        return jsonify({"ok": True, "type": "logout", "name": employee_name,
                        "status": logout_status, "att_type": att_type,
                        "time": current_time.strftime("%H:%M:%S")})
    else:
        cursor.execute(
            "UPDATE attendance SET logout_time=NULL, last_relogin=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "type": "relogin", "name": employee_name,
                        "status": "Re-Login", "time": current_time.strftime("%H:%M:%S")})


@attendance_bp.route("/api/employee/checkin", methods=["POST"])
@employee_api_required
def api_employee_checkin():
    from flask import g as _g
    emp_id = _g.api_emp_id
    data   = request.get_json() or {}
    lat    = data.get("lat")
    lon    = data.get("lon")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name, work_mode, work_lat, work_lon FROM employees WHERE employee_id=%s", (emp_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    employee_name, work_mode, work_lat, work_lon = result

    if lat and lon:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (ValueError, TypeError):
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Invalid lat/lon values."}), 400
        if work_mode == 'wfh':
            if work_lat and work_lon:
                if not is_within_range(lat_f, lon_f, float(work_lat), float(work_lon)):
                    cursor.close(); db.close()
                    return jsonify({"ok": False, "msg": "You are outside your registered home location."})
        else:
            if not is_within_range(lat_f, lon_f, OFFICE_LAT, OFFICE_LON):
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "You are outside the office premises."})

    punched_at_str = data.get("punched_at")
    now = datetime.datetime.now()
    if punched_at_str:
        try:
            _pt = datetime.datetime.fromisoformat(punched_at_str.replace("Z", "+00:00"))
            _pt = _pt.replace(tzinfo=None)
            if (now - _pt).total_seconds() <= 86400:
                now = _pt
            else:
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "Offline punch too old (>24 h). Rejected."}), 400
        except (ValueError, TypeError):
            pass

    today        = now.date()
    current_time = now.time()

    cursor.execute(
        "SELECT login_time, logout_time, status, worked_minutes, last_relogin "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record              = cursor.fetchone()
    login_time          = record[0] if record else None
    logout_time         = record[1] if record else None
    login_status        = record[2] if record else None
    worked_mins_stored  = (record[3] or 0) if record else 0
    last_relogin_stored = record[4] if record else None

    if not login_time:
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=GRACE_MINUTES)).time()
        if current_time <= grace_time:
            status = "Full Day Login"
        elif current_time <= SHIFT_HALF:
            status = "Late Login"
        else:
            status = "Half Day Login"
        cursor.execute(
            "INSERT INTO attendance (employee_id, date, login_time, status) VALUES (%s,%s,%s,%s)",
            (emp_id, today, current_time, status)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "action": "login", "name": employee_name,
                        "status": status, "time": current_time.strftime("%H:%M:%S")})
    elif not logout_time:
        session_start = last_relogin_stored if last_relogin_stored else login_time
        if not isinstance(session_start, datetime.time):
            session_start = _td_to_time(session_start)
        cur_dt    = datetime.datetime.combine(today, current_time)
        start_dt  = datetime.datetime.combine(today, session_start)
        session_m = max(0, int((cur_dt - start_dt).total_seconds() / 60))
        total_m   = worked_mins_stored + session_m
        if current_time < SHIFT_HALF:
            out_status = "Half Day Logout"
        elif current_time < SHIFT_END:
            out_status = "Early Logout"
        else:
            out_status = "Completed"
        att_type = classify_by_worked_minutes(login_status, total_m, SHIFT_START, SHIFT_END)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s, worked_minutes=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, out_status, att_type, total_m, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        detect_overtime(emp_id, today, current_time)
        return jsonify({"ok": True, "action": "logout", "name": employee_name,
                        "status": out_status, "att_type": att_type,
                        "time": current_time.strftime("%H:%M:%S")})
    else:
        cursor.execute(
            "UPDATE attendance SET logout_time=NULL, last_relogin=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "action": "relogin", "name": employee_name,
                        "status": "Re-Login", "time": current_time.strftime("%H:%M:%S")})


@attendance_bp.route("/api/employee/qr-face-checkin", methods=["POST"])
@limiter.limit("20 per minute")
def api_employee_qr_face_checkin():
    """Public kiosk endpoint — supports auth_combo: qr_face | qr_fingerprint | face_fingerprint."""
    employee_id        = request.form.get("employee_id", "").strip().upper()
    lat                = request.form.get("lat")
    lon                = request.form.get("lon")
    face_photo         = request.files.get("face_photo")
    auth_combo         = request.form.get("auth_combo", "qr_face")

    if auth_combo not in ("qr_face", "qr_fingerprint", "face_fingerprint"):
        return jsonify({"ok": False, "msg": "Invalid auth_combo"}), 400

    if not employee_id:
        return jsonify({"ok": False, "msg": "employee_id required"}), 400

    cfg = get_auth_config()

    if auth_combo in ("qr_face", "qr_fingerprint") and not cfg["qr_enabled"]:
        return jsonify({"ok": False, "msg": "QR code authentication is not enabled"}), 403
    if auth_combo in ("qr_face", "face_fingerprint") and not cfg["face_enabled"]:
        return jsonify({"ok": False, "msg": "Face recognition authentication is not enabled"}), 403
    if auth_combo in ("qr_fingerprint", "face_fingerprint"):
        if not cfg["fingerprint_enabled"]:
            return jsonify({"ok": False, "msg": "Fingerprint authentication is not enabled"}), 403
        # Real, server-verified, one-time, employee-bound proof from either
        # /api/employee/webauthn-verify-challenge (web kiosk, session-based)
        # or /api/employee/mobile-biometric-attest (mobile app, Bearer-token-
        # bound) — never a raw client-supplied flag.
        if not (_wa_fingerprint_recently_verified(employee_id)
                or _mobile_biometric_recently_verified(employee_id)):
            return jsonify({"ok": False, "msg": "Fingerprint verification failed. Please try again."}), 401

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT name, work_mode, work_lat, work_lon, face_image FROM employees WHERE employee_id=%s",
        (employee_id,)
    )
    result = cursor.fetchone()
    if not result:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    employee_name, work_mode, work_lat, work_lon, registered_face = result

    if lat and lon:
        try:
            if work_mode == 'wfh':
                if work_lat and work_lon:
                    if not is_within_range(float(lat), float(lon), float(work_lat), float(work_lon)):
                        cursor.close(); db.close()
                        return jsonify({"ok": False, "msg": "You are outside your registered home location."})
            else:
                if not is_within_range(float(lat), float(lon), OFFICE_LAT, OFFICE_LON):
                    cursor.close(); db.close()
                    return jsonify({"ok": False, "msg": "You are outside the office premises."})
        except (ValueError, TypeError):
            pass

    needs_face = auth_combo in ("qr_face", "face_fingerprint")
    if needs_face:
        if not face_photo:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face photo required for this authentication method."}), 400
        if not _face_recognition_available:
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face recognition is currently unavailable on this server. Contact your admin."}), 503
        if not registered_face or not os.path.exists(registered_face):
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "No registered face found. Please contact your admin."}), 400
        try:
            from PIL import Image as _PILImage
            face_dir = os.path.join(UPLOAD_FOLDER, "face_logs")
            os.makedirs(face_dir, exist_ok=True)
            ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            face_path = os.path.join(face_dir, f"{employee_id}_{ts}.jpg")
            img = _PILImage.open(face_photo.stream).convert("RGB")
            img.save(face_path, "JPEG", quality=80)

            known_enc      = _get_known_face_encoding(employee_id, registered_face)
            test_img_data  = face_recognition.load_image_file(face_path)
            test_encs      = face_recognition.face_encodings(test_img_data)
            if known_enc is None or not test_encs:
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "Face not detected clearly. Please retake the photo."}), 400
            if not face_recognition.compare_faces([known_enc], test_encs[0], tolerance=0.5)[0]:
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "Face did not match. Please try again."}), 401
        except Exception:
            app_log.error("Face verification error", exc_info=True)
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Face verification failed. Please retake the photo."}), 500
    elif face_photo:
        try:
            from PIL import Image as _PILImage
            face_dir = os.path.join(UPLOAD_FOLDER, "face_logs")
            os.makedirs(face_dir, exist_ok=True)
            ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            face_path = os.path.join(face_dir, f"{employee_id}_{ts}.jpg")
            img = _PILImage.open(face_photo.stream).convert("RGB")
            img.save(face_path, "JPEG", quality=80)
        except Exception:
            pass

    now          = datetime.datetime.now()
    today        = now.date()
    current_time = now.time()

    cursor.execute(
        "SELECT login_time, logout_time, status, worked_minutes, last_relogin "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (employee_id, today)
    )
    record             = cursor.fetchone()
    login_time         = record[0] if record else None
    logout_time        = record[1] if record else None
    login_status       = record[2] if record else None
    worked_mins_stored = (record[3] or 0) if record else 0
    last_relogin_stored = record[4] if record else None

    if not login_time:
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=GRACE_MINUTES)).time()
        if current_time <= grace_time:
            status = "Full Day Login"
        elif current_time <= SHIFT_HALF:
            status = "Late Login"
        else:
            status = "Half Day Login"
        cursor.execute(
            "INSERT INTO attendance (employee_id, date, login_time, status) VALUES (%s,%s,%s,%s)",
            (employee_id, today, current_time, status)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "action": "login", "name": employee_name,
                        "status": status, "time": current_time.strftime("%H:%M:%S")})
    elif not logout_time:
        session_start = last_relogin_stored if last_relogin_stored else login_time
        if not isinstance(session_start, datetime.time):
            session_start = _td_to_time(session_start)
        cur_dt    = datetime.datetime.combine(today, current_time)
        start_dt  = datetime.datetime.combine(today, session_start)
        session_m = max(0, int((cur_dt - start_dt).total_seconds() / 60))
        total_m   = worked_mins_stored + session_m
        if current_time < SHIFT_HALF:
            out_status = "Half Day Logout"
        elif current_time < SHIFT_END:
            out_status = "Early Logout"
        else:
            out_status = "Completed"
        att_type = classify_by_worked_minutes(login_status, total_m, SHIFT_START, SHIFT_END)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s, worked_minutes=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, out_status, att_type, total_m, employee_id, today)
        )
        db.commit(); cursor.close(); db.close()
        detect_overtime(employee_id, today, current_time)
        return jsonify({"ok": True, "action": "logout", "name": employee_name,
                        "status": out_status, "att_type": att_type,
                        "time": current_time.strftime("%H:%M:%S")})
    else:
        cursor.execute(
            "UPDATE attendance SET logout_time=NULL, last_relogin=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, employee_id, today)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "action": "relogin", "name": employee_name,
                        "status": "Re-Login", "time": current_time.strftime("%H:%M:%S")})


@attendance_bp.route("/api/employee/attendance", methods=["GET"])
@employee_api_required
def api_employee_attendance():
    from flask import g as _g
    emp_id = _g.api_emp_id
    try:
        year  = int(request.args.get("year",  datetime.date.today().year))
        month = int(request.args.get("month", datetime.date.today().month))
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid year/month"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type, worked_minutes
        FROM attendance
        WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s
        ORDER BY date DESC
    """, (emp_id, month, year))
    rows = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*), attendance_type FROM attendance
        WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s
        GROUP BY attendance_type
    """, (emp_id, month, year))
    type_counts = {r[1]: r[0] for r in cursor.fetchall()}
    cursor.close(); db.close()
    full = type_counts.get("Full Day", 0) + type_counts.get("Late - Full Day", 0)
    half = type_counts.get("Half Day", 0) + type_counts.get("Late - Half Day", 0)
    late = type_counts.get("Late - Full Day", 0) + type_counts.get("Late - Half Day", 0)
    return jsonify({
        "ok": True,
        "year": year, "month": month,
        "month_name": datetime.date(year, month, 1).strftime("%B %Y"),
        "summary": {"present": full + half, "full_days": full, "half_days": half, "late": late},
        "records": [
            {
                "date": str(r[0]),
                "login_time": _fmt_t(r[1]),
                "logout_time": _fmt_t(r[2]),
                "login_status": r[3],
                "logout_status": r[4],
                "attendance_type": r[5],
                "worked_minutes": r[6],
            }
            for r in rows
        ],
    })


@attendance_bp.route("/api/shifts", methods=["GET"])
@api_required
def api_shifts_get():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, name, start_time, half_time, end_time FROM shifts ORDER BY start_time")
    shifts = [
        {"id": r[0], "name": r[1],
         "start": _td_to_time(r[2]).strftime("%H:%M") if r[2] else "--",
         "half":  _td_to_time(r[3]).strftime("%H:%M") if r[3] else "--",
         "end":   _td_to_time(r[4]).strftime("%H:%M") if r[4] else "--"}
        for r in cursor.fetchall()
    ]
    cursor.execute(
        "SELECT e.employee_id, e.name, e.role, s.id, s.name "
        "FROM employees e LEFT JOIN shifts s ON e.shift_id = s.id ORDER BY e.name"
    )
    employees = [
        {"emp_id": r[0], "name": r[1], "role": r[2] or "",
         "shift_id": r[3], "shift_name": r[4] or "Default"}
        for r in cursor.fetchall()
    ]
    cursor.close(); db.close()
    return jsonify({"ok": True, "shifts": shifts, "employees": employees})


@attendance_bp.route("/api/shifts", methods=["POST"])
@api_required
def api_shifts_create():
    data  = request.get_json(silent=True) or {}
    name  = data.get("name", "").strip()
    start = data.get("start_time", "").strip()
    half  = data.get("half_time",  "").strip()
    end   = data.get("end_time",   "").strip()
    if not all([name, start, half, end]):
        return jsonify({"ok": False, "msg": "All fields required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute(
            "INSERT INTO shifts (name, start_time, half_time, end_time) VALUES (%s,%s,%s,%s) RETURNING id",
            (name, start, half, end)
        )
        sid = cursor.fetchone()[0]
        db.commit()
    except Exception:
        app_log.error("Failed to create shift", exc_info=True)
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Failed to create shift. Check for duplicate names."}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True, "id": sid})


@attendance_bp.route("/api/shifts/<int:sid>", methods=["DELETE"])
@api_required
def api_shifts_delete(sid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("DELETE FROM shifts WHERE id=%s", (sid,))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@attendance_bp.route("/api/shifts/assign", methods=["POST"])
@api_required
def api_shifts_assign():
    data     = request.get_json(silent=True) or {}
    emp_id   = data.get("emp_id", "").strip()
    shift_id = data.get("shift_id")
    if not emp_id:
        return jsonify({"ok": False, "msg": "emp_id required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE employees SET shift_id=%s WHERE employee_id=%s",
        (shift_id if shift_id else None, emp_id)
    )
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})

