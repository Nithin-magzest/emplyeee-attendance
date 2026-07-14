"""Employee portal blueprint — self-service profile, photos, QR/ID card, check-in APIs."""
import os
import calendar
import datetime
from flask import (
    Blueprint, request, session, redirect, jsonify, render_template,
)
from extensions import app, app_log, limiter
from database import get_db_connection
from utils.auth import employee_required, employee_api_required, check_password_hash, generate_password_hash
from utils.helpers import (
    _audit, _db, encrypt_pii, decrypt_pii, _validate_image_file, get_auth_config,
)
from utils.attendance_utils import (
    classify_by_worked_minutes, detect_overtime, infer_type_legacy,
    fetch_holidays_set, get_billable_past_days, _td_to_time, is_within_range,
)
from utils.leave_utils import assign_leave_balances_for_employee
from utils.face_utils import face_recognition, _face_recognition_available, _get_known_face_encoding
from utils.webauthn_utils import _wa_fingerprint_recently_verified, _mobile_biometric_recently_verified
from qr_generator import generate_qr
import utils.config as cfg

employee_portal_bp = Blueprint("employee_portal", __name__)

UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]


def _fmt_t(t):
    if t is None: return None
    if hasattr(t, 'strftime'): return t.strftime("%H:%M:%S")
    total = int(t.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)

@employee_portal_bp.route("/update_my_profile", methods=["POST"])
@employee_required
def update_my_profile():
    emp_id = session["employee_id"]
    fields = {
        "phone":                      request.form.get("phone", "").strip() or None,
        "gender":                     request.form.get("gender", "").strip() or None,
        "dob":                        request.form.get("dob", "").strip() or None,
        "blood_group":                request.form.get("blood_group", "").strip() or None,
        "address":                    request.form.get("address", "").strip() or None,
        "city":                       request.form.get("city", "").strip() or None,
        "state":                      request.form.get("state", "").strip() or None,
        "pincode":                    request.form.get("pincode", "").strip() or None,
        "emergency_contact_name":     request.form.get("emergency_contact_name", "").strip() or None,
        "emergency_contact_phone":    request.form.get("emergency_contact_phone", "").strip() or None,
        "emergency_contact_relation": request.form.get("emergency_contact_relation", "").strip() or None,
        "about_me":                   request.form.get("about_me", "").strip() or None,
    }
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        UPDATE employees SET
            phone=%s, gender=%s, dob=%s, blood_group=%s,
            address=%s, city=%s, state=%s, pincode=%s,
            emergency_contact_name=%s, emergency_contact_phone=%s, emergency_contact_relation=%s,
            about_me=%s
        WHERE employee_id=%s
    """, (*fields.values(), emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?profile_saved=1#my-profile")

@employee_portal_bp.route("/update_my_bank_details", methods=["POST"])
@employee_required
def update_my_bank_details():
    emp_id = session["employee_id"]
    fields = {
        "aadhar_number": encrypt_pii(request.form.get("aadhar_number", "").strip() or None),
        "pan_number":    encrypt_pii(request.form.get("pan_number", "").upper().strip() or None),
        "bank_name":     request.form.get("bank_name", "").strip() or None,
        "bank_account":  encrypt_pii(request.form.get("bank_account", "").strip() or None),
        "bank_ifsc":     encrypt_pii(request.form.get("bank_ifsc", "").upper().strip() or None),
        "uan_number":    encrypt_pii(request.form.get("uan_number", "").strip() or None),
    }
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        UPDATE employees SET
            aadhar_number=%s, pan_number=%s, bank_name=%s,
            bank_account=%s, bank_ifsc=%s, uan_number=%s
        WHERE employee_id=%s
    """, (*fields.values(), emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?bank_saved=1#my-profile")

@employee_portal_bp.route("/add_experience", methods=["POST"])
@employee_required
def add_experience():
    emp_id = session["employee_id"]
    company     = request.form.get("company", "").strip()
    designation = request.form.get("designation", "").strip()
    from_year   = request.form.get("from_year", "").strip()
    to_year     = request.form.get("to_year", "").strip() or None
    is_current  = 1 if request.form.get("is_current") else 0
    description = request.form.get("description", "").strip() or None
    if not company or not designation or not from_year:
        return redirect("/employee_portal?exp_error=1#my-profile")
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO employee_experience (employee_id, company, designation, from_year, to_year, is_current, description) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (emp_id, company, designation, from_year, to_year, is_current, description)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?exp_saved=1#my-profile")

@employee_portal_bp.route("/delete_experience/<int:entry_id>", methods=["POST"])
@employee_required
def delete_experience(entry_id):
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_experience WHERE id=%s AND employee_id=%s", (entry_id, emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal#my-profile")

@employee_portal_bp.route("/add_education_entry", methods=["POST"])
@employee_required
def add_education_entry():
    emp_id = session["employee_id"]
    degree          = request.form.get("degree", "").strip()
    institution     = request.form.get("institution", "").strip()
    year_of_passing = request.form.get("year_of_passing", "").strip() or None
    percentage      = request.form.get("percentage", "").strip() or None
    if not degree or not institution:
        return redirect("/employee_portal?edu_error=1#my-profile")
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO employee_education (employee_id, degree, institution, year_of_passing, percentage) "
        "VALUES (%s,%s,%s,%s,%s)",
        (emp_id, degree, institution, year_of_passing, percentage)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?edu_saved=1#my-profile")

@employee_portal_bp.route("/delete_education_entry/<int:entry_id>", methods=["POST"])
@employee_required
def delete_education_entry(entry_id):
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_education WHERE id=%s AND employee_id=%s", (entry_id, emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal#my-profile")

@employee_portal_bp.route("/update_my_photo", methods=["POST"])
@employee_required
def update_my_photo():
    from flask import send_from_directory
    import numpy as np
    from PIL import Image
    import base64, io
    emp_id = session["employee_id"]
    file = request.files.get("photo")
    ok, err = _validate_image_file(file)
    if not ok:
        return redirect("/employee_portal?photo_error=bad_format#my-profile")
    try:
        img = Image.open(file.stream).convert("RGB")
        img_array = np.array(img)
        if _face_recognition_available:
            locs = face_recognition.face_locations(img_array)
            if not locs:
                return redirect("/employee_portal?photo_error=no_face#my-profile")
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        img.save(save_path, "JPEG", quality=90)
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (emp_id + ".jpg", emp_id))
        db.commit(); cursor.close(); db.close()
        return redirect("/employee_portal?photo_saved=1#my-profile")
    except Exception:
        return redirect("/employee_portal?photo_error=failed#my-profile")

@employee_portal_bp.route("/my_qr")
@employee_required
def my_qr():
    from flask import send_file
    emp_id = session["employee_id"]
    qr_path = os.path.join("static", "qrcodes", emp_id + ".png")
    if not os.path.exists(qr_path):
        # Auto-generate QR and save path to DB
        generated = generate_qr(emp_id)
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE employees SET qr_code=%s WHERE employee_id=%s", (generated, emp_id))
        db.commit(); cursor.close(); db.close()
        qr_path = generated
    return send_file(os.path.abspath(qr_path), as_attachment=True,
                     download_name=f"QR_{emp_id}.png", mimetype="image/png")

@employee_portal_bp.route("/my_id_card")
@employee_required
def my_id_card():
    from PIL import Image, ImageDraw, ImageFont
    import io as _io2
    from flask import send_file

    emp_id = session["employee_id"]
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

    # ── Colours ──────────────────────────────────────────
    DARK   = (15,  40, 100)
    BLUE   = (30,  58, 138)
    MID    = (37,  99, 235)
    LIGHT  = (59, 130, 246)
    PALE   = (219, 234, 254)
    WHITE  = (255, 255, 255)
    LGRAY  = (241, 245, 249)
    MGRAY  = (100, 116, 139)
    DGRAY  = (15,  23,  42)
    GOLD   = (251, 191,  36)
    RED    = (220,  38,  38)

    # ── Font loader ──────────────────────────────────────
    def fnt(size, bold=False):
        candidates = (
            ["C:/Windows/Fonts/arialbd.ttf",
             "C:/Windows/Fonts/calibrib.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/System/Library/Fonts/Helvetica.ttc",
             "/Library/Fonts/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if bold else
            ["C:/Windows/Fonts/arial.ttf",
             "C:/Windows/Fonts/calibri.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/System/Library/Fonts/Helvetica.ttc",
             "/Library/Fonts/Arial.ttf",
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
        bb = draw.textbbox((0,0), _safe_text(text), font=font)
        return bb[2]-bb[0]

    def cx(draw, text, font, card_w, y, color):
        t = _safe_text(text)
        draw.text(((card_w - tw(draw, t, font))//2, y), t, font=font, fill=color)

    # ── Vertical card size (portrait) ────────────────────
    CW, CH = 500, 820

    # ════════════════════════════════════════════════════
    #  FRONT
    # ════════════════════════════════════════════════════
    front = Image.new("RGB", (CW, CH), WHITE)
    fd    = ImageDraw.Draw(front)

    # -- Top header --
    fd.rectangle([(0, 0), (CW, 110)], fill=BLUE)
    # Decorative circle top-right
    fd.ellipse([(CW-100, -60), (CW+60, 100)], fill=MID)
    cx(fd, "EMPLOYEE ID CARD", fnt(18, bold=True), CW, 18, WHITE)
    cx(fd, "Attendance Management System", fnt(11), CW, 52, PALE)
    # Thin gold accent line
    fd.rectangle([(0, 108), (CW, 113)], fill=GOLD)

    # -- Photo section --
    fd.rectangle([(0, 113), (CW, 370)], fill=LGRAY)
    PH_W  = 160
    PH_H  = 190
    PH_CX = CW // 2
    PH_X  = PH_CX - PH_W // 2
    PH_Y  = 128
    # Gold border box
    fd.rounded_rectangle([(PH_X-5, PH_Y-5), (PH_X+PH_W+5, PH_Y+PH_H+5)],
                         radius=8, fill=GOLD)
    # White inner border
    fd.rounded_rectangle([(PH_X-2, PH_Y-2), (PH_X+PH_W+2, PH_Y+PH_H+2)],
                         radius=6, fill=WHITE)
    # Photo
    photo_path = os.path.join("dataset", emp_id + ".jpg")
    try:
        ph = Image.open(photo_path).convert("RGB").resize((PH_W, PH_H), Image.LANCZOS)
        front.paste(ph, (PH_X, PH_Y))
    except Exception:
        fd.rounded_rectangle([(PH_X, PH_Y), (PH_X+PH_W, PH_Y+PH_H)], radius=4, fill=MID)
        ini = row[1][0].upper() if row and row[1] else "?"
        cx(fd, ini, fnt(56, bold=True), CW, PH_Y + PH_H//2 - 38, WHITE)

    # Name & role
    name_str = (row[1] or "Unknown")[:24]
    role_str  = (row[2] or "Employee")[:28]
    cx(fd, name_str,  fnt(18, bold=True), CW, 328, DGRAY)
    cx(fd, role_str,  fnt(12),            CW, 352, MGRAY)

    # Blue separator
    fd.rectangle([(40, 372), (CW-40, 374)], fill=PALE)

    # -- Info rows (centered) --
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
        cx(fd, lbl,            fnt(10),            CW, y+2,  MGRAY)
        cx(fd, str(val)[:34],  fnt(13, bold=True), CW, y+17, DGRAY)
        y += 44

    # Blood group badge (prominent red pill)
    bg_val = row[7] if row and row[7] else None
    if bg_val:
        bw = tw(fd, bg_val, fnt(13, bold=True)) + 28
        bx = (CW - bw) // 2
        by = y + 8
        fd.rounded_rectangle([(bx, by), (bx+bw, by+32)], radius=16, fill=RED)
        cx(fd, bg_val, fnt(13, bold=True), CW, by+8, WHITE)

    # -- Footer --
    fd.rectangle([(0, CH-60), (CW, CH)], fill=BLUE)
    fd.rectangle([(0, CH-62), (CW, CH-60)], fill=GOLD)
    cx(fd, "Confidential  |  Not Transferable", fnt(10), CW, CH-44, PALE)
    cx(fd, "Property of the Organization",       fnt(10), CW, CH-26, (160,185,240))

    # ════════════════════════════════════════════════════
    #  BACK
    # ════════════════════════════════════════════════════
    back = Image.new("RGB", (CW, CH), LGRAY)
    bd   = ImageDraw.Draw(back)

    # Top header (same style)
    bd.rectangle([(0, 0), (CW, 110)], fill=BLUE)
    bd.ellipse([(CW-100, -60), (CW+60, 100)], fill=MID)
    cx(bd, "ATTENDANCE MANAGEMENT SYSTEM", fnt(14, bold=True), CW, 22, WHITE)
    cx(bd, "Employee Attendance Card", fnt(11), CW, 52, PALE)
    bd.rectangle([(0, 108), (CW, 113)], fill=GOLD)

    # QR code — large and centered
    qr_path = os.path.join("static", "qrcodes", emp_id + ".png")
    if not os.path.exists(qr_path):
        qr_path = generate_qr(emp_id)

    QS   = 240
    qr_x = (CW - QS) // 2
    qr_y = 148
    # White card behind QR
    bd.rounded_rectangle([(qr_x-16, qr_y-16), (qr_x+QS+16, qr_y+QS+16)],
                         radius=14, fill=WHITE)
    try:
        qr_img = Image.open(qr_path).convert("RGB").resize((QS, QS), Image.LANCZOS)
        back.paste(qr_img, (qr_x, qr_y))
    except Exception:
        cx(bd, "QR NOT AVAILABLE", fnt(13), CW, qr_y+QS//2, MGRAY)

    cx(bd, "Scan to Mark Attendance",      fnt(14, bold=True), CW, qr_y+QS+28, BLUE)
    cx(bd, row[0] if row else "",          fnt(12),            CW, qr_y+QS+52, MGRAY)

    # Divider
    bd.rectangle([(40, qr_y+QS+78), (CW-40, qr_y+QS+80)], fill=(203,213,225))

    # Info below QR
    sub_info = [
        ("Name",         (row[1] or "-")[:26] if row else "-"),
        ("Designation",  (row[2] or "-")[:26] if row else "-"),
        ("Blood Group",  (row[7] or "-")      if row else "-"),
    ]
    BP = 36
    sy = qr_y + QS + 94
    for lbl2, val2 in sub_info:
        cx(bd, lbl2, fnt(10),            CW, sy,    MGRAY)
        cx(bd, val2, fnt(12, bold=True), CW, sy+14, DGRAY)
        sy += 42

    # "If found" note
    bd.rectangle([(BP, sy+8), (CW-BP, sy+10)], fill=(203,213,225))
    cx(bd, "If found, please return to:", fnt(10),            CW, sy+18, MGRAY)
    cx(bd, "HR Department",               fnt(12, bold=True), CW, sy+34, BLUE)
    if row and row[3]:
        cx(bd, row[3][:34], fnt(10), CW, sy+54, MGRAY)

    # Magnetic stripe
    bd.rectangle([(0, CH-100), (CW, CH-68)], fill=DARK)

    # Footer
    bd.rectangle([(0, CH-60), (CW, CH)], fill=BLUE)
    bd.rectangle([(0, CH-62), (CW, CH-60)], fill=GOLD)
    cx(bd, "Authorized Personnel Only  |  Not Transferable", fnt(10), CW, CH-44, PALE)
    cx(bd, "Misuse is subject to disciplinary action",        fnt(10), CW, CH-26, (160,185,240))

    # ════════════════════════════════════════════════════
    #  COMBINE side by side  (front | gap | back)
    # ════════════════════════════════════════════════════
    GAP   = 40
    LBL_H = 24
    BGCOL = (215, 225, 240)
    total = Image.new("RGB", (CW*2 + GAP, CH + LBL_H), BGCOL)
    td    = ImageDraw.Draw(total)

    td.text((10,  4), "FRONT", font=fnt(13, bold=True), fill=BLUE)
    td.text((CW + GAP + 10, 4), "BACK", font=fnt(13, bold=True), fill=BLUE)

    total.paste(front, (0,       LBL_H))
    total.paste(back,  (CW+GAP,  LBL_H))

    buf = _io2.BytesIO()
    total.save(buf, format="PNG", dpi=(200, 200))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"IDCard_{emp_id}.png", mimetype="image/png")

@employee_portal_bp.route("/employee_portal")
@employee_required
def employee_portal():
    emp_id = session["employee_id"]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, e.email, e.face_image,
               e.date_of_joining,
               COALESCE(sc.salary_per_day, 0) AS salary_per_day,
               sh.name AS shift_name, sh.start_time AS shift_start, sh.end_time AS shift_end,
               e.phone, e.gender, e.dob, e.blood_group,
               e.address, e.city, e.state, e.pincode,
               e.emergency_contact_name, e.emergency_contact_phone, e.emergency_contact_relation,
               e.aadhar_number, e.pan_number, e.bank_name, e.bank_account, e.bank_ifsc, e.uan_number,
               e.qr_code, e.work_mode, e.about_me, e.manager_name, e.department,
               e.fingerprint_credential_id
        FROM employees e
        LEFT JOIN salary_config sc ON e.employee_id = sc.employee_id
        LEFT JOIN shifts sh ON e.shift_id = sh.id
        WHERE e.employee_id = %s
    """, (emp_id,))
    emp = list(cursor.fetchone())
    # emp indices:
    # [0]=id [1]=name [2]=role [3]=email [4]=face_image [5]=date_of_joining
    # [6]=salary_per_day [7]=shift_name [8]=shift_start [9]=shift_end
    # [10]=phone [11]=gender [12]=dob [13]=blood_group
    # [14]=address [15]=city [16]=state [17]=pincode
    # [18]=emergency_contact_name [19]=emergency_contact_phone [20]=emergency_contact_relation
    # [21]=aadhar_number [22]=pan_number [23]=bank_name [24]=bank_account [25]=bank_ifsc [26]=uan_number
    # [27]=qr_code [28]=work_mode [29]=about_me [30]=manager_name [31]=department
    # [32]=fingerprint_credential_id
    fp_enrolled = bool(emp[32]) if len(emp) > 32 else False
    # Decrypt PII fields
    for _pii_idx in (21, 22, 24, 25, 26):
        if _pii_idx < len(emp):
            emp[_pii_idx] = decrypt_pii(emp[_pii_idx])

    today = datetime.date.today()
    cursor.execute(
        "SELECT login_time, logout_time, status, logout_status, attendance_type "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    today_att = cursor.fetchone()

    year  = int(request.args.get("year",  today.year))
    month = int(request.args.get("month", today.month))
    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance
        WHERE employee_id=%s AND date BETWEEN %s AND %s
        ORDER BY date DESC
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    monthly_att = cursor.fetchall()

    holidays_set  = fetch_holidays_set(year, month)
    # Fetch holiday names for attendance calendar tooltips
    cursor.execute(
        "SELECT date, name FROM holidays WHERE date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, calendar.monthrange(year, month)[1]))
    )
    att_hol_name_map = {row[0]: row[1] for row in cursor.fetchall()}
    billable_past = get_billable_past_days(year, month)
    att_by_date   = {r[0]: r for r in monthly_att}
    full_days = half_days = late_days = absent_days = 0
    total_seconds = 0
    for d in billable_past:
        row = att_by_date.get(d)
        if row:
            _, login_t, logout_t, status, _ls, att_type = row
            final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
            if   final in ("Full Day", "Approved Leave"): full_days   += 1
            elif final == "Late - Full Day":             late_days   += 1
            elif final in ("Half Day", "Present"):       half_days   += 1
            else:                                        absent_days += 1
            if login_t and logout_t:
                li = login_t.total_seconds()  if hasattr(login_t,  "total_seconds") else (login_t.hour*3600  + login_t.minute*60  + login_t.second)
                lo = logout_t.total_seconds() if hasattr(logout_t, "total_seconds") else (logout_t.hour*3600 + logout_t.minute*60 + logout_t.second)
                if lo > li:
                    total_seconds += int(lo - li)
        else:
            absent_days += 1

    total_hours_str = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    billable_count  = len(billable_past)
    present_equiv   = full_days + late_days + half_days * 0.5
    att_pct         = round(present_equiv / billable_count * 100, 1) if billable_count else 0

    # Calendar data for JS rendering
    cal_data = {}
    _, month_days = calendar.monthrange(year, month)
    for day in range(1, month_days + 1):
        d = datetime.date(year, month, day)
        if d in holidays_set:
            cal_data[day] = "holiday"
        elif d.weekday() == 6:
            cal_data[day] = "weekend"
        elif d > today:
            cal_data[day] = "future"
        else:
            row = att_by_date.get(d)
            if row:
                _, login_t, logout_t, status, _ls, att_type = row
                final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
                if   final == "Full Day":               cal_data[day] = "full"
                elif final == "Late - Full Day":        cal_data[day] = "late"
                elif final in ("Half Day", "Present"):  cal_data[day] = "half"
                else:                                   cal_data[day] = "absent"
            else:
                cal_data[day] = "absent"
    cal_hol_names = {d.day: n for d, n in att_hol_name_map.items()}
    cal_year      = year
    cal_month     = month
    cal_first_dow = datetime.date(year, month, 1).weekday()  # 0=Mon

    cursor.execute("""
        SELECT lr.leave_date, lr.reason, lr.status, lr.created_at,
               COALESCE(lt.name, '') AS leave_type_name, lr.id
        FROM leave_requests lr
        LEFT JOIN leave_types lt ON lr.leave_type_id = lt.id
        WHERE lr.employee_id=%s
        ORDER BY lr.created_at DESC LIMIT 20
    """, (emp_id,))
    my_leaves = cursor.fetchall()

    cursor.execute("""
        SELECT last_working_day, reason, status, created_at
        FROM resignation_requests WHERE employee_id=%s
        ORDER BY created_at DESC LIMIT 1
    """, (emp_id,))
    my_resignation = cursor.fetchone()

    cursor.execute("""
        SELECT id, category, subject, priority, status, admin_response, created_at
        FROM tickets WHERE employee_id=%s
        ORDER BY created_at DESC LIMIT 20
    """, (emp_id,))
    my_tickets = cursor.fetchall()

    # Leave types & per-type balances
    try:
        cursor.execute(
            "SELECT id, name, annual_quota, is_paid FROM leave_types WHERE is_active=1 ORDER BY id"
        )
        leave_types_list = cursor.fetchall()
        # Ensure balances exist for this employee
        assign_leave_balances_for_employee(cursor, emp_id, today.year)
        # Fetch from leave_balances table
        cursor.execute("""
            SELECT lt.id, lt.name, lt.annual_quota, lt.is_paid,
                   COALESCE(lb.total_days, lt.annual_quota) as total,
                   COALESCE(lb.used_days, 0) as used
            FROM leave_types lt
            LEFT JOIN leave_balances lb ON lb.employee_id=%s
                AND lb.leave_type_id=lt.id AND lb.year=%s
            WHERE lt.is_active=1 ORDER BY lt.id
        """, (emp_id, today.year))
        leave_type_balances = []
        annual_leave_quota = 0
        leaves_used = 0
        for lt_id, lt_name, lt_quota, lt_paid, total, used in cursor.fetchall():
            used = float(used or 0)
            total = int(total or lt_quota)
            remaining = max(0, total - used)
            leave_type_balances.append({
                "id": lt_id, "name": lt_name, "quota": total,
                "used": used, "balance": remaining, "is_paid": lt_paid
            })
            annual_leave_quota += total
            leaves_used += used
        leave_balance = max(0, annual_leave_quota - leaves_used)
    except Exception:
        leave_type_balances = []
        annual_leave_quota  = 12
        cursor.execute("""
            SELECT COUNT(*) FROM leave_requests
            WHERE employee_id=%s AND EXTRACT(YEAR FROM leave_date)=%s AND status IN ('Approved','Pending')
        """, (emp_id, today.year))
        leaves_used   = cursor.fetchone()[0] or 0
        leave_balance = max(0, annual_leave_quota - leaves_used)

    # Announcements for dashboard (public + private addressed to this employee)
    cursor.execute("""
        SELECT id, title, content, priority, created_at
        FROM announcements
        WHERE COALESCE(visibility,'public') = 'public'
           OR (visibility = 'private' AND target_employee_id = %s)
        ORDER BY created_at DESC LIMIT 10
    """, (emp_id,))
    announcements = cursor.fetchall()

    # Pending leave count for nav badge
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE employee_id=%s AND status='Pending'", (emp_id,))
    pending_leaves_count = cursor.fetchone()[0] or 0

    # Open ticket count for nav badge
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE employee_id=%s AND status='Open'", (emp_id,))
    open_tickets_count = cursor.fetchone()[0] or 0

    # Unread notification count for bell icon
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE recipient_type='employee' AND employee_id=%s AND is_read=FALSE",
            (emp_id,)
        )
        unread_notifications_web = cursor.fetchone()[0] or 0
    except Exception:
        unread_notifications_web = 0

    # Upcoming holidays (next 3 from today) for dashboard widget
    cursor.execute("""
        SELECT date, name FROM holidays WHERE date >= %s ORDER BY date LIMIT 3
    """, (today,))
    upcoming_holidays = cursor.fetchall()

    # Upcoming holidays for leave planning panel (rest of year, up to 15)
    cursor.execute("""
        SELECT date, name FROM holidays
        WHERE date >= %s AND EXTRACT(YEAR FROM date) = %s
        ORDER BY date LIMIT 15
    """, (today, today.year))
    leave_holidays = cursor.fetchall()

    # Holiday calendar data for employee view
    hol_year = int(request.args.get("hol_year", today.year))
    cursor.execute("SELECT id, date, name FROM holidays WHERE EXTRACT(YEAR FROM date)=%s ORDER BY date", (hol_year,))
    hol_rows = cursor.fetchall()
    hol_map = {}
    for row in hol_rows:
        date_val = row[1]
        if isinstance(date_val, datetime.date):
            hol_map[date_val] = (row[0], row[2])
    sun_cal_obj = calendar.Calendar(firstweekday=6)
    emp_hol_cal = []
    for _m in range(1, 13):
        m_hols = {}
        for _d, (_hid, _hname) in hol_map.items():
            if _d.month == _m:
                m_hols[_d.day] = (_hid, _hname)
        emp_hol_cal.append({
            'month_num':  _m,
            'month_name': calendar.month_name[_m],
            'weeks':      sun_cal_obj.monthdayscalendar(hol_year, _m),
            'holidays':   m_hols,
        })

    # Employee's own incentive history
    try:
        cursor.execute("""
            SELECT ig.title, ig.description, ei.month, ei.year, ei.amount, ei.notes, ei.awarded_at
            FROM employee_incentives ei
            JOIN incentive_goals ig ON ei.goal_id = ig.id
            WHERE ei.employee_id = %s
            ORDER BY ei.year DESC, ei.month DESC, ei.awarded_at DESC
        """, (emp_id,))
        my_incentives = cursor.fetchall()
        cursor.execute(
            "SELECT COALESCE(SUM(amount),0) FROM employee_incentives WHERE employee_id=%s AND year=%s",
            (emp_id, today.year)
        )
        total_incentive_year = float(cursor.fetchone()[0])
    except Exception:
        my_incentives = []
        total_incentive_year = 0.0

    # Employee work experience & education
    try:
        cursor.execute(
            "SELECT id, company, designation, from_year, to_year, is_current, description "
            "FROM employee_experience WHERE employee_id=%s ORDER BY is_current DESC, from_year DESC",
            (emp_id,)
        )
        my_experience = [
            {"id": r[0], "company": r[1], "designation": r[2], "from_year": r[3],
             "to_year": r[4], "is_current": r[5], "description": r[6]}
            for r in cursor.fetchall()
        ]
    except Exception:
        my_experience = []

    try:
        cursor.execute(
            "SELECT id, degree, institution, year_of_passing, percentage "
            "FROM employee_education WHERE employee_id=%s ORDER BY year_of_passing DESC",
            (emp_id,)
        )
        my_education = [
            {"id": r[0], "degree": r[1], "institution": r[2], "year_of_passing": r[3], "percentage": r[4]}
            for r in cursor.fetchall()
        ]
    except Exception:
        my_education = []

    try:
        cursor.execute(
            "SELECT id, doc_type, original_name, uploaded_by, uploaded_at FROM employee_documents WHERE employee_id=%s ORDER BY uploaded_at DESC",
            (emp_id,)
        )
        my_docs = cursor.fetchall()
    except Exception:
        my_docs = []

    try:
        cursor.execute(
            "SELECT date, shift_end, actual_logout, ot_minutes, ot_pay, status FROM overtime_records WHERE employee_id=%s AND EXTRACT(YEAR FROM date)=%s ORDER BY date DESC LIMIT 20",
            (emp_id, today.year)
        )
        my_overtime = cursor.fetchall()
    except Exception:
        my_overtime = []

    # Salary summary for Earnings tab
    salary_per_day = float(emp[6]) if emp[6] else 0.0
    gross_this_month = (full_days + late_days) * salary_per_day + half_days * salary_per_day * 0.5
    deduction_this_month = absent_days * salary_per_day + half_days * salary_per_day * 0.5
    try:
        cursor.execute(
            "SELECT COALESCE(SUM(amount),0) FROM employee_incentives WHERE employee_id=%s AND month=%s AND year=%s",
            (emp_id, today.month, today.year)
        )
        incentives_this_month = float(cursor.fetchone()[0])
    except Exception:
        incentives_this_month = 0.0
    try:
        cursor.execute(
            "SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s AND status='Approved'",
            (emp_id, today.month, today.year)
        )
        ot_pay_this_month = float(cursor.fetchone()[0] or 0)
    except Exception:
        ot_pay_this_month = 0.0
    net_this_month = gross_this_month + incentives_this_month + ot_pay_this_month

    # Comp-off balance
    try:
        cursor.execute("SELECT COALESCE(compoff_minutes_per_day,480) FROM company_settings LIMIT 1")
        mpd_row = cursor.fetchone()
        compoff_mpd = int(mpd_row[0]) if mpd_row else 480
        cursor.execute("SELECT COALESCE(earned_minutes,0), COALESCE(used_minutes,0) FROM compoff_balance WHERE employee_id=%s", (emp_id,))
        co_row = cursor.fetchone() or (0, 0)
        compoff_earned_days = round(co_row[0] / compoff_mpd, 1) if compoff_mpd else 0
        compoff_avail_days  = round(max(0, co_row[0] - co_row[1]) / compoff_mpd, 1) if compoff_mpd else 0
    except Exception:
        compoff_earned_days = 0
        compoff_avail_days  = 0

    # Last 3 months payslip summaries
    recent_payslips = []
    py2, pm2 = today.year, today.month
    for _ in range(3):
        pm2 -= 1
        if pm2 == 0:
            pm2 = 12; py2 -= 1
        _, ld = calendar.monthrange(py2, pm2)
        cursor.execute("""
            SELECT date, login_time, logout_time, status, logout_status, attendance_type
            FROM attendance WHERE employee_id=%s AND date BETWEEN %s AND %s
        """, (emp_id, datetime.date(py2, pm2, 1), datetime.date(py2, pm2, ld)))
        p_att = cursor.fetchall()
        p_billable = get_billable_past_days(py2, pm2)
        p_att_map  = {r[0]: r for r in p_att}
        p_full = p_late = p_half = p_absent = 0
        for d in p_billable:
            row = p_att_map.get(d)
            if row:
                _, lt, lot, st, _ls, at = row
                final = at if at else infer_type_legacy(st, lt, lot)
                if   final in ("Full Day", "Approved Leave"): p_full   += 1
                elif final == "Late - Full Day":              p_late   += 1
                elif final in ("Half Day", "Present"):        p_half   += 1
                else:                                         p_absent += 1
            else:
                p_absent += 1
        p_gross = (p_full + p_late) * salary_per_day + p_half * salary_per_day * 0.5
        try:
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM employee_incentives WHERE employee_id=%s AND month=%s AND year=%s", (emp_id, pm2, py2))
            p_inc = float(cursor.fetchone()[0])
        except Exception:
            p_inc = 0.0
        try:
            cursor.execute("SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s AND status='Approved'", (emp_id, pm2, py2))
            p_ot = float(cursor.fetchone()[0] or 0)
        except Exception:
            p_ot = 0.0
        recent_payslips.append({
            'month': calendar.month_name[pm2], 'year': py2,
            'gross': p_gross, 'incentives': p_inc, 'ot_pay': p_ot,
            'net': p_gross + p_inc + p_ot,
            'present': p_full + p_late + p_half, 'absent': p_absent,
        })

    # Shift swap data
    try:
        cursor.execute("""
            SELECT ssr.id, ssr.target_id, et.name, ts.name AS tgt_shift,
                   ssr.reason, ssr.status, ssr.created_at
            FROM shift_swap_requests ssr
            JOIN employees et ON et.employee_id = ssr.target_id
            JOIN shifts ts ON ts.id = ssr.target_shift_id
            WHERE ssr.requester_id=%s ORDER BY ssr.created_at DESC LIMIT 20
        """, (emp_id,))
        my_swap_requests = cursor.fetchall()
        cursor.execute("""
            SELECT ssr.id, ssr.requester_id, er.name, rs.name AS req_shift,
                   ssr.reason, ssr.status, ssr.created_at
            FROM shift_swap_requests ssr
            JOIN employees er ON er.employee_id = ssr.requester_id
            JOIN shifts rs ON rs.id = ssr.requester_shift_id
            WHERE ssr.target_id=%s AND ssr.status='Pending_Target' ORDER BY ssr.created_at DESC
        """, (emp_id,))
        incoming_swap_requests = cursor.fetchall()
        cursor.execute("""
            SELECT e.employee_id, e.name, COALESCE(s.shift_name,''),
                   COALESCE(TO_CHAR(s.start_time,'HH24:MI'),''),
                   COALESCE(TO_CHAR(s.end_time,'HH24:MI'),''),
                   COALESCE(e.department,''), COALESCE(e.designation,'')
            FROM employees e
            LEFT JOIN shifts s ON s.id = e.shift_id
            WHERE e.employee_id != %s AND e.is_active=1
            ORDER BY e.name
        """, (emp_id,))
        swap_eligible_employees = cursor.fetchall()
    except Exception:
        my_swap_requests = []
        incoming_swap_requests = []
        swap_eligible_employees = []

    cursor.close(); db.close()

    # Build last 12 months list for pay slips section
    payslip_months = []
    py, pm = today.year, today.month
    for _ in range(12):
        payslip_months.append((py, pm, calendar.month_name[pm]))
        pm -= 1
        if pm == 0:
            pm = 12; py -= 1

    return render_template("employee_portal.html",
        emp=emp,
        today_date=today,
        today=today.strftime("%d %b %Y"),
        today_long=today.strftime("%A, %d %B %Y"),
        today_att=today_att,
        monthly_att=monthly_att,
        full_days=full_days, late_days=late_days,
        half_days=half_days, absent_days=absent_days,
        billable=billable_count,
        my_leaves=my_leaves,
        my_resignation=my_resignation,
        my_tickets=my_tickets,
        leave_sent=request.args.get("leave_sent") == "1",
        resigned=request.args.get("resigned") == "1",
        ticket_sent=request.args.get("ticket_sent") == "1",
        month_name=datetime.date(year, month, 1).strftime("%B %Y"),
        selected_month=f"{year}-{month:02d}",
        att_pct=att_pct,
        total_hours=total_hours_str,
        cal_data=cal_data,
        cal_hol_names=cal_hol_names,
        cal_year=cal_year,
        cal_month=cal_month,
        cal_first_dow=cal_first_dow,
        sel_year=year,
        sel_month=month,
        years=list(range(today.year - 2, today.year + 1)),
        months=[(i, datetime.date(year, i, 1).strftime("%B")) for i in range(1, 13)],
        payslip_months=payslip_months,
        leave_balance=leave_balance,
        leaves_used=leaves_used,
        annual_leave_quota=annual_leave_quota,
        leave_type_balances=leave_type_balances,
        leave_types_for_form=[{"id": lt[0], "name": lt[1]} for lt in (leave_types_list if leave_types_list else [])],
        announcements=announcements,
        pending_leaves_count=pending_leaves_count,
        open_tickets_count=open_tickets_count,
        unread_notifications_web=unread_notifications_web,
        upcoming_holidays=upcoming_holidays,
        leave_holidays=leave_holidays,
        hol_year=hol_year,
        emp_hol_cal=emp_hol_cal,
        all_holidays_list=hol_rows,
        my_incentives=my_incentives,
        total_incentive_year=total_incentive_year,
        my_experience=my_experience,
        my_education=my_education,
        my_docs=my_docs,
        my_overtime=my_overtime,
        compoff_avail_days=compoff_avail_days,
        compoff_earned_days=compoff_earned_days,
        salary_per_day=salary_per_day,
        gross_this_month=gross_this_month,
        deduction_this_month=deduction_this_month,
        incentives_this_month=incentives_this_month,
        ot_pay_this_month=ot_pay_this_month,
        net_this_month=net_this_month,
        recent_payslips=recent_payslips,
        my_swap_requests=my_swap_requests,
        incoming_swap_requests=incoming_swap_requests,
        swap_eligible_employees=swap_eligible_employees,
        swap_sent=request.args.get("swap_sent") == "1",
        swap_responded=request.args.get("swap_responded") == "1",
        swap_error=request.args.get("swap_error", ""),
        fp_enrolled=fp_enrolled,
        fp_enabled=get_auth_config().get("fingerprint_enabled", False),
    )

@employee_portal_bp.route("/api/employee/change-password", methods=["POST"])
@employee_api_required
def api_employee_change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "").strip()
    new_password     = data.get("new_password", "").strip()
    if not current_password or not new_password:
        return jsonify({"ok": False, "msg": "current_password and new_password required"}), 400
    if len(new_password) < 8:
        return jsonify({"ok": False, "msg": "New password must be at least 8 characters"}), 400
    from flask import g as _g
    emp_id = _g.api_emp_id
    with _db() as (cursor, conn):
        cursor.execute("SELECT password FROM employees WHERE employee_id=%s", (emp_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Employee not found"}), 404
        if not row[0] or not check_password_hash(row[0], current_password):
            return jsonify({"ok": False, "msg": "Current password is incorrect"}), 401
        cursor.execute(
            "UPDATE employees SET password=%s WHERE employee_id=%s",
            (generate_password_hash(new_password), emp_id)
        )
        conn.commit()
    return jsonify({"ok": True, "msg": "Password changed successfully"})

@employee_portal_bp.route("/api/employee/portal", methods=["GET"])
@employee_api_required
def api_employee_portal():
    from flask import g as _g
    emp_id = _g.api_emp_id
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()

    cursor.execute("""
        SELECT e.name, e.email, COALESCE(c.name, '') AS company_name
        FROM employees e
        LEFT JOIN companies c ON e.company_id = c.id
        WHERE e.employee_id=%s
    """, (emp_id,))
    emp = cursor.fetchone()

    cursor.execute(
        "SELECT login_time, logout_time, status, logout_status, attendance_type "
        "FROM attendance WHERE employee_id=%s AND date=%s", (emp_id, today)
    )
    att = cursor.fetchone()

    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance WHERE employee_id=%s AND date >= %s
        ORDER BY date DESC LIMIT 10
    """, (emp_id, today - datetime.timedelta(days=30)))
    recent = cursor.fetchall()

    cursor.execute(
        "SELECT leave_date, reason, status, created_at FROM leave_requests "
        "WHERE employee_id=%s ORDER BY created_at DESC LIMIT 5", (emp_id,)
    )
    leaves = cursor.fetchall()

    cursor.execute(
        "SELECT last_working_day, reason, status, created_at FROM resignation_requests "
        "WHERE employee_id=%s ORDER BY created_at DESC LIMIT 1", (emp_id,)
    )
    resign = cursor.fetchone()
    cursor.execute(
        "SELECT COUNT(*) FROM notifications WHERE recipient_type='employee' AND employee_id=%s AND is_read=FALSE",
        (emp_id,)
    )
    unread_notifications = cursor.fetchone()[0]
    cursor.execute("""
        SELECT title, content, priority, created_at FROM announcements
        WHERE COALESCE(visibility,'public') = 'public'
           OR (visibility = 'private' AND target_employee_id = %s)
        ORDER BY created_at DESC LIMIT 5
    """, (emp_id,))
    ann_rows = cursor.fetchall()
    cursor.execute("SELECT role, department FROM employees WHERE employee_id=%s", (emp_id,))
    emp_extra = cursor.fetchone()
    cursor.close(); db.close()

    return jsonify({
        "ok": True,
        "employee_id": emp_id,
        "name": emp[0] if emp else emp_id,
        "email": emp[1] if emp else None,
        "company_name": emp[2] if emp else "",
        "today": today.strftime("%d %b %Y"),
        "today_attendance": {
            "login_time": _fmt_t(att[0]),
            "logout_time": _fmt_t(att[1]),
            "login_status": att[2],
            "logout_status": att[3],
            "attendance_type": att[4],
        } if att else None,
        "recent_attendance": [
            {"date": str(r[0]), "login_time": _fmt_t(r[1]), "logout_time": _fmt_t(r[2]),
             "login_status": r[3], "logout_status": r[4], "attendance_type": r[5]}
            for r in recent
        ],
        "recent_leaves": [
            {"leave_date": str(r[0]), "reason": r[1], "status": r[2],
             "requested_at": str(r[3])}
            for r in leaves
        ],
        "resignation": {
            "last_working_day": str(resign[0]),
            "reason": resign[1],
            "status": resign[2],
            "created_at": str(resign[3]),
        } if resign else None,
        "unread_notifications": unread_notifications,
        "role": emp_extra[0] if emp_extra else None,
        "department": emp_extra[1] if emp_extra else None,
        "announcements": [
            {"title": r[0], "content": r[1], "priority": r[2], "created_at": str(r[3])}
            for r in ann_rows
        ],
    })

@employee_portal_bp.route("/api/employee/checkin", methods=["POST"])
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
            if not is_within_range(lat_f, lon_f, cfg.OFFICE_LAT, cfg.OFFICE_LON):
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
        grace_time = (datetime.datetime.combine(today, cfg.SHIFT_START) + datetime.timedelta(minutes=cfg.GRACE_MINUTES)).time()
        if current_time <= grace_time:
            status = "Full Day Login"
        elif current_time <= cfg.SHIFT_HALF:
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
        if current_time < cfg.SHIFT_HALF:
            out_status = "Half Day Logout"
        elif current_time < cfg.SHIFT_END:
            out_status = "Early Logout"
        else:
            out_status = "Completed"
        att_type = classify_by_worked_minutes(login_status, total_m, cfg.SHIFT_START, cfg.SHIFT_END)
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

@employee_portal_bp.route("/api/employee/sync_punches", methods=["POST"])
@employee_api_required
def api_employee_sync_punches():
    """Batch-submit offline punches queued on the device when there was no connectivity."""
    from flask import g as _g
    emp_id  = _g.api_emp_id
    payload = request.get_json() or {}
    punches = payload.get("punches", [])
    if not punches:
        return jsonify({"ok": True, "results": []})

    db2  = get_db_connection()
    cur2 = db2.cursor(buffered=True)
    cur2.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
    if not cur2.fetchone():
        cur2.close(); db2.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404

    results = []
    for punch in punches:
        punched_at_str = punch.get("punched_at", "")
        lat = punch.get("lat")
        lon = punch.get("lon")
        try:
            _pt = datetime.datetime.fromisoformat(punched_at_str.replace("Z", "+00:00"))
            _pt = _pt.replace(tzinfo=None)
            _now = datetime.datetime.now()
            age = (_now - _pt).total_seconds()
            if age > 86400:
                results.append({"id": punch.get("id"), "ok": False, "msg": "Too old (>24 h)"})
                continue
            if _pt > _now + datetime.timedelta(minutes=5):
                results.append({"id": punch.get("id"), "ok": False, "msg": "Future timestamp rejected"})
                continue
        except (ValueError, TypeError):
            results.append({"id": punch.get("id"), "ok": False, "msg": "Invalid timestamp"})
            continue

        punch_date = _pt.date()
        punch_time = _pt.time()
        cur2.execute(
            "SELECT login_time, logout_time, status, worked_minutes, last_relogin "
            "FROM attendance WHERE employee_id=%s AND date=%s",
            (emp_id, punch_date)
        )
        rec = cur2.fetchone()
        login_time = rec[0] if rec else None
        logout_time = rec[1] if rec else None
        login_status = rec[2] if rec else None
        worked_mins = (rec[3] or 0) if rec else 0
        last_relogin = rec[4] if rec else None

        if not login_time:
            grace_time = (datetime.datetime.combine(punch_date, cfg.SHIFT_START) + datetime.timedelta(minutes=cfg.GRACE_MINUTES)).time()
            if punch_time <= grace_time:
                status = "Full Day Login"
            elif punch_time <= cfg.SHIFT_HALF:
                status = "Late Login"
            else:
                status = "Half Day Login"
            cur2.execute(
                "INSERT INTO attendance (employee_id, date, login_time, status) VALUES (%s,%s,%s,%s)",
                (emp_id, punch_date, punch_time, status)
            )
            db2.commit()
            results.append({"id": punch.get("id"), "ok": True, "action": "login", "status": status})
        elif not logout_time:
            session_start = last_relogin if last_relogin else login_time
            if not isinstance(session_start, datetime.time):
                session_start = _td_to_time(session_start)
            cur_dt    = datetime.datetime.combine(punch_date, punch_time)
            start_dt  = datetime.datetime.combine(punch_date, session_start)
            session_m = max(0, int((cur_dt - start_dt).total_seconds() / 60))
            total_m   = worked_mins + session_m
            if punch_time < cfg.SHIFT_HALF:
                out_status = "Half Day Logout"
            elif punch_time < cfg.SHIFT_END:
                out_status = "Early Logout"
            else:
                out_status = "Completed"
            att_type = classify_by_worked_minutes(login_status, total_m, cfg.SHIFT_START, cfg.SHIFT_END)
            cur2.execute(
                "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s, worked_minutes=%s "
                "WHERE employee_id=%s AND date=%s",
                (punch_time, out_status, att_type, total_m, emp_id, punch_date)
            )
            db2.commit()
            results.append({"id": punch.get("id"), "ok": True, "action": "logout", "status": out_status})
        else:
            results.append({"id": punch.get("id"), "ok": False, "msg": "Duplicate — day already complete"})

    cur2.close(); db2.close()
    _audit("sync_punches", "attendance", emp_id, f"Synced {len([r for r in results if r['ok']])} offline punches")
    return jsonify({"ok": True, "results": results})

@employee_portal_bp.route("/api/employee/auth-config", methods=["GET"])
def api_employee_auth_config():
    """Return all authentication method flags (public, no token required)."""
    return jsonify({"ok": True, **get_auth_config()})

@employee_portal_bp.route("/api/employee/qr-face-checkin", methods=["POST"])
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

    auth_cfg = get_auth_config()

    if auth_combo in ("qr_face", "qr_fingerprint") and not auth_cfg["qr_enabled"]:
        return jsonify({"ok": False, "msg": "QR code authentication is not enabled"}), 403
    if auth_combo in ("qr_face", "face_fingerprint") and not auth_cfg["face_enabled"]:
        return jsonify({"ok": False, "msg": "Face recognition authentication is not enabled"}), 403
    if auth_combo in ("qr_fingerprint", "face_fingerprint"):
        if not auth_cfg["fingerprint_enabled"]:
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
                if not is_within_range(float(lat), float(lon), cfg.OFFICE_LAT, cfg.OFFICE_LON):
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
        grace_time = (datetime.datetime.combine(today, cfg.SHIFT_START) + datetime.timedelta(minutes=cfg.GRACE_MINUTES)).time()
        if current_time <= grace_time:
            status = "Full Day Login"
        elif current_time <= cfg.SHIFT_HALF:
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
        if current_time < cfg.SHIFT_HALF:
            out_status = "Half Day Logout"
        elif current_time < cfg.SHIFT_END:
            out_status = "Early Logout"
        else:
            out_status = "Completed"
        att_type = classify_by_worked_minutes(login_status, total_m, cfg.SHIFT_START, cfg.SHIFT_END)
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

@employee_portal_bp.route("/api/employee/salary", methods=["GET"])
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

@employee_portal_bp.route("/api/employee/attendance", methods=["GET"])
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

@employee_portal_bp.route("/api/employee/profile", methods=["GET"])
@employee_api_required
def api_employee_profile():
    from flask import g as _g
    emp_id = _g.api_emp_id
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, e.role, e.department,
               e.phone, e.dob, e.gender, e.blood_group, e.address, e.city, e.state,
               e.pincode, e.about_me, e.emergency_contact_name, e.emergency_contact_phone,
               e.bank_name, e.bank_account, e.bank_ifsc, e.pan_number, e.aadhar_number,
               COALESCE(s.salary_per_day, 0), COALESCE(e.joining_date, e.date_of_joining),
               COALESCE(c.name, '')
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        LEFT JOIN companies c ON e.company_id = c.id
        WHERE e.employee_id = %s
    """, (emp_id,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    return jsonify({
        "ok": True,
        "profile": {
            "employee_id": row[0], "name": row[1], "email": row[2],
            "role": row[3], "department": row[4],
            "phone": row[5],
            "dob": str(row[6]) if row[6] else None,
            "gender": row[7], "blood_group": row[8],
            "address": row[9], "city": row[10], "state": row[11], "pincode": row[12],
            "about_me": row[13],
            "emergency_contact_name": row[14], "emergency_contact_phone": row[15],
            "bank_name": row[16], "bank_account": decrypt_pii(row[17]), "bank_ifsc": decrypt_pii(row[18]),
            "pan_number": decrypt_pii(row[19]), "aadhar_number": decrypt_pii(row[20]),
            "salary_per_day": float(row[21]),
            "join_date": str(row[22]) if row[22] else None,
            "company_name": row[23],
            "photo_url": f"/dataset/{row[0]}.jpg",
        },
    })

@employee_portal_bp.route("/api/employee/photo", methods=["POST"])
@employee_api_required
def api_employee_upload_photo():
    from flask import g as _g
    from PIL import Image
    emp_id = _g.api_emp_id
    file = request.files.get("photo")
    ok, err = _validate_image_file(file)
    if not ok:
        return jsonify({"ok": False, "msg": err}), 400
    try:
        img = Image.open(file.stream).convert("RGB")
        save_path = os.path.join(UPLOAD_FOLDER, emp_id + ".jpg")
        img.save(save_path, "JPEG", quality=85)
        return jsonify({"ok": True, "msg": "Photo uploaded successfully", "photo_url": f"/dataset/{emp_id}.jpg"})
    except Exception:
        return jsonify({"ok": False, "msg": "Failed to process image"}), 500

