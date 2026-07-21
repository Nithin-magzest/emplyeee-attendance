"""Employees blueprint — CRUD, photos, QR codes, ID cards, API."""
import os
import io
import csv
import secrets
import datetime
import psycopg2

from flask import (Blueprint, session, request, redirect, render_template,
                   flash, url_for, jsonify, send_file, send_from_directory,
                   abort, Response, current_app)

from extensions import app_log
from database import get_db_connection
from utils.auth import (admin_required, employee_required,
                        api_required, generate_password_hash)
from utils.helpers import (_audit, _validate_image_file, _validate_upload,
                           get_company_settings, encrypt_pii, decrypt_pii, _db)
from utils.email_utils import get_email_config, send_email_smtp
from qr_generator import generate_qr
from app import assign_leave_balances_for_employee, _enroll_fingerprint_from_form

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset")

try:
    import face_recognition
    _face_recognition_available = True
except Exception:
    face_recognition = None
    _face_recognition_available = False

employees_bp = Blueprint("employees", __name__)


def _td_to_time(val):
    if val is None:
        return None
    if isinstance(val, datetime.time):
        return val
    total = int(val.total_seconds())
    h, rem = divmod(total, 3600)
    m, s   = divmod(rem, 60)
    return datetime.time(h % 24, m, s)


def _build_id_card_buf(emp_id):
    """Generate the front+back ID card PNG and return a BytesIO buffer, or None if not found."""
    from PIL import Image, ImageDraw, ImageFont
    import io as _io2

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, e.email, e.face_image, e.date_of_joining,
               sh.name AS shift_name, e.blood_group, e.phone
        FROM employees e
        LEFT JOIN shifts sh ON e.shift_id = sh.id
        WHERE e.employee_id = %s
    """, (emp_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("""
            SELECT employee_id, name, role, email, face_image, date_of_joining,
                   NULL, blood_group, phone
            FROM employees WHERE employee_id=%s
        """, (emp_id,))
        row = cursor.fetchone()
    cursor.close(); db.close()

    if not row:
        return None

    DARK  = (15,  40, 100)
    BLUE  = (30,  58, 138)
    MID   = (37,  99, 235)
    LIGHT = (59, 130, 246)
    PALE  = (219, 234, 254)
    WHITE = (255, 255, 255)
    LGRAY = (241, 245, 249)
    MGRAY = (100, 116, 139)
    DGRAY = (15,  23,  42)
    GOLD  = (251, 191,  36)
    RED   = (220,  38,  38)

    def fnt(size, bold=False):
        candidates = (
            ["C:/Windows/Fonts/arialbd.ttf",
             "C:/Windows/Fonts/calibrib.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if bold else
            ["C:/Windows/Fonts/arial.ttf",
             "C:/Windows/Fonts/calibri.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for p in candidates:
            try: return ImageFont.truetype(p, size)
            except: pass
        return ImageFont.load_default()

    def _safe_text(text):
        try:
            text.encode('latin-1')
            return text
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text.encode('ascii', 'replace').decode('ascii')

    def tw(draw, text, font):
        bb = draw.textbbox((0, 0), _safe_text(text), font=font)
        return bb[2] - bb[0]

    def cx(draw, text, font, card_w, y, color):
        t = _safe_text(text)
        draw.text(((card_w - tw(draw, t, font)) // 2, y), t, font=font, fill=color)

    CW, CH = 500, 820

    # ── FRONT ──────────────────────────────────────────────
    front = Image.new("RGB", (CW, CH), WHITE)
    fd    = ImageDraw.Draw(front)

    fd.rectangle([(0, 0), (CW, 110)], fill=BLUE)
    fd.ellipse([(CW-100, -60), (CW+60, 100)], fill=MID)
    cx(fd, "EMPLOYEE ID CARD", fnt(18, bold=True), CW, 18, WHITE)
    cx(fd, "Attendance Management System", fnt(11), CW, 52, PALE)
    fd.rectangle([(0, 108), (CW, 113)], fill=GOLD)

    fd.rectangle([(0, 113), (CW, 370)], fill=LGRAY)
    PH_W, PH_H = 160, 190
    PH_X = CW // 2 - PH_W // 2
    PH_Y = 128
    fd.rounded_rectangle([(PH_X-5, PH_Y-5), (PH_X+PH_W+5, PH_Y+PH_H+5)], radius=8, fill=GOLD)
    fd.rounded_rectangle([(PH_X-2, PH_Y-2), (PH_X+PH_W+2, PH_Y+PH_H+2)], radius=6, fill=WHITE)
    photo_path = os.path.join("dataset", emp_id + ".jpg")
    try:
        ph = Image.open(photo_path).convert("RGB").resize((PH_W, PH_H), Image.LANCZOS)
        front.paste(ph, (PH_X, PH_Y))
    except Exception:
        fd.rounded_rectangle([(PH_X, PH_Y), (PH_X+PH_W, PH_Y+PH_H)], radius=4, fill=MID)
        ini = row[1][0].upper() if row and row[1] else "?"
        cx(fd, ini, fnt(56, bold=True), CW, PH_Y + PH_H // 2 - 38, WHITE)

    cx(fd, (row[1] or "Unknown")[:24], fnt(18, bold=True), CW, 328, DGRAY)
    cx(fd, (row[2] or "Employee")[:28], fnt(12),            CW, 352, MGRAY)
    fd.rectangle([(40, 372), (CW-40, 374)], fill=PALE)

    info_rows = [
        ("Employee ID", row[0]  if row            else "-"),
        ("Email",       row[3]  if row and row[3] else "-"),
        ("Phone",       row[8]  if row and row[8] else "-"),
        ("Blood Group", row[7]  if row and row[7] else "-"),
    ]
    y = 390
    for i, (lbl, val) in enumerate(info_rows):
        if i % 2 == 0:
            fd.rectangle([(0, y-4), (CW, y+38)], fill=LGRAY)
        cx(fd, lbl,           fnt(10),            CW, y+2,  MGRAY)
        cx(fd, str(val)[:34], fnt(13, bold=True), CW, y+17, DGRAY)
        y += 44

    bg_val = row[7] if row and row[7] else None
    if bg_val:
        bw = tw(fd, bg_val, fnt(13, bold=True)) + 28
        bx = (CW - bw) // 2
        by = y + 8
        fd.rounded_rectangle([(bx, by), (bx+bw, by+32)], radius=16, fill=RED)
        cx(fd, bg_val, fnt(13, bold=True), CW, by+8, WHITE)

    fd.rectangle([(0, CH-60), (CW, CH)], fill=BLUE)
    fd.rectangle([(0, CH-62), (CW, CH-60)], fill=GOLD)
    cx(fd, "Confidential  |  Not Transferable", fnt(10), CW, CH-44, PALE)
    cx(fd, "Property of the Organization",       fnt(10), CW, CH-26, (160,185,240))

    # ── BACK ───────────────────────────────────────────────
    back = Image.new("RGB", (CW, CH), LGRAY)
    bd   = ImageDraw.Draw(back)

    bd.rectangle([(0, 0), (CW, 110)], fill=BLUE)
    bd.ellipse([(CW-100, -60), (CW+60, 100)], fill=MID)
    cx(bd, "ATTENDANCE MANAGEMENT SYSTEM", fnt(14, bold=True), CW, 22, WHITE)
    cx(bd, "Employee Attendance Card", fnt(11), CW, 52, PALE)
    bd.rectangle([(0, 108), (CW, 113)], fill=GOLD)

    from qr_generator import generate_qr
    qr_path = os.path.join("static", "qrcodes", emp_id + ".png")
    if not os.path.exists(qr_path):
        qr_path = generate_qr(emp_id)
    QS = 240
    qr_x = (CW - QS) // 2
    qr_y = 148
    bd.rounded_rectangle([(qr_x-16, qr_y-16), (qr_x+QS+16, qr_y+QS+16)], radius=14, fill=WHITE)
    try:
        qr_img = Image.open(qr_path).convert("RGB").resize((QS, QS), Image.LANCZOS)
        back.paste(qr_img, (qr_x, qr_y))
    except Exception:
        cx(bd, "QR NOT AVAILABLE", fnt(13), CW, qr_y+QS//2, MGRAY)

    cx(bd, "Scan to Mark Attendance", fnt(14, bold=True), CW, qr_y+QS+28, BLUE)
    cx(bd, row[0] if row else "",     fnt(12),            CW, qr_y+QS+52, MGRAY)
    bd.rectangle([(40, qr_y+QS+78), (CW-40, qr_y+QS+80)], fill=(203,213,225))

    sub_info = [
        ("Name",        (row[1] or "-")[:26] if row else "-"),
        ("Designation", (row[2] or "-")[:26] if row else "-"),
        ("Blood Group", (row[7] or "-")      if row else "-"),
    ]
    sy = qr_y + QS + 94
    for lbl2, val2 in sub_info:
        cx(bd, lbl2, fnt(10),            CW, sy,    MGRAY)
        cx(bd, val2, fnt(12, bold=True), CW, sy+14, DGRAY)
        sy += 42

    bd.rectangle([(36, sy+8), (CW-36, sy+10)], fill=(203,213,225))
    cx(bd, "If found, please return to:", fnt(10),            CW, sy+18, MGRAY)
    cx(bd, "HR Department",               fnt(12, bold=True), CW, sy+34, BLUE)
    if row and row[3]:
        cx(bd, row[3][:34], fnt(10), CW, sy+54, MGRAY)

    bd.rectangle([(0, CH-100), (CW, CH-68)], fill=DARK)
    bd.rectangle([(0, CH-60),  (CW, CH)],    fill=BLUE)
    bd.rectangle([(0, CH-62),  (CW, CH-60)], fill=GOLD)
    cx(bd, "Authorized Personnel Only  |  Not Transferable", fnt(10), CW, CH-44, PALE)
    cx(bd, "Misuse is subject to disciplinary action",        fnt(10), CW, CH-26, (160,185,240))

    # ── Combine front + back ───────────────────────────────
    GAP, LBL_H = 40, 24
    BGCOL = (215, 225, 240)
    total = Image.new("RGB", (CW*2 + GAP, CH + LBL_H), BGCOL)
    td = ImageDraw.Draw(total)
    td.text((10, 4),               "FRONT", font=fnt(13, bold=True), fill=BLUE)
    td.text((CW + GAP + 10, 4),   "BACK",  font=fnt(13, bold=True), fill=BLUE)
    total.paste(front, (0,      LBL_H))
    total.paste(back,  (CW+GAP, LBL_H))

    buf = _io2.BytesIO()
    total.save(buf, format="PNG", dpi=(200, 200))
    buf.seek(0)
    return buf

@employees_bp.route("/delete_employee/<emp_id>", methods=["POST"])
@admin_required
def delete_employee(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT face_image, qr_code FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    if row:
        for path in row:
            if path and os.path.exists(path):
                os.remove(path)
        cursor.execute("DELETE FROM attendance WHERE employee_id=%s", (emp_id,))
        cursor.execute("DELETE FROM salary_config WHERE employee_id=%s", (emp_id,))
        cursor.execute("DELETE FROM leave_requests WHERE employee_id=%s", (emp_id,))
        cursor.execute("DELETE FROM resignation_requests WHERE employee_id=%s", (emp_id,))
        cursor.execute("DELETE FROM employees WHERE employee_id=%s", (emp_id,))
        db.commit()
        _audit("delete_employee", "employees", emp_id, f"Employee {emp_id} permanently deleted")
        flash(f"Employee '{emp_id}' deleted successfully.", "success")
    else:
        flash(f"Employee '{emp_id}' not found.", "error")
    cursor.close(); db.close()
    return redirect("/employees")



@employees_bp.route("/edit_employee/<emp_id>", methods=["GET"])
@admin_required
def edit_employee_page(emp_id):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT employee_id, name, email, role FROM employees WHERE employee_id=%s", (emp_id,)
    )
    emp = cursor.fetchone()
    cursor.close(); db.close()
    if not emp:
        return "Employee not found", 404
    return render_template("edit_employee.html", emp=emp, active_nav="employees")



@employees_bp.route("/employee_profile/<emp_id>")
@admin_required
def employee_profile(emp_id):
    today = datetime.date.today()
    with _db() as (cursor, db):
        cursor.execute("""
            SELECT employee_id, name, email, role, phone, gender, dob, blood_group,
                   date_of_joining, department, manager_name, work_mode,
                   address, city, state, pincode,
                   emergency_contact_name, emergency_contact_phone, emergency_contact_relation,
                   aadhar_number, pan_number, bank_name, bank_account, bank_ifsc, uan_number,
                   about_me, face_image, shift_id
            FROM employees WHERE employee_id=%s
        """, (emp_id,))
        emp = cursor.fetchone()
        if not emp:
            return "Employee not found", 404
        # Decrypt PII: [19]=aadhar_number, [20]=pan_number, [22]=bank_account, [23]=bank_ifsc, [24]=uan_number
        emp = list(emp)
        for _pii_idx in (19, 20, 22, 23, 24):
            if _pii_idx < len(emp):
                emp[_pii_idx] = decrypt_pii(emp[_pii_idx])

        # Attendance this month
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('Present','Late Login') THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent,
                SUM(CASE WHEN status='Late Login' THEN 1 ELSE 0 END) AS late,
                SUM(CASE WHEN attendance_type='Half Day' THEN 1 ELSE 0 END) AS halfday
            FROM attendance
            WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s
        """, (emp_id, today.month, today.year))
        att = cursor.fetchone()

        # Last 5 attendance records
        cursor.execute("""
            SELECT date, login_time, logout_time, status, attendance_type
            FROM attendance WHERE employee_id=%s
            ORDER BY date DESC LIMIT 5
        """, (emp_id,))
        recent_att = cursor.fetchall()

        # Leave summary this year
        cursor.execute("""
            SELECT lt.name, COUNT(*) as cnt
            FROM leave_requests lr
            LEFT JOIN leave_types lt ON lr.leave_type_id = lt.id
            WHERE lr.employee_id=%s AND lr.status='Approved'
              AND EXTRACT(YEAR FROM lr.leave_date)=%s
            GROUP BY lt.name
        """, (emp_id, today.year))
        leave_used = cursor.fetchall()

        # Pending leaves
        cursor.execute("""
            SELECT COUNT(*) FROM leave_requests
            WHERE employee_id=%s AND status='Pending'
        """, (emp_id,))
        pending_leaves = cursor.fetchone()[0]

        # Salary config
        cursor.execute("SELECT salary_per_day FROM salary_config WHERE employee_id=%s", (emp_id,))
        sal_row = cursor.fetchone()
        salary_per_day = sal_row[0] if sal_row else None

        # Open tickets
        cursor.execute("""
            SELECT COUNT(*) FROM tickets WHERE employee_id=%s AND status IN ('Open','In Progress')
        """, (emp_id,))
        open_tickets = cursor.fetchone()[0]

        # Shift info
        shift_name = None
        if emp[27]:
            cursor.execute("SELECT name, start_time, end_time FROM shifts WHERE id=%s", (emp[27],))
            sh = cursor.fetchone()
            if sh:
                shift_name = f"{sh[0]} ({sh[1]} – {sh[2]})"

    return render_template("employee_profile.html",
        emp=emp,
        att=att,
        recent_att=recent_att,
        leave_used=leave_used,
        pending_leaves=pending_leaves,
        salary_per_day=salary_per_day,
        open_tickets=open_tickets,
        shift_name=shift_name,
        today=today,
    
        active_nav="employees",
    )



@employees_bp.route("/edit_employee", methods=["POST"])
@admin_required
def edit_employee():
    emp_id          = request.form["emp_id"].strip()
    name            = request.form.get("name",            "").strip()
    email           = request.form.get("email",           "").strip() or None
    role            = request.form.get("role",            "").strip() or None
    date_of_joining = request.form.get("date_of_joining", "").strip() or None
    department      = request.form.get("department",      "").strip() or None
    manager_name    = request.form.get("manager_name",    "").strip() or None
    manager_id      = request.form.get("manager_id",      "").strip() or None
    phone           = request.form.get("phone",           "").strip() or None
    gender          = request.form.get("gender",          "").strip() or None
    dob             = request.form.get("dob",             "").strip() or None
    blood_group     = request.form.get("blood_group",     "").strip() or None
    shift_id_raw    = request.form.get("shift_id",        "").strip()
    shift_id        = int(shift_id_raw) if shift_id_raw else None
    address         = request.form.get("address",         "").strip() or None
    city            = request.form.get("city",            "").strip() or None
    state           = request.form.get("state",           "").strip() or None
    pincode         = request.form.get("pincode",         "").strip() or None
    ec_name         = request.form.get("ec_name",         "").strip() or None
    ec_phone        = request.form.get("ec_phone",        "").strip() or None
    ec_rel          = request.form.get("ec_rel",          "").strip() or None
    work_mode       = request.form.get("work_mode",       "office").strip() or "office"
    work_lat_raw    = request.form.get("work_lat",        "").strip()
    work_lon_raw    = request.form.get("work_lon",        "").strip()
    work_lat        = float(work_lat_raw) if work_lat_raw else None
    work_lon        = float(work_lon_raw) if work_lon_raw else None

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE employees SET name=%s, email=%s, role=%s, date_of_joining=%s, "
        "department=%s, manager_name=%s, manager_id=%s, phone=%s, gender=%s, dob=%s, blood_group=%s, "
        "shift_id=%s, address=%s, city=%s, state=%s, pincode=%s, "
        "emergency_contact_name=%s, emergency_contact_phone=%s, emergency_contact_relation=%s, "
        "work_mode=%s, work_lat=%s, work_lon=%s "
        "WHERE employee_id=%s",
        (name, email, role, date_of_joining, department, manager_name, manager_id,
         phone, gender, dob, blood_group, shift_id,
         address, city, state, pincode,
         ec_name, ec_phone, ec_rel,
         work_mode, work_lat, work_lon, emp_id)
    )
    db.commit(); cursor.close(); db.close()
    flash(f"Employee '{emp_id}' updated successfully.", "success")
    return redirect("/employees")



@employees_bp.route("/api/employee_info/<emp_id>")
@admin_required
def api_employee_info(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT employee_id, name, role, email, date_of_joining, "
        "work_mode, work_lat, work_lon, department, manager_name, face_image, qr_code, "
        "phone, gender, dob, blood_group, shift_id, "
        "address, city, state, pincode, "
        "emergency_contact_name, emergency_contact_phone, emergency_contact_relation, "
        "COALESCE(manager_id,'') "
        "FROM employees WHERE employee_id=%s", (emp_id,)
    )
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    (eid, name, role, email, doj, wm, wlat, wlon, dept, mgr, face_image, qr_code,
     phone, gender, dob, blood_group, shift_id,
     address, city, state, pincode,
     ec_name, ec_phone, ec_rel, mgr_id) = row
    return jsonify({
        "emp_id":          eid,
        "name":            name         or "",
        "role":            role         or "",
        "email":           email        or "",
        "doj":             doj.strftime("%Y-%m-%d") if doj else "",
        "work_mode":       wm           or "office",
        "work_lat":        str(wlat)    if wlat else "",
        "work_lon":        str(wlon)    if wlon else "",
        "department":      dept         or "",
        "manager_name":    mgr          or "",
        "manager_id":      mgr_id       or "",
        "has_photo":       bool(face_image and os.path.exists(face_image)),
        "has_qr":          bool(qr_code  and os.path.exists(qr_code)),
        "phone":           phone        or "",
        "gender":          gender       or "",
        "dob":             dob.strftime("%Y-%m-%d") if dob else "",
        "blood_group":     blood_group  or "",
        "shift_id":        shift_id     or "",
        "address":         address      or "",
        "city":            city         or "",
        "state":           state        or "",
        "pincode":         pincode      or "",
        "ec_name":         ec_name      or "",
        "ec_phone":        ec_phone     or "",
        "ec_rel":          ec_rel       or "",
    })



@employees_bp.route("/employees")
@admin_required
def view_employees():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    active_cid = session.get("active_company_id")
    if active_cid:
        cursor.execute("""
            SELECT e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                   COUNT(a.date)  AS total_days,
                   MAX(a.date)    AS last_seen,
                   e.work_mode, e.work_lat, e.work_lon,
                   e.face_image, e.qr_code,
                   e.department, e.phone, e.gender,
                   s.name AS shift_name, e.shift_id
            FROM employees e
            LEFT JOIN attendance a ON e.employee_id = a.employee_id
            LEFT JOIN shifts     s ON e.shift_id = s.id
            WHERE e.company_id = %s
            GROUP BY e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                     e.work_mode, e.work_lat, e.work_lon, e.face_image, e.qr_code,
                     e.department, e.phone, e.gender, s.name, e.shift_id
            ORDER BY e.name
        """, (active_cid,))
    else:
        cursor.execute("""
            SELECT e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                   COUNT(a.date)  AS total_days,
                   MAX(a.date)    AS last_seen,
                   e.work_mode, e.work_lat, e.work_lon,
                   e.face_image, e.qr_code,
                   e.department, e.phone, e.gender,
                   s.name AS shift_name, e.shift_id
            FROM employees e
            LEFT JOIN attendance a ON e.employee_id = a.employee_id
            LEFT JOIN shifts     s ON e.shift_id = s.id
            GROUP BY e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                     e.work_mode, e.work_lat, e.work_lon, e.face_image, e.qr_code,
                     e.department, e.phone, e.gender, s.name, e.shift_id
            ORDER BY e.name
        """)
    employees_raw = cursor.fetchall()

    cursor.execute("SELECT DISTINCT employee_id FROM resignation_requests WHERE status='Accepted'")
    resigned_set  = {r[0] for r in cursor.fetchall()}
    cursor.execute(
        "SELECT DISTINCT employee_id FROM leave_requests "
        "WHERE status='Approved' AND leave_date=CURRENT_DATE"
    )
    on_leave_set  = {r[0] for r in cursor.fetchall()}

    employees = []
    for row in employees_raw:
        eid = row[0]
        if eid in resigned_set:
            emp_status = "Resigned"
        elif eid in on_leave_set:
            emp_status = "On Leave"
        else:
            emp_status = "Active"
        employees.append(row + (emp_status,))

    total          = len(employees)
    active_count   = sum(1 for e in employees if e[-1] == "Active")
    on_leave_count = sum(1 for e in employees if e[-1] == "On Leave")
    resigned_count = sum(1 for e in employees if e[-1] == "Resigned")

    # Full shift details for Schedule tab
    cursor.execute("SELECT id, name, start_time, half_time, end_time FROM shifts ORDER BY start_time")
    shift_full = []
    for sid, sname, st, ht, et in cursor.fetchall():
        shift_full.append({
            "id": sid, "name": sname,
            "start": _td_to_time(st).strftime("%H:%M") if st else "--",
            "half":  _td_to_time(ht).strftime("%H:%M") if ht else "--",
            "end":   _td_to_time(et).strftime("%H:%M") if et else "--",
        })
    # Simple (id, name) list for dropdowns
    cursor.execute("SELECT id, name FROM shifts ORDER BY name")
    shifts = cursor.fetchall()

    # Breaks list
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active FROM break_config ORDER BY break_time")
    breaks_raw = cursor.fetchall()
    breaks_list = []
    for bid, bname, bt, dur, bactive in breaks_raw:
        def _fmt_bt(v):
            if v is None: return "--"
            if isinstance(v, datetime.timedelta): h,m=divmod(int(v.total_seconds())//60,60); return "%02d:%02d"%(h,m)
            return str(v)[:5]
        breaks_list.append({"id": bid, "name": bname, "time": _fmt_bt(bt), "duration": dur, "active": bactive})

    cursor.execute(
        "SELECT department FROM employees "
        "WHERE department IS NOT NULL AND department != '' "
        "GROUP BY department ORDER BY MIN(id) ASC"
    )
    departments = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT id, name FROM companies ORDER BY name")
    companies = cursor.fetchall()
    cursor.execute("SELECT id, name FROM onboarding_templates WHERE is_active=1 ORDER BY name")
    onboarding_templates = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("employees.html",
        employees=employees,
        shifts=shifts,
        shift_full=shift_full,
        breaks_list=breaks_list,
        departments=departments,
        companies=companies,
        onboarding_templates=onboarding_templates,
        total=total,
        active_count=active_count,
        on_leave_count=on_leave_count,
        resigned_count=resigned_count,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        active_nav="employees",
    )



@employees_bp.route("/employee_detail/<emp_id>")
@admin_required
def employee_detail(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, e.email, e.date_of_joining,
               e.work_mode, e.work_lat, e.work_lon,
               e.face_image, e.qr_code,
               e.department, e.phone, e.gender, e.dob, e.blood_group,
               e.shift_id, e.manager_name,
               e.address, e.city, e.state, e.pincode,
               e.emergency_contact_name, e.emergency_contact_phone, e.emergency_contact_relation,
               e.aadhar_number, e.pan_number,
               e.bank_name, e.bank_account, e.bank_ifsc, e.uan_number,
               s.name AS shift_name,
               COUNT(a.date)  AS total_days,
               MAX(a.date)    AS last_seen,
               SUM(CASE WHEN a.attendance_type IN ('Present','Full Day','Approved Leave') OR (a.login_time IS NOT NULL AND a.attendance_type IS NULL) THEN 1 ELSE 0 END) AS full_days,
               SUM(CASE WHEN a.attendance_type='Half Day' THEN 1 ELSE 0 END) AS half_days,
               SUM(CASE WHEN a.attendance_type LIKE 'Late%%' OR a.status='Late Login' THEN 1 ELSE 0 END) AS late_days,
               COALESCE(sc.salary_per_day, 0) AS salary_per_day,
               e.about_me
        FROM employees e
        LEFT JOIN shifts s ON e.shift_id = s.id
        LEFT JOIN attendance a ON e.employee_id = a.employee_id
        LEFT JOIN salary_config sc ON e.employee_id = sc.employee_id
        WHERE e.employee_id = %s
        GROUP BY e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                 e.work_mode, e.work_lat, e.work_lon,
                 e.face_image, e.qr_code,
                 e.department, e.phone, e.gender, e.dob, e.blood_group,
                 e.shift_id, e.manager_name,
                 e.address, e.city, e.state, e.pincode,
                 e.emergency_contact_name, e.emergency_contact_phone, e.emergency_contact_relation,
                 e.aadhar_number, e.pan_number,
                 e.bank_name, e.bank_account, e.bank_ifsc, e.uan_number,
                 s.name, sc.salary_per_day, e.about_me
    """, (emp_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        flash("Employee not found.", "error")
        return redirect("/employees")

    # Decrypt PII fields: [23]=aadhar_number, [24]=pan_number, [26]=bank_account, [27]=bank_ifsc, [28]=uan_number
    row = list(row)
    for _pii_idx in (23, 24, 26, 27, 28):
        if _pii_idx < len(row):
            row[_pii_idx] = decrypt_pii(row[_pii_idx])

    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE employee_id=%s AND status='Accepted'", (emp_id,))
    is_resigned = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE employee_id=%s AND status='Approved' AND leave_date=CURRENT_DATE", (emp_id,))
    is_on_leave = cursor.fetchone()[0] > 0

    if is_resigned:
        emp_status = "Resigned"
    elif is_on_leave:
        emp_status = "On Leave"
    else:
        emp_status = "Active"

    # Recent attendance (last 30 records)
    cursor.execute("""
        SELECT date, login_time, logout_time, attendance_type, status
        FROM attendance WHERE employee_id=%s
        ORDER BY date DESC LIMIT 30
    """, (emp_id,))
    raw_att = cursor.fetchall()

    def _fmt_time(t):
        if t is None:
            return None
        if isinstance(t, datetime.timedelta):
            total = int(t.total_seconds())
            h, rem = divmod(total, 3600)
            m = rem // 60
            suffix = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            return f"{h12:02d}:{m:02d} {suffix}"
        if hasattr(t, 'strftime'):
            return t.strftime('%I:%M %p')
        return str(t)

    recent_attendance = [
        (date, _fmt_time(lt), _fmt_time(lot), att_type, status)
        for date, lt, lot, att_type, status in raw_att
    ]

    # Work experience
    cursor.execute("""
        SELECT company, designation, from_year, to_year, is_current, description
        FROM employee_experience WHERE employee_id=%s ORDER BY from_year DESC
    """, (emp_id,))
    experience = cursor.fetchall()

    # Education
    cursor.execute("""
        SELECT degree, institution, year_of_passing, percentage
        FROM employee_education WHERE employee_id=%s ORDER BY year_of_passing DESC
    """, (emp_id,))
    education = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]

    # Documents for this employee
    cursor.execute(
        "SELECT id, doc_type, original_name, uploaded_by, uploaded_at FROM employee_documents WHERE employee_id=%s ORDER BY uploaded_at DESC",
        (emp_id,)
    )
    emp_docs = cursor.fetchall()

    cursor.close(); db.close()
    return render_template("employee_detail.html",
        emp=row,
        emp_status=emp_status,
        recent_attendance=recent_attendance,
        experience=experience,
        education=education,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        emp_docs=emp_docs,
    
        active_nav="employees",
    )



@employees_bp.route("/add_employee_page", methods=["POST"])
@admin_required
def add_employee_page():
    name            = request.form.get("name", "").strip()
    emp_id          = request.form.get("emp_id", "").strip()
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

    if not name or not emp_id:
        flash("Name and Employee ID are required.", "error")
        return redirect("/employees")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    # Auto-increment emp_id if already taken
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id=%s", (emp_id,))
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

    file = request.files.get("face")
    if not file or not file.filename:
        flash("A face photo is required.", "error")
        cursor.close(); db.close()
        return redirect("/employees")

    _img_ok, _img_err = _validate_image_file(file)
    if not _img_ok:
        flash(_img_err, "error")
        cursor.close(); db.close()
        return redirect("/employees")

    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)

    if _face_recognition_available:
        test_img = face_recognition.load_image_file(filepath)
        if not face_recognition.face_encodings(test_img):
            os.remove(filepath)
            flash("No face detected in the uploaded photo. Please upload a clear, well-lit front-facing photo.", "error")
            cursor.close(); db.close()
            return redirect("/employees")

    auto_pass  = secrets.token_urlsafe(8)
    hashed_pwd = generate_password_hash(auto_pass)

    # Retry up to 5 times in case of duplicate ID collision
    prefix = ''.join(c for c in emp_id if not c.isdigit())
    if not prefix:
        prefix = emp_id
    original_filepath = filepath  # photo was already saved under initial emp_id
    registered = False
    for _attempt in range(5):
        # Keep photo file in sync with the current emp_id on each retry attempt
        new_filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        if new_filepath != original_filepath and os.path.exists(original_filepath):
            try:
                os.rename(original_filepath, new_filepath)
                original_filepath = new_filepath
            except OSError:
                pass
        filepath = new_filepath
        qr_path = generate_qr(emp_id)
        try:
            _mgr_id   = request.form.get("manager_id", "").strip() or None
            _mgr_name = request.form.get("manager_name", "").strip() or None
            _dept     = request.form.get("department", "").strip() or None
            cursor.execute(
                "INSERT INTO employees (name, employee_id, email, role, face_image, qr_code, password, "
                "date_of_joining, work_mode, work_lat, work_lon, company_id, manager_id, manager_name, department, "
                "force_pin_change) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
                (name, emp_id, email, role, filepath, qr_path, hashed_pwd,
                 date_of_joining, work_mode, work_lat, work_lon, company_id,
                 _mgr_id, _mgr_name, _dept)
            )
            db.commit()
            _enroll_fingerprint_from_form(emp_id, cursor, db)
            assign_leave_balances_for_employee(cursor, emp_id)
            db.commit()
            registered = True
            break
        except psycopg2.IntegrityError:
            db.rollback()
            # Find next available ID and retry
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

    if registered:
        flash(f"Employee '{name}' registered! ID: {emp_id} | Password: {auto_pass}", "success")
        # Auto-assign default onboarding template if configured
        cursor.execute("SELECT default_onboarding_template_id FROM company_settings LIMIT 1")
        _cs = cursor.fetchone()
        _default_tpl = _cs[0] if _cs and _cs[0] else None
        if _default_tpl:
            cursor.execute("SELECT id FROM onboarding_templates WHERE id=%s AND is_active=1", (_default_tpl,))
            if cursor.fetchone():
                cursor.execute("""
                    SELECT id FROM employee_onboarding
                    WHERE employee_id=%s AND template_id=%s
                """, (emp_id, _default_tpl))
                if not cursor.fetchone():
                    _due = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
                    cursor.execute("""
                        INSERT INTO employee_onboarding (employee_id, template_id, assigned_date, due_date, status)
                        VALUES (%s, %s, %s, %s, 'In Progress') RETURNING id
                    """, (emp_id, _default_tpl, datetime.date.today().isoformat(), _due))
                    _ob_id = cursor.fetchone()[0]
                    db.commit()
                    cursor.execute("""
                        SELECT id, task_title, task_description, requires_document, due_days, sort_order
                        FROM onboarding_template_tasks WHERE template_id=%s ORDER BY sort_order, id
                    """, (_default_tpl,))
                    for _tt in cursor.fetchall():
                        cursor.execute("""
                            INSERT INTO employee_onboarding_tasks
                            (onboarding_id, template_task_id, employee_id, task_title,
                             task_description, requires_document, due_days, status)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,'Pending')
                        """, (_ob_id, _tt[0], emp_id, _tt[1], _tt[2], _tt[3], _tt[4]))
                    db.commit()
                    flash("Onboarding checklist auto-assigned.", "success")
        if email:
            _ecfg = get_email_config()
            if _ecfg:
                _html = (f"<p>Hi <strong>{name}</strong>, your account is ready.</p>"
                         f"<p>Employee ID: <strong>{emp_id}</strong><br>"
                         f"Password: <strong>{auto_pass}</strong></p>")
                try:
                    send_email_smtp(email, f"Welcome {name} — Your Login Credentials", _html, _ecfg)
                    flash(f"Credentials email sent to {email}", "success")
                except Exception:
                    pass
    else:
        if os.path.exists(filepath):
            os.remove(filepath)
        flash("Registration failed. Please try again.", "error")
    cursor.close(); db.close()
    return redirect("/employees")



@employees_bp.route("/update_employee_photo/<emp_id>", methods=["POST"])
@admin_required
def update_employee_photo(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id=%s", (emp_id,))
    if not cursor.fetchone():
        flash("Employee not found.", "error")
        cursor.close(); db.close()
        return redirect("/employees")

    file = request.files.get("face")
    if not file or not file.filename:
        flash("No photo file provided.", "error")
        cursor.close(); db.close()
        return redirect("/employees")

    _img_ok, _img_err = _validate_image_file(file)
    if not _img_ok:
        flash(_img_err, "error")
        cursor.close(); db.close()
        return redirect("/employees")

    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)

    if _face_recognition_available:
        test_img = face_recognition.load_image_file(filepath)
        if not face_recognition.face_encodings(test_img):
            os.remove(filepath)
            flash("No face detected in the uploaded photo. Please upload a clear front-facing photo.", "error")
            cursor.close(); db.close()
            return redirect("/employees")

    cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (filepath, emp_id))
    db.commit()
    flash(f"Photo updated for employee '{emp_id}'.", "success")
    cursor.close(); db.close()
    return redirect("/employees")



@employees_bp.route("/regenerate_qr/<emp_id>", methods=["POST"])
@admin_required
def regenerate_qr(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id=%s", (emp_id,))
    if not cursor.fetchone():
        flash("Employee not found.", "error")
        cursor.close(); db.close()
        return redirect("/employees")
    from qr_generator import generate_qr
    qr_path = generate_qr(emp_id)
    cursor.execute("UPDATE employees SET qr_code=%s WHERE employee_id=%s", (qr_path, emp_id))
    db.commit()
    flash(f"QR code regenerated for '{emp_id}'.", "success")
    cursor.close(); db.close()
    return redirect("/employees")



@employees_bp.route("/view_qrcodes")
@admin_required
def view_qrcodes():
    return redirect("/view_photos")


@employees_bp.route("/dataset/<path:filename>")
@admin_required
def serve_dataset(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)



@employees_bp.route("/my_photo")
def my_photo():
    emp_id = session.get("employee_id")
    if not emp_id:
        return "", 403
    photo_path = os.path.join(UPLOAD_FOLDER, emp_id + ".jpg")
    if not os.path.exists(photo_path):
        return "", 404
    return send_from_directory(UPLOAD_FOLDER, emp_id + ".jpg")



@employees_bp.route("/view_photos")
@admin_required
def view_photos():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name, role, email, face_image, qr_code FROM employees ORDER BY name")
    employees = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("employee_photos.html", employees=employees,
        active_nav="employees",
    )


@employees_bp.route("/update_photo/<emp_id>", methods=["POST"])
@admin_required
def update_photo(emp_id):
    file = request.files.get("photo")
    ok, err = _validate_image_file(file)
    if not ok:
        return jsonify({"ok": False, "msg": err}), 400
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(save_path)
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (emp_id + ".jpg", emp_id))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@employees_bp.route("/api/generate_emp_id")
def generate_emp_id():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "not logged in"}), 401
    company_id_raw = request.args.get("company_id", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    if company_id_raw.isdigit():
        company_id = int(company_id_raw)
        cursor.execute("SELECT COALESCE(code,''), name FROM companies WHERE id=%s", (company_id,))
        row = cursor.fetchone()
        code         = (row[0] or "").strip().upper() if row else ""
        company_name = row[1] if row else ""
        cursor.execute("SELECT employee_id FROM employees WHERE company_id=%s", (company_id,))
    else:
        cursor.execute("SELECT COALESCE(company_code,'') FROM company_settings LIMIT 1")
        row = cursor.fetchone()
        code         = (row[0] or "").strip().upper() if row else ""
        company_name = ""
        cursor.execute("SELECT employee_id FROM employees WHERE company_id IS NULL")

    # Find max existing sequence number to avoid collisions on deletions
    prefix = code if code else "EMP"
    max_seq = 0
    for (eid,) in cursor.fetchall():
        if eid and eid.upper().startswith(prefix):
            suffix = eid[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

    # Also check all employees globally in case company_id mismatch
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id LIKE %s", (f"{prefix}%",))
    for (eid,) in cursor.fetchall():
        if eid and eid.upper().startswith(prefix):
            suffix = eid[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

    cursor.close(); db.close()
    seq    = max_seq + 1
    emp_id = f"{prefix}{seq:03d}"
    return jsonify({"emp_id": emp_id, "code": code, "seq": seq, "company_name": company_name})



@employees_bp.route("/admin_id_card/<emp_id>")
@admin_required
def admin_id_card(emp_id):
    buf = _build_id_card_buf(emp_id)
    if buf is None:
        return "Employee not found", 404
    return send_file(buf, as_attachment=True,
                     download_name=f"IDCard_{emp_id}.png",
                     mimetype="image/png")


@employees_bp.route("/admin_view_id_card/<emp_id>")
@admin_required
def admin_view_id_card(emp_id):
    buf = _build_id_card_buf(emp_id)
    if buf is None:
        return "Employee not found", 404
    return send_file(buf, as_attachment=False,
                     download_name=f"IDCard_{emp_id}.png",
                     mimetype="image/png")



@employees_bp.route("/api/employees", methods=["GET"])
@api_required
def api_employees():
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))
    offset   = (page - 1) * per_page
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "total": total, "page": page, "per_page": per_page,
                    "employees": [
        {"employee_id": r[0], "name": r[1], "email": r[2], "salary_per_day": float(r[3])}
        for r in rows
    ]})



@employees_bp.route("/api/employees", methods=["POST"])
@api_required
def api_register_employee():
    name   = request.form.get("name", "").strip()
    emp_id = request.form.get("emp_id", "").strip()
    email  = request.form.get("email", "").strip() or None
    file   = request.files.get("face")
    if not name or not emp_id or not file:
        return jsonify({"ok": False, "msg": "name, emp_id and face image required"}), 400
    # Validate extension, MIME type, magic bytes and size before writing to disk.
    ok, err = _validate_image_file(file)
    if not ok:
        return jsonify({"ok": False, "msg": err}), 400
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)
    if _face_recognition_available:
        test_img = face_recognition.load_image_file(filepath)
        if not face_recognition.face_encodings(test_img):
            os.remove(filepath)
            return jsonify({"ok": False, "msg": "No face detected in uploaded photo."}), 400
    qr_path    = generate_qr(emp_id)
    init_pass  = request.form.get("password", "").strip() or emp_id
    hashed_pwd = generate_password_hash(init_pass)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute(
            "INSERT INTO employees (name, employee_id, email, face_image, qr_code, password, force_pin_change) "
            "VALUES (%s,%s,%s,%s,%s,%s,1)",
            (name, emp_id, email, filepath, qr_path, hashed_pwd)
        )
        db.commit()
    except Exception:
        app_log.error("API employee register failed", exc_info=True)
        db.rollback(); cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Failed to create employee. Check for duplicate ID."}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee {name} registered."})



@employees_bp.route("/api/employees/<emp_id>", methods=["GET"])
@api_required
def api_employee_detail(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, e.role, e.date_of_joining,
               COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        WHERE e.employee_id = %s
    """, (emp_id,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    return jsonify({"ok": True, "employee": {
        "employee_id": row[0], "name": row[1], "email": row[2],
        "role": row[3], "date_of_joining": str(row[4]) if row[4] else None,
        "salary_per_day": float(row[5])
    }})



@employees_bp.route("/api/employees/<emp_id>", methods=["PUT"])
@api_required
def api_edit_employee(emp_id):
    data            = request.get_json() or {}
    name            = data.get("name", "").strip()
    email           = data.get("email", "").strip() or None
    role            = data.get("role", "").strip() or None
    date_of_joining = data.get("date_of_joining", "").strip() or None
    if not name:
        return jsonify({"ok": False, "msg": "name required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE employees SET name=%s, email=%s, role=%s, date_of_joining=%s WHERE employee_id=%s",
        (name, email, role, date_of_joining, emp_id)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Employee updated."})



@employees_bp.route("/api/employees/<emp_id>", methods=["DELETE"])
@api_required
def api_delete_employee(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT face_image, qr_code FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    for path in row:
        if path and os.path.exists(path):
            try: os.remove(path)
            except Exception as _e: app_log.warning("Could not delete file %s: %s", path, _e)
    cursor.execute("DELETE FROM attendance WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM salary_config WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM leave_requests WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM resignation_requests WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM tickets WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM employees WHERE employee_id=%s", (emp_id,))
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee '{emp_id}' deleted."})



