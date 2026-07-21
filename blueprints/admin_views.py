"""Admin views blueprint — dashboard, settings, analytics, companies."""
import calendar
import csv
import datetime
import io
import json
import os
import psycopg2
import re
import secrets

from flask import (Blueprint, current_app, session, request, redirect,
                   render_template, flash, url_for, jsonify, send_file,
                   abort, Response)

from extensions import app_log, limiter
from database import get_db_connection
from utils.auth import (admin_required, employee_required, api_required,
                        check_password_hash, generate_password_hash, _hash_token)
from utils.helpers import (_audit, get_company_settings, get_auth_config,
                           encrypt_pii, decrypt_pii, _validate_image_file,
                           _safe_redirect, _safe_referrer_redirect, _db)
from utils.email_utils import get_email_config, send_email_smtp, send_email_async
from qr_generator import generate_qr
from utils.attendance_utils import _td_to_time
from utils.config import (SHIFT_START, SHIFT_HALF, SHIFT_END,
                          load_salary_rules, load_default_shift)

admin_views_bp = Blueprint("admin_views", __name__)

try:
    import face_recognition as face_recognition
    _face_recognition_available = True
except Exception:
    face_recognition = None
    _face_recognition_available = False

_VALID_CFS_COLS = frozenset({
    "face_auth_enabled", "geo_enabled", "geo_radius", "qr_enabled", "pin_enabled",
    "fingerprint_enabled", "biometric_enabled", "notify_leave", "notify_payslip",
    "notify_resignation", "notify_doc_expiry", "session_timeout",
    "late_deduction_pct", "half_day_deduction_pct", "grace_minutes",
    "shift_start", "shift_half", "shift_end", "holiday_pay", "leave_pay",
})

_TOGGLE_COLUMN_MAP = {
    "fingerprint": "fingerprint_enabled",
    "qr":          "qr_enabled",
    "face":        "face_enabled",
    "location":    "location_enabled",
    "password":    "employee_password_auth",
}
_TOGGLE_LABEL_MAP = {
    "fingerprint": "Fingerprint / Biometric",
    "qr":          "QR Code",
    "face":        "Face Recognition",
    "location":    "Location Verification",
    "password":    "Password Login",
}


def _read_global_features():
    """Read global company_settings feature flags as dict."""
    try:
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute("""
            SELECT face_auth_enabled, geo_enabled, COALESCE(geo_radius,300), qr_enabled,
                   pin_enabled, COALESCE(fingerprint_enabled,0), COALESCE(biometric_enabled,0),
                   COALESCE(notify_leave,1), COALESCE(notify_payslip,1),
                   COALESCE(notify_resignation,1), COALESCE(notify_doc_expiry,1),
                   COALESCE(session_timeout,30),
                   COALESCE(late_deduction_pct,10), COALESCE(half_day_deduction_pct,50),
                   COALESCE(grace_minutes,15), COALESCE(holiday_pay,'paid'),
                   COALESCE(leave_pay,'exclude'),
                   COALESCE(shift_start,'09:00:00'), COALESCE(shift_half,'13:00:00'),
                   COALESCE(shift_end,'18:00:00')
            FROM company_settings LIMIT 1
        """)
        r = cur.fetchone(); cur.close(); db.close()
        if r:
            return {
                "face_auth_enabled": bool(r[0]), "geo_enabled": bool(r[1]),
                "geo_radius": r[2], "qr_enabled": bool(r[3]), "pin_enabled": bool(r[4]),
                "fingerprint_enabled": bool(r[5]), "biometric_enabled": bool(r[6]),
                "notify_leave": bool(r[7]), "notify_payslip": bool(r[8]),
                "notify_resignation": bool(r[9]), "notify_doc_expiry": bool(r[10]),
                "session_timeout": r[11],
                "late_deduction_pct": float(r[12]), "half_day_deduction_pct": float(r[13]),
                "grace_minutes": int(r[14]), "holiday_pay": r[15], "leave_pay": r[16],
                "shift_start": r[17], "shift_half": r[18], "shift_end": r[19],
            }
    except Exception:
        pass
    return {
        "face_auth_enabled": True, "geo_enabled": False, "geo_radius": 300,
        "qr_enabled": True, "pin_enabled": True, "fingerprint_enabled": False,
        "biometric_enabled": False, "notify_leave": True, "notify_payslip": True,
        "notify_resignation": True, "notify_doc_expiry": True, "session_timeout": 30,
        "late_deduction_pct": 10.0, "half_day_deduction_pct": 50.0, "grace_minutes": 15,
        "holiday_pay": "paid", "leave_pay": "exclude",
        "shift_start": "09:00:00", "shift_half": "13:00:00", "shift_end": "18:00:00",
    }


def get_co_features(company_id=None):
    """Return feature settings for a company, falling back to global defaults."""
    if not company_id:
        return _read_global_features()
    try:
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute("""
            SELECT face_auth_enabled, geo_enabled, geo_radius, qr_enabled,
                   pin_enabled, fingerprint_enabled, biometric_enabled,
                   notify_leave, notify_payslip, notify_resignation, notify_doc_expiry,
                   session_timeout, late_deduction_pct, half_day_deduction_pct,
                   grace_minutes, holiday_pay, leave_pay, shift_start, shift_half, shift_end
            FROM company_feature_settings WHERE company_id=%s
        """, (company_id,))
        r = cur.fetchone(); cur.close(); db.close()
        if r:
            return {
                "face_auth_enabled": bool(r[0]), "geo_enabled": bool(r[1]),
                "geo_radius": r[2], "qr_enabled": bool(r[3]), "pin_enabled": bool(r[4]),
                "fingerprint_enabled": bool(r[5]), "biometric_enabled": bool(r[6]),
                "notify_leave": bool(r[7]), "notify_payslip": bool(r[8]),
                "notify_resignation": bool(r[9]), "notify_doc_expiry": bool(r[10]),
                "session_timeout": r[11],
                "late_deduction_pct": float(r[12]), "half_day_deduction_pct": float(r[13]),
                "grace_minutes": int(r[14]), "holiday_pay": r[15], "leave_pay": r[16],
                "shift_start": r[17], "shift_half": r[18], "shift_end": r[19],
            }
    except Exception:
        pass
    return _read_global_features()


def _upsert_co_feature(company_id, field, value):
    """Insert or update a single field in company_feature_settings."""
    if not company_id:
        return
    if field not in _VALID_CFS_COLS:
        app_log.error("_upsert_co_feature: rejected unknown column %s", field)
        return
    try:
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute(f"""
            INSERT INTO company_feature_settings (company_id, {field})
            VALUES (%s, %s)
            ON CONFLICT (company_id) DO UPDATE SET {field}=EXCLUDED.{field}
        """, (company_id, value))
        db.commit(); cur.close(); db.close()
    except Exception:
        pass


def _today_pending_counts(cursor):
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pl = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pr = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pt = cursor.fetchone()[0]
    return pl, pr, pt


def _enroll_fingerprint_from_form(emp_id, cursor, db):
    """Shared by admin_action()/add_employee_page(): read the WebAuthn
    attestation posted by the registration form (if any), verify and store
    it, flashing a warning on failure. No-op if the field is empty."""
    fp_attestation = request.form.get("fingerprint_attestation", "").strip()
    if not fp_attestation:
        return
    from app import _wa_verify_and_store_registration as _wa_reg
    _ok, _err = _wa_reg(
        emp_id, fp_attestation, session.get("wa_reg_challenge"), cursor, db
    )
    session.pop("wa_reg_challenge", None)
    session.pop("wa_reg_alg_ids", None)
    if not _ok:
        flash(f"⚠️ Fingerprint enrollment failed verification: {_err}", "error")


def assign_leave_balances_for_employee(cursor, employee_id, year=None):
    """Auto-assign leave balances for all active leave types for a new/existing employee."""
    if year is None:
        year = datetime.date.today().year
    cursor.execute("SELECT id, annual_quota FROM leave_types WHERE is_active=1")
    for lt_id, quota in cursor.fetchall():
        cursor.execute("""
            INSERT INTO leave_balances (employee_id, leave_type_id, year, total_days, used_days)
            VALUES (%s, %s, %s, %s, 0)
            ON CONFLICT (employee_id, leave_type_id, year) DO UPDATE SET
                total_days = CASE WHEN leave_balances.used_days = 0
                                  THEN EXCLUDED.total_days ELSE leave_balances.total_days END
        """, (employee_id, lt_id, year, quota))



@admin_views_bp.route("/csp-report", methods=["POST"])
def csp_report():
    """Receives Content-Security-Policy violation reports from browsers."""
    try:
        report = request.get_json(force=True, silent=True) or {}
        violation = report.get("csp-report", report)
        app_log.warning(
            "CSP violation",
            extra={
                "blocked_uri": violation.get("blocked-uri", ""),
                "violated_directive": violation.get("violated-directive", ""),
                "document_uri": violation.get("document-uri", ""),
                "source_file": violation.get("source-file", ""),
            },
        )
    except Exception:
        pass
    return "", 204


@admin_views_bp.route("/")
def home():
    return render_template("index.html", auth_cfg=get_auth_config())


@admin_views_bp.route("/admin")
@admin_required
def admin():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()
    active_cid = session.get("active_company_id")
    _co_filter = "AND e.company_id=%s" if active_cid else ""
    _co_sub    = "AND employee_id IN (SELECT employee_id FROM employees WHERE company_id=%s)" if active_cid else ""
    _co_args   = (active_cid,) if active_cid else ()

    if active_cid:
        cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id=%s", _co_args)
    else:
        cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND login_time IS NOT NULL {_co_sub}",
        (today,) + _co_args
    )
    present = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND status='Late Login' {_co_sub}",
        (today,) + _co_args
    )
    late = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT e.employee_id, e.name, a.login_time, a.logout_time, a.status, "
        f"       a.logout_status, a.attendance_type, e.role "
        f"FROM employees e "
        f"LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s "
        f"WHERE 1=1 {_co_filter} ORDER BY e.name",
        (today,) + _co_args
    )
    today_rows = cursor.fetchall()

    if active_cid:
        cursor.execute("SELECT employee_id, name FROM employees WHERE company_id=%s ORDER BY name", _co_args)
    else:
        cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
    all_employees = cursor.fetchall()

    cursor.execute(
        f"SELECT COUNT(*) FROM leave_requests WHERE status='Pending' {_co_sub}",
        _co_args
    )
    pending_leaves = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(*) FROM resignation_requests WHERE status='Pending' {_co_sub}",
        _co_args
    )
    pending_resignations = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress') {_co_sub}",
        _co_args
    )
    pending_tickets = cursor.fetchone()[0]

    try:
        cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE status='Pending'")
        pending_ot = cursor.fetchone()[0]
    except Exception:
        pending_ot = 0

    cursor.execute("SELECT id, name, COALESCE(code,'') FROM companies ORDER BY name")
    companies_list = cursor.fetchall()

    # Onboarding summary for dashboard widget
    try:
        cursor.execute("""
            SELECT
              SUM(CASE WHEN status != 'Completed' THEN 1 ELSE 0 END),
              SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END),
              SUM(CASE WHEN status != 'Completed' AND due_date < %s THEN 1 ELSE 0 END)
            FROM employee_onboarding
        """, (today,))
        _ob = cursor.fetchone()
        ob_active    = int(_ob[0] or 0)
        ob_completed = int(_ob[1] or 0)
        ob_overdue   = int(_ob[2] or 0)
        cursor.execute("""
            SELECT eo.id, e.name, ot.name, eo.due_date
            FROM employee_onboarding eo
            JOIN employees e ON eo.employee_id = e.employee_id
            JOIN onboarding_templates ot ON eo.template_id = ot.id
            WHERE eo.status != 'Completed' AND eo.due_date < %s
            ORDER BY eo.due_date LIMIT 5
        """, (today,))
        ob_overdue_list = cursor.fetchall()
    except Exception:
        ob_active = ob_completed = ob_overdue = 0
        ob_overdue_list = []

    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active FROM break_config ORDER BY break_time")
    break_rows = cursor.fetchall()
    breaks_display = []
    for b in break_rows:
        bt = b[2]
        if hasattr(bt, 'seconds'):
            h, m = divmod(bt.seconds // 60, 60)
        else:
            h, m = bt.hour, bt.minute
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        breaks_display.append({
            "id": b[0], "name": b[1],
            "time_str": "%02d:%02d %s" % (h12, m, ampm),
            "duration": b[3], "is_active": b[4]
        })

    cursor.close()
    db.close()

    return render_template("admin.html",
        total=total,
        present=present,
        absent=total - present,
        late=late,
        today=today.strftime("%d %b %Y"),
        active_nav="dashboard",
        today_rows=today_rows,
        all_employees=all_employees,
        shift_start=SHIFT_START.strftime("%I:%M %p"),
        shift_end=SHIFT_END.strftime("%I:%M %p"),
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_ot=pending_ot,
        pending_tickets=pending_tickets,
        now_month=today.month,
        now_year=today.year,
        breaks_display=breaks_display,
        companies_list=companies_list,
        ob_active=ob_active,
        ob_completed=ob_completed,
        ob_overdue=ob_overdue,
        ob_overdue_list=ob_overdue_list,
    )


@admin_views_bp.route("/api/dashboard_live")
@admin_required
def dashboard_live():
    def fmt(t):
        if t is None:
            return None
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M:%S")
        total = int(t.total_seconds())
        h, rem = divmod(total, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()
    active_cid = session.get("active_company_id")
    _co_filter = "AND e.company_id=%s" if active_cid else ""
    _co_sub    = "AND employee_id IN (SELECT employee_id FROM employees WHERE company_id=%s)" if active_cid else ""
    _co_args   = (active_cid,) if active_cid else ()

    if active_cid:
        cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id=%s", _co_args)
    else:
        cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND login_time IS NOT NULL {_co_sub}",
        (today,) + _co_args
    )
    present = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND status='Late Login' {_co_sub}",
        (today,) + _co_args
    )
    late = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT e.employee_id, e.name, a.login_time, a.logout_time, "
        f"       a.status, a.logout_status, a.attendance_type, e.role "
        f"FROM employees e "
        f"LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s "
        f"WHERE 1=1 {_co_filter} ORDER BY e.name",
        (today,) + _co_args
    )
    rows = []
    for emp_id, name, login_t, logout_t, status, logout_s, att_type, role in cursor.fetchall():
        rows.append({
            "emp_id":   emp_id,
            "name":     name,
            "role":     role or "",
            "login_t":  fmt(login_t),
            "logout_t": fmt(logout_t),
            "status":   status or "",
            "logout_s": logout_s or "",
            "att_type": att_type or "",
        })

    cursor.execute(f"SELECT COUNT(*) FROM leave_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_leaves = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM resignation_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_resignations = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress') {_co_sub}", _co_args)
    pending_tickets = cursor.fetchone()[0]

    cursor.close(); db.close()

    return jsonify({
        "total":   total,
        "present": present,
        "absent":  total - present,
        "late":    late,
        "rows":    rows,
        "pending_leaves":       pending_leaves,
        "pending_resignations": pending_resignations,
        "pending_tickets":      pending_tickets,
    })


@admin_views_bp.route("/today_present")
@admin_required
def today_present():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    active_cid = session.get("active_company_id")
    _co = "AND e.company_id=%s" if active_cid else ""
    _args = (today,) + ((active_cid,) if active_cid else ())
    cursor.execute(f"""
        SELECT e.employee_id, e.name, e.role, a.login_time, a.logout_time,
               a.status, a.logout_status, a.attendance_type
        FROM employees e
        JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.login_time IS NOT NULL {_co}
        ORDER BY a.login_time
    """, _args)
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="present", title="Present Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        active_nav="attendance",
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)


@admin_views_bp.route("/today_absent")
@admin_required
def today_absent():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    active_cid = session.get("active_company_id")
    _co = "AND e.company_id=%s" if active_cid else ""
    _args = (today,) + ((active_cid,) if active_cid else ())
    cursor.execute(f"""
        SELECT e.employee_id, e.name, e.role
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.employee_id IS NULL {_co}
        ORDER BY e.name
    """, _args)
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="absent", title="Absent Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        active_nav="attendance",
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)


@admin_views_bp.route("/today_late")
@admin_required
def today_late():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    active_cid = session.get("active_company_id")
    _co = "AND e.company_id=%s" if active_cid else ""
    _args = (today,) + ((active_cid,) if active_cid else ())
    cursor.execute(f"""
        SELECT e.employee_id, e.name, e.role, a.login_time, a.status
        FROM employees e
        JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.status IN ('Late Login', 'Half Day Login') {_co}
        ORDER BY a.login_time
    """, _args)
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="late", title="Late Logins Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        active_nav="attendance",
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)


@admin_views_bp.route("/admin_action", methods=["POST"])
@admin_required
def admin_action():
    action = request.form.get("action")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    if action == "register":
        try:
            name            = request.form["name"]
            emp_id          = request.form["emp_id"].strip()
            email           = request.form.get("email", "").strip() or None
            role            = request.form.get("role", "").strip() or None
            date_of_joining = request.form.get("date_of_joining", "").strip() or None
            work_mode       = request.form.get("work_mode", "office").strip() or "office"
            work_lat_raw    = request.form.get("work_lat", "").strip()
            work_lon_raw    = request.form.get("work_lon", "").strip()
            work_lat        = float(work_lat_raw) if work_lat_raw else None
            work_lon        = float(work_lon_raw) if work_lon_raw else None
            company_id_raw  = request.form.get("company_id", "").strip()
            company_id      = int(company_id_raw) if company_id_raw.isdigit() else None
            # Extended fields
            department      = request.form.get("department", "").strip() or None
            phone           = request.form.get("phone", "").strip() or None
            manager_id      = request.form.get("manager_id", "").strip() or None
            manager_name    = request.form.get("manager_name", "").strip() or None
            salary_per_day_raw = request.form.get("salary_per_day", "").strip()
            salary_per_day  = float(salary_per_day_raw) if salary_per_day_raw else None
            gender          = request.form.get("gender", "").strip() or None
            dob_raw         = request.form.get("dob", "").strip()
            dob             = dob_raw if dob_raw else None
            blood_group     = request.form.get("blood_group", "").strip() or None
            address         = request.form.get("address", "").strip() or None
            city            = request.form.get("city", "").strip() or None
            state           = request.form.get("state", "").strip() or None
            pincode         = request.form.get("pincode", "").strip() or None
            ec_name         = request.form.get("emergency_contact_name", "").strip() or None
            ec_phone        = request.form.get("emergency_contact_phone", "").strip() or None
            ec_relation     = request.form.get("emergency_contact_relation", "").strip() or None
            aadhar          = encrypt_pii(request.form.get("aadhar_number", "").strip() or None)
            pan             = encrypt_pii(request.form.get("pan_number", "").strip().upper() or None)
            bank_name       = request.form.get("bank_name", "").strip() or None
            bank_account    = encrypt_pii(request.form.get("bank_account", "").strip() or None)
            bank_ifsc       = encrypt_pii(request.form.get("bank_ifsc", "").strip().upper() or None)
            uan             = encrypt_pii(request.form.get("uan_number", "").strip() or None)
            file            = request.files["face"]
        except (KeyError, ValueError) as _e:
            cursor.close(); db.close()
            flash(f"Missing or invalid field in registration form: {_e}", "error")
            return redirect("/admin")
        # Auto-increment emp_id if it's already taken
        cursor.execute("SELECT 1 FROM employees WHERE employee_id = %s", (emp_id,))
        if cursor.fetchone():
            prefix = ''.join(c for c in emp_id if not c.isdigit())
            if prefix:
                cursor.execute(
                    "SELECT employee_id FROM employees WHERE employee_id LIKE %s",
                    (prefix + "%",)
                )
                max_seq = 0
                for (eid,) in cursor.fetchall():
                    sfx = eid[len(prefix):]
                    if sfx.isdigit():
                        max_seq = max(max_seq, int(sfx))
                emp_id = f"{prefix}{max_seq + 1:03d}"
        _img_ok, _img_err = _validate_image_file(file)
        if not _img_ok:
            flash(_img_err, "error")
            cursor.close(); db.close()
            return redirect("/admin")
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        file.save(filepath)

        # Validate that the uploaded photo contains a detectable face
        if _face_recognition_available:
            test_img = face_recognition.load_image_file(filepath)
            if not face_recognition.face_encodings(test_img):
                os.remove(filepath)
                flash("No face detected in the uploaded photo. Please upload a clear, well-lit front-facing photo.", "error")
                cursor.close()
                db.close()
                return redirect("/admin")

        qr_path    = generate_qr(emp_id)
        auto_pass  = secrets.token_urlsafe(8)   # e.g. "aB3xQ7mR"
        hashed_pwd = generate_password_hash(auto_pass)
        try:
            cursor.execute(
                "INSERT INTO employees (name, employee_id, email, role, face_image, qr_code, password, "
                "date_of_joining, work_mode, work_lat, work_lon, company_id, "
                "department, phone, manager_id, manager_name, "
                "gender, dob, blood_group, "
                "address, city, state, pincode, "
                "emergency_contact_name, emergency_contact_phone, emergency_contact_relation, "
                "aadhar_number, pan_number, bank_name, bank_account, bank_ifsc, uan_number, "
                "force_pin_change) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                "%s,%s,%s,%s,"
                "%s,%s,%s,"
                "%s,%s,%s,%s,"
                "%s,%s,%s,"
                "%s,%s,%s,%s,%s,%s,1)",
                (name, emp_id, email, role, filepath, qr_path, hashed_pwd,
                 date_of_joining, work_mode, work_lat, work_lon, company_id,
                 department, phone, manager_id, manager_name,
                 gender, dob, blood_group,
                 address, city, state, pincode,
                 ec_name, ec_phone, ec_relation,
                 aadhar, pan, bank_name, bank_account, bank_ifsc, uan)
            )
            db.commit()
            if salary_per_day is not None:
                cursor.execute(
                    "INSERT INTO salary_config (employee_id, salary_per_day) VALUES (%s,%s) "
                    "ON CONFLICT (employee_id) DO UPDATE SET salary_per_day=%s",
                    (emp_id, salary_per_day, salary_per_day)
                )
                db.commit()
            _enroll_fingerprint_from_form(emp_id, cursor, db)
            assign_leave_balances_for_employee(cursor, emp_id)
            db.commit()
            flash(f"✅ Employee '{name}' registered! ID: {emp_id} | Password: {auto_pass}", "success")
            # Send welcome email with credentials
            if not email:
                flash("⚠️ No email address provided — credentials email not sent. Share them manually.", "error")
            else:
                _ecfg = get_email_config()
                if not _ecfg:
                    flash("⚠️ SMTP not configured — credentials email not sent. Go to Email Settings to set it up.", "error")
                else:
                    _welcome_html = f"""
<div style="font-family:'Segoe UI',sans-serif;max-width:520px;margin:0 auto;background:#f8fafc;padding:32px 24px;border-radius:16px;">
  <div style="background:linear-gradient(135deg,#1e3a8a,#2563eb);border-radius:12px;padding:28px 24px;text-align:center;margin-bottom:24px;">
    <div style="font-size:36px;margin-bottom:8px;">👋</div>
    <h1 style="color:#fff;font-size:22px;margin:0;">Welcome to the Team!</h1>
    <p style="color:rgba(255,255,255,0.8);font-size:14px;margin:6px 0 0;">Your employee account has been created</p>
  </div>
  <p style="color:#1e293b;font-size:15px;margin-bottom:20px;">Hi <strong>{name}</strong>, here are your login credentials for the Attendance Portal:</p>
  <div style="background:#fff;border:1px solid #dbeafe;border-radius:12px;padding:20px 24px;margin-bottom:20px;">
    <table style="width:100%;font-size:14px;border-collapse:collapse;">
      <tr>
        <td style="color:#64748b;padding:8px 0;border-bottom:1px solid #f1f5f9;font-weight:600;width:40%;">Employee ID</td>
        <td style="color:#1e293b;padding:8px 0;border-bottom:1px solid #f1f5f9;font-weight:700;">{emp_id}</td>
      </tr>
      <tr>
        <td style="color:#64748b;padding:8px 0;font-weight:600;">Password</td>
        <td style="color:#1e293b;padding:8px 0;font-weight:700;font-family:monospace;font-size:15px;">{auto_pass}</td>
      </tr>
    </table>
  </div>
  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-size:13px;color:#92400e;margin-bottom:20px;">
    🔒 Please change your password after your first login for security.
  </div>
  <p style="color:#64748b;font-size:12px;text-align:center;margin:0;">This is an automated message — please do not reply.</p>
</div>"""
                    try:
                        send_email_smtp(email, f"Welcome {name} — Your Login Credentials", _welcome_html, _ecfg)
                        flash(f"📧 Credentials email sent to {email}", "success")
                    except Exception as _mail_err:
                        flash(f"⚠️ Email delivery failed: {_mail_err}. Share credentials manually.", "error")
        except psycopg2.IntegrityError:
            db.rollback()
            os.remove(filepath)
            flash(f"Employee ID '{emp_id}' already exists. Please use a different ID.", "error")
            cursor.close()
            db.close()
            return redirect("/admin")

    elif action == "update_face":
        emp_id   = request.form["emp_id"]
        file     = request.files["face"]
        cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
        row = cursor.fetchone()
        if not row:
            flash(f"Employee ID '{emp_id}' not found.", "error")
            cursor.close()
            db.close()
            return redirect("/admin")
        name = row[0]
        _img_ok, _img_err = _validate_image_file(file)
        if not _img_ok:
            flash(_img_err, "error")
            cursor.close(); db.close()
            return redirect("/admin")
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        file.save(filepath)
        if _face_recognition_available:
            test_img = face_recognition.load_image_file(filepath)
            if not face_recognition.face_encodings(test_img):
                os.remove(filepath)
                flash("No face detected in the uploaded photo. Please upload a clear, well-lit front-facing photo.", "error")
                cursor.close()
                db.close()
                return redirect("/admin")
        cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (filepath, emp_id))
        db.commit()
        flash(f"Face photo updated successfully for '{name}' (ID: {emp_id}).", "success")

    elif action == "reset_password":
        emp_id = request.form.get("emp_id", "").strip()
        cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
        row = cursor.fetchone()
        if not row:
            flash(f"Employee ID '{emp_id}' not found.", "error")
        else:
            cursor.execute(
                "UPDATE employees SET password=%s WHERE employee_id=%s",
                (generate_password_hash(emp_id), emp_id)
            )
            db.commit()
            flash(f"Password reset for '{row[0]}' ({emp_id}). They can now login using their Employee ID as the password.", "success")

    elif action == "holiday":
        cursor.execute(
            "INSERT INTO holidays (date, name) VALUES (%s,%s)",
            (request.form["date"], request.form["holiday_name"])
        )
        db.commit()

    elif action == "salary":
        emp_id = request.form["emp_id"]
        salary = request.form["salary"]
        cursor.execute("SELECT 1 FROM salary_config WHERE employee_id=%s", (emp_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE salary_config SET salary_per_day=%s WHERE employee_id=%s",
                (salary, emp_id)
            )
        else:
            cursor.execute(
                "INSERT INTO salary_config (employee_id, salary_per_day) VALUES (%s,%s)",
                (emp_id, salary)
            )
        db.commit()

    cursor.close()
    db.close()
    return redirect("/admin")


@admin_views_bp.route("/settings")
@admin_required
def settings_page():
    tab    = request.args.get("tab", "company")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Email config
    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email FROM email_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    email_config = {"host": row[0], "port": row[1], "user": row[2], "password": "••••••••" if row[3] else "", "from_name": row[4], "from_email": row[5] or row[2]} if row else None

    # Shifts (with company)
    cursor.execute("""
        SELECT s.id, s.name, s.start_time, s.half_time, s.end_time,
               COALESCE(s.company_id, 0), COALESCE(c.name, '')
        FROM shifts s
        LEFT JOIN companies c ON c.id = s.company_id
        ORDER BY c.name, s.start_time
    """)
    shift_rows = []
    for sid, sname, st, ht, et, scid, scname in cursor.fetchall():
        shift_rows.append({
            "id": sid, "name": sname,
            "start": _td_to_time(st).strftime("%H:%M") if st else "--",
            "half":  _td_to_time(ht).strftime("%H:%M") if ht else "--",
            "end":   _td_to_time(et).strftime("%H:%M") if et else "--",
            "company_id": scid, "company_name": scname,
        })
    cursor.execute("SELECT e.employee_id, e.name, e.role, s.name FROM employees e LEFT JOIN shifts s ON e.shift_id = s.id ORDER BY e.name")
    emp_list = [{"emp_id": r[0], "name": r[1], "role": r[2] or "", "shift": r[3] or "Default"} for r in cursor.fetchall()]

    # Company-specific shifts (company_id IS NOT NULL)
    cursor.execute("SELECT id, name, start_time, half_time, end_time, company_id FROM shifts WHERE company_id IS NOT NULL ORDER BY company_id, start_time")
    _co_shifts_raw = cursor.fetchall()
    company_shifts = {}
    for _csid, _csname, _csstart, _cshalf, _csend, _cscid in _co_shifts_raw:
        def _tdfmt(v):
            if v is None: return "--"
            if isinstance(v, datetime.timedelta):
                _s = int(v.total_seconds()); return "%02d:%02d" % (_s // 3600, (_s % 3600) // 60)
            if isinstance(v, datetime.time): return v.strftime("%H:%M")
            return str(v)[:5]
        company_shifts.setdefault(_cscid, []).append((_csid, _csname, _tdfmt(_csstart), _tdfmt(_cshalf), _tdfmt(_csend)))

    # Company-specific breaks (company_id IS NOT NULL), nested per shift
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active, company_id, COALESCE(shift_id,0) FROM break_config WHERE company_id IS NOT NULL ORDER BY company_id, shift_id, break_time")
    _co_breaks_raw = cursor.fetchall()
    company_breaks = {}
    for _cbid, _cbname, _cbt, _cbdur, _cbactive, _cbcid, _cbsid in _co_breaks_raw:
        if _cbt is None: _cbt_str = "--"
        elif isinstance(_cbt, datetime.timedelta):
            _s = int(_cbt.total_seconds()); _cbt_str = "%02d:%02d" % (_s // 3600, (_s % 3600) // 60)
        elif isinstance(_cbt, datetime.time): _cbt_str = _cbt.strftime("%H:%M")
        else: _cbt_str = str(_cbt)[:5]
        company_breaks.setdefault(_cbcid, {}).setdefault(_cbsid, []).append((_cbid, _cbname, _cbt_str, _cbdur, _cbactive))

    # Breaks (with shift_id) — pre-format break_time as HH:MM
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active, COALESCE(shift_id,0) FROM break_config WHERE company_id IS NULL ORDER BY shift_id, break_time")
    breaks = []
    for _bid, _bname, _bt, _bdur, _bactive, _bshift in cursor.fetchall():
        if _bt is None:
            _bt_str = "--"
        elif isinstance(_bt, datetime.timedelta):
            _s = int(_bt.total_seconds()); _bt_str = "%02d:%02d" % (_s // 3600, (_s % 3600) // 60)
        elif isinstance(_bt, datetime.time):
            _bt_str = _bt.strftime("%H:%M")
        else:
            _bt_str = str(_bt)[:5]
        breaks.append((_bid, _bname, _bt_str, _bdur, _bactive, _bshift))

    # Salary
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0), e.role, s.last_revised,
               COALESCE(e.phone,''), COALESCE(e.email,'')
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    salaries = cursor.fetchall()

    # Announcements (admin sees all; include visibility and target employee name)
    cursor.execute("""
        SELECT a.id, a.title, a.content, a.priority, a.created_at,
               COALESCE(a.visibility,'public'), COALESCE(a.target_employee_id,''), COALESCE(e.name,'')
        FROM announcements a
        LEFT JOIN employees e ON e.employee_id = a.target_employee_id
        ORDER BY a.created_at DESC
    """)
    ann_list = cursor.fetchall()
    pub_anns  = [r for r in ann_list if r[5] == 'public']
    priv_anns = [r for r in ann_list if r[5] == 'private']

    # Employee list for private announcement targeting
    cursor.execute("SELECT employee_id, name FROM employees WHERE is_active=1 ORDER BY name")
    ann_emp_list = cursor.fetchall()

    # Pending counts
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    pending_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(company_code,''), COALESCE(default_onboarding_template_id,0) FROM company_settings LIMIT 1")
    _cr = cursor.fetchone()
    company_code = _cr[0] if _cr else ""
    default_onboarding_tpl = int(_cr[1]) if _cr and _cr[1] else 0

    # Company stats
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM employees e
        WHERE NOT EXISTS (
            SELECT 1 FROM resignation_requests r
            WHERE r.employee_id = e.employee_id AND r.status = 'Approved'
        )
    """)
    active_employees = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT department) FROM employees WHERE department IS NOT NULL AND department != ''")
    total_departments = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM shifts")
    total_shifts = cursor.fetchone()[0]
    cursor.execute("SELECT id, name FROM onboarding_templates WHERE is_active=1 ORDER BY name")
    onboarding_templates = cursor.fetchall()

    cursor.execute("""
        SELECT c.id, c.name, COALESCE(c.code,''), c.created_at,
               COUNT(e.id) AS emp_count,
               COALESCE(c.working_days,'Mon,Tue,Wed,Thu,Fri'),
               CASE WHEN c.pin IS NOT NULL AND c.pin != '' THEN 1 ELSE 0 END AS has_pin
        FROM companies c
        LEFT JOIN employees e ON e.company_id = c.id
        GROUP BY c.id, c.name, c.code, c.created_at, c.working_days, c.pin
        ORDER BY c.name
    """)
    companies = cursor.fetchall()

    # Feature flags — per-company when active, global otherwise
    _active_cid_settings = session.get("active_company_id")
    fr = get_co_features(_active_cid_settings)
    cursor.execute("SELECT COALESCE(working_days,'Mon,Tue,Wed,Thu,Fri'), COALESCE(company_name,''), COALESCE(timezone,'Asia/Kolkata') FROM company_settings LIMIT 1")
    _gset = cursor.fetchone()
    features = {
        "face_auth":    fr["face_auth_enabled"],
        "geo":          fr["geo_enabled"],
        "geo_radius":   fr["geo_radius"],
        "qr":           fr["qr_enabled"],
        "pin":          fr["pin_enabled"],
        "fingerprint":  fr["fingerprint_enabled"],
        "biometric":    fr["biometric_enabled"],
        "notify_leave": fr["notify_leave"],
        "notify_payslip": fr["notify_payslip"],
        "notify_resignation": fr["notify_resignation"],
        "notify_doc_expiry":  fr["notify_doc_expiry"],
        "session_timeout": fr["session_timeout"],
        "working_days": (_gset[0] if _gset else "Mon,Tue,Wed,Thu,Fri").split(","),
        "company_name": _gset[1] if _gset else "",
        "timezone":     _gset[2] if _gset else "Asia/Kolkata",
        # salary rules from company features
        "late_deduction_pct": fr["late_deduction_pct"],
        "half_day_deduction_pct": fr["half_day_deduction_pct"],
        "grace_minutes": fr["grace_minutes"],
        "holiday_pay": fr["holiday_pay"],
        "leave_pay": fr["leave_pay"],
        "shift_start": fr["shift_start"],
        "shift_half": fr["shift_half"],
        "shift_end": fr["shift_end"],
    }

    # Resolve salary/shift display values: company-specific overrides global
    def _td_str(v):
        if v is None: return None
        if isinstance(v, str): return v[:5]
        if isinstance(v, datetime.timedelta):
            t = int(v.total_seconds()); return "%02d:%02d" % (t//3600, (t%3600)//60)
        if isinstance(v, datetime.time): return v.strftime("%H:%M")
        return str(v)[:5]

    _co_shift_start = _td_str(fr.get("shift_start")) or SHIFT_START.strftime("%H:%M")
    _co_shift_half  = _td_str(fr.get("shift_half"))  or SHIFT_HALF.strftime("%H:%M")
    _co_shift_end   = _td_str(fr.get("shift_end"))   or SHIFT_END.strftime("%H:%M")

    cursor.close(); db.close()
    return render_template("settings.html",
        tab=tab,
        email_config=email_config,
        company_code=company_code,
        total_employees=total_employees,
        active_employees=active_employees,
        total_departments=total_departments,
        total_shifts=total_shifts,
        companies=companies,
        company_shifts=company_shifts,
        company_breaks=company_breaks,
        shifts=shift_rows,
        emp_list=emp_list,
        breaks=breaks,
        salaries=salaries,
        ann_list=ann_list,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        saved=request.args.get("saved") == "1",
        active_nav="settings",
        default_start=_co_shift_start,
        default_half=_co_shift_half,
        default_end=_co_shift_end,
        now_month=datetime.date.today().month,
        now_year=datetime.date.today().year,
        default_onboarding_tpl=default_onboarding_tpl,
        onboarding_templates=onboarding_templates,
        late_deduction_pct=round(fr["late_deduction_pct"], 1),
        half_day_deduction_pct=round(fr["half_day_deduction_pct"], 1),
        grace_minutes=fr["grace_minutes"],
        holiday_pay=fr["holiday_pay"],
        leave_pay=fr["leave_pay"],
        auth_config={
            "face_enabled":            fr["face_auth_enabled"],
            "qr_enabled":              fr["qr_enabled"],
            "fingerprint_enabled":     fr["fingerprint_enabled"],
            "location_enabled":        fr["geo_enabled"],
            "employee_password_auth":  True,
        },
        features=features,
    )


@admin_views_bp.route("/save_default_onboarding_template", methods=["POST"])
@admin_required
def save_default_onboarding_template():
    tpl_id = request.form.get("default_onboarding_template_id") or None
    if tpl_id == "0" or tpl_id == "":
        tpl_id = None
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE company_settings SET default_onboarding_template_id=%s", (tpl_id,))
    db.commit(); cursor.close(); db.close()
    flash("Default onboarding template saved.", "success")
    return redirect("/onboarding?tab=templates")


@admin_views_bp.route("/toggle_auth_method", methods=["POST"])
@admin_required
def toggle_auth_method():
    method  = request.form.get("method", "")
    enabled = request.form.get("enabled", "0") == "1"
    if method not in _TOGGLE_COLUMN_MAP:
        flash("Invalid authentication method.", "danger")
        return redirect("/settings?tab=attendance")
    column = _TOGGLE_COLUMN_MAP[method]
    label  = _TOGGLE_LABEL_MAP[method]
    active_cid = session.get("active_company_id")
    # Map old column names to company_feature_settings column names
    _cfs_map = {"face_enabled": "face_auth_enabled", "location_enabled": "geo_enabled",
                "employee_password_auth": None}  # password auth stays global
    cfs_col = _cfs_map.get(column, column)
    if active_cid and cfs_col:
        _upsert_co_feature(active_cid, cfs_col, 1 if enabled else 0)
    else:
        _VALID_CS_TOGGLE = frozenset(_TOGGLE_COLUMN_MAP.values())
        if column not in _VALID_CS_TOGGLE:
            flash("Invalid setting.", "danger")
            return redirect("/settings?tab=attendance")
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(f"UPDATE company_settings SET {column}=%s", (1 if enabled else 0,))
        db.commit(); cursor.close(); db.close()
    state = "enabled" if enabled else "disabled"
    flash(f"{label} {state}.", "success")
    return redirect("/settings?tab=attendance")


@admin_views_bp.route("/toggle_fingerprint", methods=["POST"])
@admin_required
def toggle_fingerprint():
    enabled = request.form.get("enabled", "0") == "1"
    active_cid = session.get("active_company_id")
    if active_cid:
        _upsert_co_feature(active_cid, "fingerprint_enabled", 1 if enabled else 0)
    else:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE company_settings SET fingerprint_enabled=%s", (1 if enabled else 0,))
        db.commit(); cursor.close(); db.close()
    state = "enabled" if enabled else "disabled"
    flash(f"Fingerprint authentication {state}.", "success")
    return redirect("/settings?tab=attendance")


@admin_views_bp.route("/save_company_code", methods=["POST"])
@admin_required
def save_company_code():
    code = request.form.get("company_code", "").strip().upper()[:10]
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE company_settings SET company_code=%s", (code,))
    db.commit(); cursor.close(); db.close()
    flash(f"Company code set to '{code}'.", "success")
    return redirect("/settings?tab=company")


@admin_views_bp.route("/save_company_info", methods=["POST"])
@admin_required
def save_company_info():
    import pytz as _pytz
    _VALID_DAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
    name     = request.form.get("company_name", "").strip()[:200]
    code     = request.form.get("company_code", "").strip().upper()[:10]
    timezone = request.form.get("timezone", "Asia/Kolkata").strip()
    w_days_raw = request.form.getlist("working_days")
    # Validate timezone against pytz database
    if timezone not in _pytz.all_timezones_set:
        flash("Invalid timezone selected.", "danger")
        return redirect("/settings?tab=company")
    # Validate day names
    w_days_set = set(w_days_raw)
    if w_days_set and not w_days_set.issubset(_VALID_DAYS):
        flash("Invalid working days selected.", "danger")
        return redirect("/settings?tab=company")
    w_days = ",".join(d for d in w_days_raw if d in _VALID_DAYS)
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE company_settings SET company_name=%s, company_code=%s, timezone=%s, working_days=%s",
        (name, code, timezone, w_days or "Mon,Tue,Wed,Thu,Fri")
    )
    db.commit(); cursor.close(); db.close()
    flash("Company info saved.", "success")
    return redirect("/settings?tab=company")


@admin_views_bp.route("/toggle_feature", methods=["POST"])
@admin_required
def toggle_feature():
    from flask import jsonify
    allowed = {
        "face_auth_enabled","geo_enabled","qr_enabled","pin_enabled",
        "fingerprint_enabled","biometric_enabled",
        "notify_leave","notify_payslip","notify_resignation","notify_doc_expiry",
    }
    data    = request.get_json(force=True) or {}
    feature = data.get("feature", "")
    value   = 1 if data.get("value") else 0
    if feature not in allowed:
        return jsonify({"ok": False, "error": "unknown feature"}), 400
    active_cid = session.get("active_company_id")
    # Explicit allowlist maps feature name → exact DB column (no dynamic interpolation)
    _CS_COL_MAP = {
        "face_auth_enabled":  "face_auth_enabled",
        "geo_enabled":        "geo_enabled",
        "qr_enabled":         "qr_enabled",
        "pin_enabled":        "pin_enabled",
        "fingerprint_enabled":"fingerprint_enabled",
        "biometric_enabled":  "biometric_enabled",
        "notify_leave":       "notify_leave",
        "notify_payslip":     "notify_payslip",
        "notify_resignation": "notify_resignation",
        "notify_doc_expiry":  "notify_doc_expiry",
    }
    cs_col = _CS_COL_MAP.get(feature)
    if not cs_col:
        return jsonify({"ok": False, "error": "unknown feature"}), 400
    if active_cid:
        _upsert_co_feature(active_cid, cs_col, value)
    else:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(f"UPDATE company_settings SET {cs_col}=%s", (value,))
        db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True})


@admin_views_bp.route("/save_geo_radius", methods=["POST"])
@admin_required
def save_geo_radius():
    try:
        radius = int(request.form.get("geo_radius", 100))
        if not (50 <= radius <= 5000):
            raise ValueError
    except (ValueError, TypeError):
        flash("Geo radius must be between 50 and 5000 metres.", "danger")
        return redirect("/settings?tab=attendance")
    active_cid = session.get("active_company_id")
    if active_cid:
        _upsert_co_feature(active_cid, "geo_radius", radius)
    else:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE company_settings SET geo_radius=%s", (radius,))
        db.commit(); cursor.close(); db.close()
    flash("Attendance settings saved.", "success")
    return redirect("/settings?tab=attendance")


@admin_views_bp.route("/save_security_settings", methods=["POST"])
@admin_required
def save_security_settings():
    try:
        timeout = int(request.form.get("session_timeout", 30))
        if not (5 <= timeout <= 1440):
            raise ValueError
    except (ValueError, TypeError):
        flash("Session timeout must be between 5 and 1440 minutes.", "danger")
        return redirect("/settings?tab=security")
    active_cid = session.get("active_company_id")
    if active_cid:
        _upsert_co_feature(active_cid, "session_timeout", timeout)
    else:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE company_settings SET session_timeout=%s", (timeout,))
        db.commit(); cursor.close(); db.close()
    flash("Security settings saved.", "success")
    return redirect("/settings?tab=security")


@admin_views_bp.route("/switch_company", methods=["POST"])
@admin_required
def switch_company():
    cid  = request.form.get("company_id", "").strip()
    pin  = request.form.get("pin", "").strip()
    dest = _safe_redirect(request.form.get("next", ""), "/admin")
    if not cid:
        session.pop("active_company_id", None)
        flash("Switched to: All Companies", "success")
        return redirect(dest)
    try:
        cid = int(cid)
    except ValueError:
        return redirect(dest)
    db = get_db_connection(); cur = db.cursor(buffered=True)
    cur.execute("SELECT name, COALESCE(pin,'') FROM companies WHERE id=%s", (cid,))
    row = cur.fetchone()
    cur.close(); db.close()
    if not row:
        flash("Company not found.", "error")
        return redirect(dest)
    cname, stored_pin = row
    if stored_pin and not secrets.compare_digest(stored_pin, pin):
        flash(f"Incorrect PIN for {cname}.", "error")
        return redirect(dest + ("&" if "?" in dest else "?") + "pin_error=1&pin_cid=" + str(cid))
    session["active_company_id"] = cid
    flash(f"Switched to: {cname}", "success")
    return redirect(dest)


@admin_views_bp.route("/clear_company", methods=["POST"])
@admin_required
def clear_company():
    session.pop("active_company_id", None)
    flash("Viewing all companies.", "success")
    return redirect(_safe_redirect(request.form.get("next", ""), "/admin"))


@admin_views_bp.route("/set_company_pin", methods=["POST"])
@admin_required
def set_company_pin():
    cid = request.form.get("company_id", "").strip()
    pin = request.form.get("pin", "").strip()
    if not cid:
        flash("Invalid request.", "error")
        return redirect("/settings?tab=company")
    db = get_db_connection(); cur = db.cursor(buffered=True)
    cur.execute("UPDATE companies SET pin=%s WHERE id=%s", (pin or None, int(cid)))
    db.commit(); cur.close(); db.close()
    flash("PIN " + ("set." if pin else "removed."), "success")
    return redirect("/settings?tab=company")


@admin_views_bp.route("/companies")
@admin_required
def view_companies():
    return redirect("/settings?tab=company")


@admin_views_bp.route("/companies/add", methods=["POST"])
@admin_required
def add_company():
    name        = request.form.get("name", "").strip()
    code        = request.form.get("code", "").strip().upper()[:20] or None
    redirect_to = request.form.get("redirect_to", "companies")
    dest        = "/settings?tab=company" if redirect_to == "settings" else "/companies"
    if not name:
        flash("Company name is required.", "error")
        return redirect(dest)
    w_days = ",".join(request.form.getlist("working_days")) or "Mon,Tue,Wed,Thu,Fri"
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("INSERT INTO companies (name, code, working_days) VALUES (%s, %s, %s) RETURNING id", (name, code, w_days))
    new_cid = cursor.fetchone()[0]
    db.commit()

    shift_names  = request.form.getlist("shift_name[]")
    shift_starts = request.form.getlist("shift_start[]")
    shift_halfs  = request.form.getlist("shift_half[]")
    shift_ends   = request.form.getlist("shift_end[]")
    for sname, sstart, shalf, send in zip(shift_names, shift_starts, shift_halfs, shift_ends):
        sname = sname.strip(); sstart = sstart.strip(); shalf = shalf.strip(); send = send.strip()
        if sname and sstart and shalf and send:
            cursor.execute(
                "INSERT INTO shifts (name, start_time, half_time, end_time, company_id) VALUES (%s,%s,%s,%s,%s)",
                (sname,
                 sstart + ":00" if len(sstart) == 5 else sstart,
                 shalf  + ":00" if len(shalf)  == 5 else shalf,
                 send   + ":00" if len(send)   == 5 else send,
                 new_cid)
            )
    db.commit()

    break_names = request.form.getlist("break_name[]")
    break_times = request.form.getlist("break_time[]")
    break_durs  = request.form.getlist("break_duration[]")
    for bname, btime, bdur in zip(break_names, break_times, break_durs):
        bname = bname.strip(); btime = btime.strip(); bdur = bdur.strip()
        if bname and btime and bdur.isdigit():
            cursor.execute(
                "INSERT INTO break_config (break_name, break_time, duration_minutes, company_id) VALUES (%s,%s,%s,%s)",
                (bname, btime + ":00" if len(btime) == 5 else btime, int(bdur), new_cid)
            )
    db.commit()
    cursor.close(); db.close()
    flash(f"Company '{name}' added.", "success")
    return redirect(dest)


@admin_views_bp.route("/companies/<int:cid>/edit", methods=["POST"])
@admin_required
def edit_company(cid):
    name        = request.form.get("name", "").strip()
    new_code    = (request.form.get("code", "").strip().upper()[:20]) or None
    redirect_to = request.form.get("redirect_to", "companies")
    dest        = "/settings?tab=company" if redirect_to == "settings" else "/companies"

    if not name:
        flash("Company name is required.", "error")
        return redirect(dest)

    db = get_db_connection(); cursor = db.cursor(buffered=True)

    w_days = ",".join(request.form.getlist("working_days")) or "Mon,Tue,Wed,Thu,Fri"

    cursor.execute("SELECT COALESCE(code,'') FROM companies WHERE id=%s", (cid,))
    row      = cursor.fetchone()
    old_code = (row[0] or "").strip().upper() if row else ""

    cursor.execute("UPDATE companies SET name=%s, code=%s, working_days=%s WHERE id=%s", (name, new_code, w_days, cid))
    db.commit()

    renamed_count = 0
    if old_code and new_code and old_code != new_code:
        cursor.execute(
            "SELECT employee_id FROM employees WHERE company_id=%s AND employee_id LIKE %s",
            (cid, old_code + "%")
        )
        to_rename = [
            (r[0], new_code + r[0][len(old_code):])
            for r in cursor.fetchall() if r[0].startswith(old_code)
        ]

        related_tables = [
            "attendance", "salary_config", "leave_requests", "notifications",
            "resignation_requests", "tickets", "employee_incentives",
            "employee_experience", "employee_education", "leave_balances",
            "employee_documents", "performance_reviews", "overtime_records",
            "regularization_requests", "compoff_balance", "employee_onboarding",
        ]

        for old_eid, new_eid in to_rename:
            for tbl in related_tables:
                try:
                    cursor.execute(
                        f"UPDATE {tbl} SET employee_id=%s WHERE employee_id=%s",
                        (new_eid, old_eid)
                    )
                except Exception:
                    pass

            old_img = os.path.join(current_app.config["UPLOAD_FOLDER"], old_eid + ".jpg")
            new_img = os.path.join(current_app.config["UPLOAD_FOLDER"], new_eid + ".jpg")
            old_qr  = os.path.join("static", "qrcodes", old_eid + ".png")
            new_qr  = os.path.join("static", "qrcodes", new_eid + ".png")

            cursor.execute(
                "UPDATE employees SET employee_id=%s, face_image=%s, qr_code=%s "
                "WHERE employee_id=%s AND company_id=%s",
                (new_eid, new_img, new_qr, old_eid, cid)
            )

            if os.path.exists(old_img):
                try: os.rename(old_img, new_img)
                except Exception: pass
            if os.path.exists(old_qr):
                try: os.rename(old_qr, new_qr)
                except Exception: pass

            renamed_count += 1

        db.commit()
        flash(
            f"Company updated. {renamed_count} employee ID(s) renamed: "
            f"{old_code}xxx → {new_code}xxx.",
            "success"
        )
    else:
        flash("Company updated.", "success")

    cursor.close(); db.close()
    return redirect(dest)


@admin_views_bp.route("/companies/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_company(cid):
    redirect_to = request.form.get("redirect_to", "companies")
    dest        = "/settings?tab=company" if redirect_to == "settings" else "/companies"
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id=%s", (cid,))
    count = cursor.fetchone()[0]
    if count > 0:
        cursor.close(); db.close()
        flash(f"Cannot delete: {count} employee(s) are assigned to this company.", "error")
        return redirect(dest)
    cursor.execute("DELETE FROM companies WHERE id=%s", (cid,))
    db.commit(); cursor.close(); db.close()
    flash("Company deleted.", "success")
    return redirect(dest)


@admin_views_bp.route("/announcements", methods=["GET", "POST"])
@admin_required
def announcements_admin():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            visibility = request.form.get("visibility", "public")
            target_emp = request.form.get("target_employee_id", "").strip() or None
            if visibility == "private" and not target_emp:
                flash("Please select an employee for a private announcement.", "error")
                cursor.close(); db.close()
                return redirect("/performance?tab=announcements")
            if visibility == "public":
                target_emp = None
            cursor.execute(
                "INSERT INTO announcements (title, content, priority, visibility, target_employee_id) VALUES (%s,%s,%s,%s,%s)",
                (request.form["title"], request.form["content"], request.form.get("priority","Normal"), visibility, target_emp)
            )
            db.commit()
            flash("Announcement posted.", "success")
        elif action == "delete":
            cursor.execute("DELETE FROM announcements WHERE id=%s", (request.form["ann_id"],))
            db.commit()
            flash("Announcement deleted.", "success")
        cursor.close(); db.close()
        return redirect("/performance?tab=announcements")
    cursor.close(); db.close()
    return redirect("/performance?tab=announcements")


@admin_views_bp.route("/api/breaks")
@limiter.limit("30 per minute")
def api_breaks():
    if not (session.get("admin_logged_in") or session.get("employee_id")):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, break_name, break_time, duration_minutes FROM break_config WHERE is_active=1 ORDER BY break_time")
    rows = cursor.fetchall()
    cursor.close(); db.close()
    result = []
    for row in rows:
        bt = row[2]
        if hasattr(bt, 'seconds'):
            total = bt.seconds
            h, m = divmod(total // 60, 60)
        else:
            h, m = bt.hour, bt.minute
        result.append({"id": row[0], "name": row[1],
                        "hour": h, "minute": m,
                        "duration": row[3]})
    return jsonify(result)


@admin_views_bp.route("/break_config")
@admin_required
def view_break_config():
    return redirect("/settings?tab=shifts")


@admin_views_bp.route("/add_break", methods=["POST"])
@admin_required
def add_break():
    name     = request.form.get("break_name", "").strip()
    btime    = request.form.get("break_time", "")
    duration = int(request.form.get("duration_minutes", 10) or 10)
    dest     = _safe_redirect(request.form.get("redirect", ""), _safe_referrer_redirect(request.referrer or "", "/employees?tab=schedule"))
    cid_raw  = request.form.get("company_id", "").strip()
    company_id = int(cid_raw) if cid_raw.isdigit() else None
    sid_raw  = request.form.get("shift_id", "").strip()
    shift_id = int(sid_raw) if sid_raw.isdigit() else None
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if company_id:
        cursor.execute(
            "INSERT INTO break_config (break_name, break_time, duration_minutes, company_id, shift_id) VALUES (%s,%s,%s,%s,%s)",
            (name, btime, duration, company_id, shift_id)
        )
    else:
        cursor.execute("INSERT INTO break_config (break_name, break_time, duration_minutes, shift_id) VALUES (%s,%s,%s,%s)",
                       (name, btime, duration, shift_id))
    db.commit(); cursor.close(); db.close()
    flash("Break added successfully.", "success")
    return redirect(dest)


@admin_views_bp.route("/update_break", methods=["POST"])
@admin_views_bp.route("/update_break/<int:bid>", methods=["POST"])
@admin_required
def update_break(bid=None):
    if bid is None:
        try: bid = int(request.form.get("break_id", ""))
        except: return redirect("/employees?tab=schedule")
    name     = request.form.get("break_name", "").strip()
    btime    = request.form.get("break_time", "")
    duration = int(request.form.get("duration_minutes", 10) or 10)
    active   = 1 if request.form.get("is_active") else 0
    dest     = _safe_redirect(request.form.get("redirect", ""), _safe_referrer_redirect(request.referrer or "", "/employees?tab=schedule"))
    sid_raw  = request.form.get("shift_id", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if sid_raw.isdigit():
        cursor.execute(
            "UPDATE break_config SET break_name=%s, break_time=%s, duration_minutes=%s, is_active=%s, shift_id=%s WHERE id=%s",
            (name, btime, duration, active, int(sid_raw), bid)
        )
    else:
        cursor.execute(
            "UPDATE break_config SET break_name=%s, break_time=%s, duration_minutes=%s, is_active=%s WHERE id=%s",
            (name, btime, duration, active, bid)
        )
    db.commit(); cursor.close(); db.close()
    flash("Break updated.", "success")
    return redirect(dest)


@admin_views_bp.route("/delete_break", methods=["POST"])
@admin_views_bp.route("/delete_break/<int:bid>", methods=["POST"])
@admin_required
def delete_break(bid=None):
    if bid is None:
        try: bid = int(request.form.get("break_id", ""))
        except: return redirect("/employees?tab=schedule")
    dest = request.form.get("redirect") or "/employees?tab=schedule"
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM break_config WHERE id=%s", (bid,))
    db.commit(); cursor.close(); db.close()
    flash("Break deleted.", "success")
    return redirect(dest)


@admin_views_bp.route("/email_config", methods=["GET", "POST"])
@admin_required
def email_config():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    if request.method == "POST":
        host       = request.form["smtp_host"].strip()
        port       = int(request.form["smtp_port"])
        user       = request.form["smtp_user"].strip()
        password   = request.form["smtp_pass"].strip()
        from_name  = request.form.get("from_name", "Attendance System").strip()
        from_email = request.form.get("from_email", "").strip() or user

        cursor.execute("DELETE FROM email_config")
        cursor.execute(
            "INSERT INTO email_config (smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email) VALUES (%s,%s,%s,%s,%s,%s)",
            (host, port, user, encrypt_pii(password), from_name, from_email)
        )
        db.commit()
        cursor.close()
        db.close()
        return redirect("/settings?tab=email&saved=1")

    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email FROM email_config ORDER BY id DESC LIMIT 1")
    row    = cursor.fetchone()
    config = {"host": row[0], "port": row[1], "user": row[2], "password": decrypt_pii(row[3]), "from_name": row[4], "from_email": row[5] or row[2]} if row else None
    cursor.close()
    db.close()

    return render_template("email_config.html",
        config=config,
        saved=request.args.get("saved") == "1",
        active_nav="salary",
    )


@admin_views_bp.route("/test_email", methods=["POST"])
@admin_required
def test_email():
    to_email = request.form.get("test_to", "").strip()
    config   = get_email_config()
    if not config:
        return jsonify({"ok": False, "msg": "Email not configured yet."})
    if not to_email:
        return jsonify({"ok": False, "msg": "Enter a test recipient email."})
    try:
        send_email_smtp(
            to_email,
            "Test Email - Attendance System",
            "<h2>Test email from Employee Attendance System</h2><p>Email configuration is working correctly.</p>",
            config,
        )
        return jsonify({"ok": True, "msg": f"Test email sent to {to_email}"})
    except Exception:
        app_log.error("Test email send failed", exc_info=True)
        return jsonify({"ok": False, "msg": "Failed to send test email. Check email settings."})


@admin_views_bp.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
def api_login():
    data     = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if "\x00" in username or "\x00" in password:
        return jsonify({"ok": False, "msg": "Invalid credentials"}), 401
    with _db() as (cursor, conn):
        cursor.execute("SELECT password FROM admin_users WHERE username=%s", (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[0], password):
            token = secrets.token_hex(32)
            cursor.execute(
                "INSERT INTO api_tokens (token, token_type, identity, expires_at) "
                "VALUES (%s, 'admin', %s, NOW() + INTERVAL '24 hours')",
                (_hash_token(token), username)
            )
            conn.commit()
            return jsonify({"ok": True, "token": token, "username": username})
    return jsonify({"ok": False, "msg": "Invalid credentials"}), 401


@admin_views_bp.route("/api/logout", methods=["POST"])
def api_logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        with _db() as (cursor, conn):
            cursor.execute("DELETE FROM api_tokens WHERE token=%s", (_hash_token(auth[7:]),))
            conn.commit()
    return jsonify({"ok": True})


@admin_views_bp.route("/api/dashboard", methods=["GET"])
@api_required
def api_dashboard():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND login_time IS NOT NULL",
        (today,)
    )
    present = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND status='Late Login'",
        (today,)
    )
    late = cursor.fetchone()[0]
    cursor.execute("""
        SELECT e.employee_id, e.name, a.login_time, a.logout_time, a.status,
               a.logout_status, a.attendance_type
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s
        ORDER BY e.name
    """, (today,))
    rows = cursor.fetchall()
    today_rows = [
        {
            "employee_id": r[0], "name": r[1],
            "login_time":  str(r[2]) if r[2] else None,
            "logout_time": str(r[3]) if r[3] else None,
            "login_status": r[4], "logout_status": r[5], "attendance_type": r[6],
        }
        for r in rows
    ]
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE recipient_type='admin' AND is_read=FALSE")
    unread_notifications = cursor.fetchone()[0]
    cursor.close(); db.close()

    return jsonify({
        "ok": True, "total": total, "present": present,
        "absent": total - present, "late": late,
        "today": today.strftime("%d %b %Y"), "today_rows": today_rows,
        "pending_leaves": pending_leaves, "pending_resignations": pending_resignations,
        "pending_tickets": pending_tickets, "unread_notifications": unread_notifications,
    })


@admin_views_bp.route("/api/email_config", methods=["GET"])
@api_required
def api_get_email_config():
    cfg = get_email_config()
    # Never return the SMTP password to clients — they only need to know config exists.
    safe_cfg = {k: v for k, v in cfg.items() if k != "password"}
    safe_cfg["password_set"] = bool(cfg.get("password"))
    return jsonify({"ok": True, "config": safe_cfg})


@admin_views_bp.route("/api/email_config", methods=["POST"])
@api_required
def api_save_email_config():
    data      = request.get_json() or {}
    host      = data.get("smtp_host", "").strip()
    port      = int(data.get("smtp_port", 587))
    user      = data.get("smtp_user", "").strip()
    password  = data.get("smtp_pass", "").strip()
    from_name = data.get("from_name", "HR Department").strip()
    if not host or not user or not password:
        return jsonify({"ok": False, "msg": "host, user and password required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM email_config")
    cursor.execute(
        "INSERT INTO email_config (smtp_host, smtp_port, smtp_user, smtp_pass, from_name) VALUES (%s,%s,%s,%s,%s)",
        (host, port, user, encrypt_pii(password), from_name)
    )
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@admin_views_bp.route("/api/admin/employee/<emp_id>/reset-fingerprint", methods=["POST"])
@admin_required
def admin_reset_employee_fingerprint(emp_id):
    """Admin: clear a specific employee's WebAuthn credential so they can re-enroll on a new device."""
    emp_id = emp_id.strip().upper()
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(
            "UPDATE employees SET fingerprint_credential_id=NULL, fingerprint_public_key=NULL, "
            "fingerprint_sign_count=0 WHERE employee_id=%s",
            (emp_id,)
        )
        db.commit()
        affected = cursor.rowcount
        cursor.close(); db.close()
        if affected == 0:
            return jsonify({"ok": False, "msg": "Employee not found"}), 404
        _audit("admin_reset_fingerprint", "employees", emp_id)
        return jsonify({"ok": True})
    except Exception:
        app_log.error("Failed to reset employee fingerprint", exc_info=True)
        return jsonify({"ok": False, "msg": "Failed to reset fingerprint. Please try again."}), 500


@admin_views_bp.route("/admin_payslips")
@admin_required
def admin_payslips():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("SELECT employee_id, name, role, COALESCE(phone,''), COALESCE(email,'') FROM employees ORDER BY name")
    employees = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]

    cursor.close(); db.close()

    today = datetime.date.today()
    slip_months = []
    y, m = today.year, today.month
    for _ in range(12):
        slip_months.append((y, m, calendar.month_name[m]))
        m -= 1
        if m == 0:
            m = 12; y -= 1

    return render_template("admin_payslips.html",
        employees=employees,
        slip_months=slip_months,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets
    ,
        active_nav="salary",
    )


@admin_views_bp.route("/payroll_settings", methods=["GET", "POST"])
@admin_required
def payroll_settings():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Ensure at least one row exists
    cursor.execute("SELECT COUNT(*) FROM payroll_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO payroll_config (pf_employee_pct, pf_employer_pct, professional_tax, tds_annual_pct, pf_basic_cap) VALUES (12,12,200,0,15000)")
        db.commit()

    if request.method == "POST":
        pf_emp  = float(request.form.get("pf_employee_pct", 12))
        pf_er   = float(request.form.get("pf_employer_pct", 12))
        pt      = float(request.form.get("professional_tax", 200))
        tds     = float(request.form.get("tds_annual_pct", 0))
        pf_cap  = float(request.form.get("pf_basic_cap", 15000))
        cursor.execute("""
            UPDATE payroll_config SET pf_employee_pct=%s, pf_employer_pct=%s,
            professional_tax=%s, tds_annual_pct=%s, pf_basic_cap=%s
        """, (pf_emp, pf_er, pt, tds, pf_cap))
        db.commit()

        # Update per-employee monthly CTC / basic_pct if submitted
        emp_ids = request.form.getlist("emp_id")
        for eid in emp_ids:
            ctc  = request.form.get(f"ctc_{eid}", "")
            bpct = request.form.get(f"bpct_{eid}", "50")
            if ctc:
                spd = round(float(ctc) / 26, 2)
                cursor.execute("""
                    INSERT INTO salary_config (employee_id, salary_per_day, monthly_ctc, basic_pct)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (employee_id) DO UPDATE SET
                        salary_per_day=%s, monthly_ctc=%s, basic_pct=%s
                """, (eid, spd, ctc, bpct, spd, ctc, bpct))
        db.commit()
        flash("Payroll settings saved.", "success")
        cursor.close(); db.close()
        return redirect("/payroll_settings")

    cursor.execute("SELECT pf_employee_pct, pf_employer_pct, professional_tax, tds_annual_pct, pf_basic_cap FROM payroll_config LIMIT 1")
    cfg = cursor.fetchone() or (12, 12, 200, 0, 15000)

    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, e.department,
               COALESCE(s.monthly_ctc, 0), COALESCE(s.salary_per_day, 0), COALESCE(s.basic_pct, 50)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    employees = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(company_name,'') FROM company_settings LIMIT 1")
    co = cursor.fetchone()
    cursor.close(); db.close()

    return render_template("payroll_settings.html",
        cfg=cfg, employees=employees,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        co=co
    ,
        active_nav="salary",
    )


@admin_views_bp.route("/analytics")
@admin_required
def analytics():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("SELECT company_name FROM company_settings LIMIT 1")
    row = cursor.fetchone()
    co = type('Co', (), {'company_name': row[0] if row else 'My Company'})()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]

    today = datetime.date.today()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]

    _doj_start = today.replace(day=1)
    _doj_end   = datetime.date(today.year + 1, 1, 1) if today.month == 12 else today.replace(month=today.month + 1, day=1)
    cursor.execute(
        "SELECT COUNT(*) FROM employees WHERE date_of_joining >= %s AND date_of_joining < %s",
        (_doj_start, _doj_end)
    )
    new_this_month = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(DISTINCT employee_id) FROM attendance WHERE date=%s AND login_time IS NOT NULL",
        (today,)
    )
    today_present = cursor.fetchone()[0]
    today_absent = max(0, total_employees - today_present)

    cursor.execute("SELECT date FROM holidays")
    all_holidays = {r[0] for r in cursor.fetchall()}

    def _working_days_in_month(y, m):
        _, last_day = calendar.monthrange(y, m)
        days = []
        for d in range(1, last_day + 1):
            dt = datetime.date(y, m, d)
            if dt.weekday() != 6 and dt not in all_holidays:
                days.append(dt)
        return days

    monthly_series = []
    for i in range(5, -1, -1):
        ref = today.replace(day=1) - datetime.timedelta(days=1) * (i * 28)
        ref = ref.replace(day=1)
        y, m = ref.year, ref.month
        working_days = _working_days_in_month(y, m)
        if not working_days:
            continue
        past_days = [d for d in working_days if d <= today]
        total_days = len(past_days)
        if total_days == 0:
            monthly_series.append({
                'month_label': datetime.date(y, m, 1).strftime("%b %Y"),
                'total_days': 0, 'present_days': 0, 'absent_days': 0, 'att_pct': 0
            })
            continue
        month_start = datetime.date(y, m, 1)
        if m == 12:
            month_end = datetime.date(y + 1, 1, 1)
        else:
            month_end = datetime.date(y, m + 1, 1)
        cursor.execute("""
            SELECT COUNT(DISTINCT employee_id) FROM attendance
            WHERE date >= %s AND date < %s AND login_time IS NOT NULL
        """, (month_start, month_end))
        present_records = cursor.fetchone()[0]
        expected = total_days * (total_employees or 1)
        present_pct = round(present_records / expected * 100, 1) if expected else 0
        monthly_series.append({
            'month_label': month_start.strftime("%b %Y"),
            'total_days': total_days,
            'present_days': present_records,
            'absent_days': max(0, expected - present_records),
            'att_pct': present_pct
        })

    if today.month >= 1:
        y, m = today.year, today.month
        working_days = _working_days_in_month(y, m)
        past_days = [d for d in working_days if d <= today]
        total_m = len(past_days)
        if total_m > 0:
            _ms = datetime.date(y, m, 1)
            _me = datetime.date(y + 1, 1, 1) if m == 12 else datetime.date(y, m + 1, 1)
            cursor.execute("""
                SELECT COUNT(DISTINCT employee_id) FROM attendance
                WHERE date >= %s AND date < %s AND login_time IS NOT NULL
            """, (_ms, _me))
            present_m = cursor.fetchone()[0]
            expected_m = total_m * (total_employees or 1)
            avg_attendance_pct = round(present_m / expected_m * 100, 1) if expected_m else 0
        else:
            avg_attendance_pct = 0
    else:
        avg_attendance_pct = 0

    cursor.execute("""
        SELECT department, COUNT(*) as cnt FROM employees
        WHERE department IS NOT NULL AND department != ''
        GROUP BY department ORDER BY cnt DESC
    """)
    dept_data = [{'department': r[0], 'count': r[1]} for r in cursor.fetchall()]

    cursor.execute("""
        SELECT lt.name, COUNT(*) as cnt
        FROM leave_requests lr
        JOIN leave_types lt ON lr.leave_type_id = lt.id
        WHERE lr.status='Approved' AND EXTRACT(YEAR FROM lr.leave_date)=%s
        GROUP BY lt.name ORDER BY cnt DESC
    """, (today.year,))
    leave_by_type = [{'name': r[0], 'count': r[1]} for r in cursor.fetchall()]

    cursor.execute("""
        SELECT e.employee_id, e.name,
               ROUND(COUNT(CASE WHEN a.login_time IS NOT NULL THEN 1 END)::NUMERIC /
                     GREATEST((LEAST((date_trunc('month', %s::date) + INTERVAL '1 month - 1 day')::date, %s::date) - %s::date) + 1, 1) * 100, 1) AS pct
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND EXTRACT(MONTH FROM a.date)=%s AND EXTRACT(YEAR FROM a.date)=%s
        GROUP BY e.employee_id, e.name
        ORDER BY pct DESC LIMIT 5
    """, (datetime.date(today.year, today.month, 1), today, datetime.date(today.year, today.month, 1), today.month, today.year))
    top_present = [{'name': r[1], 'employee_id': r[0], 'pct': float(r[2] or 0)} for r in cursor.fetchall()]

    cursor.execute("""
        SELECT gender, COUNT(*) as cnt FROM employees
        WHERE gender IS NOT NULL AND gender != ''
        GROUP BY gender
    """)
    gender_data = [{'gender': r[0], 'count': r[1]} for r in cursor.fetchall()]

    # Attendance heatmap — last 35 days (5 weeks) present count per day
    heatmap_start = today - datetime.timedelta(days=34)
    cursor.execute("""
        SELECT date, COUNT(DISTINCT employee_id) as cnt
        FROM attendance
        WHERE date BETWEEN %s AND %s AND login_time IS NOT NULL
        GROUP BY date
    """, (heatmap_start, today))
    heatmap_raw = {r[0]: r[1] for r in cursor.fetchall()}
    heatmap_data = []
    for i in range(35):
        d = heatmap_start + datetime.timedelta(days=i)
        heatmap_data.append({'date': d.strftime('%Y-%m-%d'), 'day': d.strftime('%a'), 'count': heatmap_raw.get(d, 0)})

    # Department-wise attendance rate this month
    cursor.execute("""
        SELECT e.department,
               COUNT(DISTINCT e.employee_id) as total_emp,
               COUNT(DISTINCT CASE WHEN a.login_time IS NOT NULL THEN a.employee_id END) as present_emp
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND EXTRACT(MONTH FROM a.date)=%s AND EXTRACT(YEAR FROM a.date)=%s
        WHERE e.department IS NOT NULL AND e.department != ''
        GROUP BY e.department
        ORDER BY present_emp DESC
    """, (today.month, today.year))
    dept_attendance = []
    for r in cursor.fetchall():
        dept, total, present = r[0], r[1], r[2]
        pct = round(present / total * 100, 1) if total else 0
        dept_attendance.append({'dept': dept, 'total': total, 'present': present, 'pct': pct})

    # Late arrival trend — last 14 days
    late_start = today - datetime.timedelta(days=13)
    cursor.execute("""
        SELECT date, COUNT(DISTINCT employee_id) as late_cnt
        FROM attendance
        WHERE date BETWEEN %s AND %s AND status='Late Login'
        GROUP BY date ORDER BY date ASC
    """, (late_start, today))
    late_raw = {r[0]: r[1] for r in cursor.fetchall()}
    late_trend = []
    for i in range(14):
        d = late_start + datetime.timedelta(days=i)
        late_trend.append({'date': d.strftime('%d %b'), 'count': late_raw.get(d, 0)})

    # Employee retention — tenure bands
    cursor.execute("SELECT date_of_joining FROM employees WHERE date_of_joining IS NOT NULL")
    retention = {'0-6m': 0, '6-12m': 0, '1-3y': 0, '3y+': 0}
    for (doj,) in cursor.fetchall():
        if isinstance(doj, str):
            try: doj = datetime.date.fromisoformat(doj)
            except Exception as _e:
                app_log.debug("Skipping bad date_of_joining value %r: %s", doj, _e)
                continue
        months = (today.year - doj.year) * 12 + (today.month - doj.month)
        if months < 6:       retention['0-6m'] += 1
        elif months < 12:    retention['6-12m'] += 1
        elif months < 36:    retention['1-3y'] += 1
        else:                retention['3y+'] += 1

    # Smart Alerts Panel
    smart_alerts = []

    # 1. Employees absent 3+ consecutive working days
    working_days_back = []
    for i in range(1, 15):
        d = today - datetime.timedelta(days=i)
        if d.weekday() != 6 and d not in all_holidays:
            working_days_back.append(d)
        if len(working_days_back) == 5:
            break
    last3 = working_days_back[:3]
    if len(last3) == 3:
        cursor.execute("""
            SELECT e.name, e.employee_id
            FROM employees e
            WHERE NOT EXISTS (
                SELECT 1 FROM attendance a
                WHERE a.employee_id = e.employee_id
                AND a.date IN (%s,%s,%s)
                AND a.login_time IS NOT NULL
            )
        """, (last3[0], last3[1], last3[2]))
        absent3 = cursor.fetchall()
        if absent3:
            names = ', '.join(r[1] for r in absent3[:3])
            extra = f' +{len(absent3)-3} more' if len(absent3) > 3 else ''
            smart_alerts.append({
                'level': 'danger',
                'icon': 'ti-user-off',
                'title': f'{len(absent3)} employee{"s" if len(absent3)>1 else ""} absent for 3+ consecutive days',
                'detail': names + extra,
                'link': '/monthly_report'
            })

    # 2. Leave requests spike this week vs last week
    week_start = today - datetime.timedelta(days=today.weekday())
    last_week_start = week_start - datetime.timedelta(days=7)
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE leave_date >= %s", (week_start,))
    leaves_this_week = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE leave_date >= %s AND leave_date < %s", (last_week_start, week_start))
    leaves_last_week = cursor.fetchone()[0]
    if leaves_last_week > 0 and leaves_this_week > leaves_last_week * 1.4:
        pct_jump = round((leaves_this_week - leaves_last_week) / leaves_last_week * 100)
        smart_alerts.append({
            'level': 'warning',
            'icon': 'ti-calendar-up',
            'title': f'Leave requests spiked {pct_jump}% compared to last week',
            'detail': f'{leaves_this_week} requests this week vs {leaves_last_week} last week',
            'link': '/leave_requests'
        })

    # 3. Employees with attendance below 50% this month
    cursor.execute("""
        SELECT e.name, e.employee_id,
               COUNT(CASE WHEN a.login_time IS NOT NULL THEN 1 END) as present_days,
               COUNT(a.date) as total_days
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id
            AND EXTRACT(MONTH FROM a.date)=%s AND EXTRACT(YEAR FROM a.date)=%s
        GROUP BY e.employee_id, e.name
        HAVING COUNT(a.date) > 0
           AND (COUNT(CASE WHEN a.login_time IS NOT NULL THEN 1 END)::NUMERIC / COUNT(a.date)) < 0.5
    """, (today.month, today.year))
    low_att = cursor.fetchall()
    if low_att:
        names = ', '.join(r[1] for r in low_att[:3])
        extra = f' +{len(low_att)-3} more' if len(low_att) > 3 else ''
        smart_alerts.append({
            'level': 'warning',
            'icon': 'ti-chart-bar-off',
            'title': f'{len(low_att)} employee{"s" if len(low_att)>1 else ""} below 50% attendance this month',
            'detail': names + extra,
            'link': '/monthly_report'
        })

    # 4. High pending leave approvals
    if pending_leaves >= 5:
        smart_alerts.append({
            'level': 'warning',
            'icon': 'ti-clock-pause',
            'title': f'{pending_leaves} leave requests pending approval',
            'detail': 'Employees may be waiting — review and approve',
            'link': '/leave_requests'
        })

    # 5. New joiners who have never logged in
    cursor.execute("""
        SELECT e.name, e.employee_id FROM employees e
        WHERE e.date_of_joining >= %s
        AND NOT EXISTS (SELECT 1 FROM attendance a WHERE a.employee_id=e.employee_id AND a.login_time IS NOT NULL)
    """, (today - datetime.timedelta(days=30),))
    never_logged = cursor.fetchall()
    if never_logged:
        names = ', '.join(r[1] for r in never_logged[:3])
        extra = f' +{len(never_logged)-3} more' if len(never_logged) > 3 else ''
        smart_alerts.append({
            'level': 'info',
            'icon': 'ti-user-question',
            'title': f'{len(never_logged)} new joiner{"s" if len(never_logged)>1 else ""} {"have" if len(never_logged)>1 else "has"} never logged attendance',
            'detail': names + extra,
            'link': '/employees'
        })

    # 6. Pending overtime approvals
    cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE status='Pending'")
    ot_pending_count = cursor.fetchone()[0]
    if ot_pending_count >= 3:
        smart_alerts.append({
            'level': 'info',
            'icon': 'ti-clock-bolt',
            'title': f'{ot_pending_count} overtime requests waiting for approval',
            'detail': 'Review pending OT requests from the dashboard',
            'link': '/overtime'
        })

    # 6. Documents expiring in next 30 days
    cursor.execute("""
        SELECT COUNT(*) FROM employee_documents
        WHERE expiry_date IS NOT NULL
          AND expiry_date >= CURRENT_DATE
          AND expiry_date <= CURRENT_DATE + INTERVAL '30 days'
    """)
    expiring_docs = cursor.fetchone()[0]
    if expiring_docs > 0:
        smart_alerts.append({
            'level': 'warning',
            'icon': 'ti-file-alert',
            'title': f'{expiring_docs} employee document{"s" if expiring_docs > 1 else ""} expiring within 30 days',
            'detail': 'Review and renew documents before they expire',
            'link': '/documents'
        })

    if not smart_alerts:
        smart_alerts.append({
            'level': 'success',
            'icon': 'ti-circle-check',
            'title': 'All systems healthy — no anomalies detected',
            'detail': 'Attendance, leaves and approvals are all on track',
            'link': ''
        })

    cursor.close(); db.close()

    return render_template("analytics.html",
        co=co,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        total_employees=total_employees,
        new_this_month=new_this_month,
        today_present=today_present,
        today_absent=today_absent,
        avg_attendance_pct=avg_attendance_pct,
        monthly_series=monthly_series,
        dept_data=dept_data,
        leave_by_type=leave_by_type,
        top_present=top_present,
        gender_data=gender_data,
        heatmap_data=heatmap_data,
        dept_attendance=dept_attendance,
        late_trend=late_trend,
        retention=retention,
        smart_alerts=smart_alerts,
    
        active_nav="analytics",
    )


@admin_views_bp.route("/audit_logs")
def audit_logs_redirect():
    return redirect("/admin_tools?tab=audit_logs")


@admin_views_bp.route("/admin_tools")
@admin_required
def admin_tools():
    tab = request.args.get("tab", "org_chart")
    db = get_db_connection(); cursor = db.cursor(buffered=True)

    active_cid = session.get("active_company_id")
    _co_sub    = "AND employee_id IN (SELECT employee_id FROM employees WHERE company_id=%s)" if active_cid else ""
    _co_args   = (active_cid,) if active_cid else ()
    _co_emp    = "AND company_id=%s" if active_cid else ""

    cursor.execute(f"SELECT COUNT(*) FROM leave_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_leaves = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM resignation_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_resignations = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM tickets WHERE status='Open' {_co_sub}", _co_args)
    pending_tickets = cursor.fetchone()[0]

    if active_cid:
        cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != '' AND company_id=%s ORDER BY department", (active_cid,))
    else:
        cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != '' ORDER BY department")
    departments = [r[0] for r in cursor.fetchall()]

    # Audit logs — filter by employees of the active company when set
    actor_f  = request.args.get("actor", "").strip()
    action_f = request.args.get("action", "").strip()
    date_f   = request.args.get("date", "").strip()
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 50
    conditions, params = [], []
    if actor_f:  conditions.append("actor LIKE %s"); params.append(f"%{actor_f}%")
    if action_f: conditions.append("action LIKE %s"); params.append(f"%{action_f}%")
    if date_f:   conditions.append("DATE(created_at) = %s"); params.append(date_f)
    if active_cid:
        # Show logs where the target_id is an employee of the active company,
        # OR the actor is an employee of the active company, OR it's an admin action
        conditions.append(
            "(target_id IN (SELECT employee_id FROM employees WHERE company_id=%s) "
            "OR actor IN (SELECT employee_id FROM employees WHERE company_id=%s) "
            "OR actor_type='admin')"
        )
        params += [active_cid, active_cid]
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    cursor.execute(f"SELECT COUNT(*) FROM audit_logs {where}", params)
    total = cursor.fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    cursor.execute(
        f"""SELECT id, actor, actor_type, action, target_table, target_id,
                   detail, ip_address, created_at
            FROM audit_logs {where} ORDER BY created_at DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset]
    )
    logs = cursor.fetchall()
    if active_cid:
        cursor.execute(
            "SELECT DISTINCT actor FROM audit_logs WHERE actor IN "
            "(SELECT employee_id FROM employees WHERE company_id=%s) OR actor_type='admin' ORDER BY actor LIMIT 200",
            (active_cid,)
        )
    else:
        cursor.execute("SELECT DISTINCT actor FROM audit_logs ORDER BY actor LIMIT 200")
    actors = [r[0] for r in cursor.fetchall()]

    co = get_company_settings()
    cursor.close(); db.close()
    return render_template("admin_tools.html",
        co=co, tab=tab, departments=departments,
        logs=logs, total=total, page=page, total_pages=total_pages,
        actor_f=actor_f, action_f=action_f, date_f=date_f, actors=actors,
        pending_leaves=pending_leaves, pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    
        active_nav="admin_tools",
    )

