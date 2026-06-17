from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
import cv2
import datetime
import html as _html
import face_recognition
from database import get_db_connection
from qr_generator import generate_qr
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os
import math
import re
import calendar
import mysql.connector
import smtplib
import ssl
import secrets
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import threading
import io as _io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.context_processor
def inject_common_vars():
    return dict(
        shift_start=SHIFT_START.strftime("%I:%M %p"),
        shift_end=SHIFT_END.strftime("%I:%M %p"),
    )

@app.route("/favicon.ico")
def favicon():
    ico = os.path.join(app.static_folder, "favicon.ico")
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/x-icon") if os.path.exists(ico) else ("", 204)

# In-memory API token store  { token: username }
_api_tokens: dict = {}

# Jinja2 filter: handles both datetime.time and datetime.timedelta from MySQL
@app.template_filter("fmt_time")
def fmt_time_filter(value):
    if value is None:
        return "--"
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M:%S")
    # timedelta (MySQL connector returns TIME columns as timedelta)
    total = int(value.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)

# ---------------- CONFIG ----------------
_key_file = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.path.exists(_key_file):
    with open(_key_file) as _f:
        app.secret_key = _f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(_key_file, "w") as _f:
        _f.write(app.secret_key)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = 1800

UPLOAD_FOLDER = "dataset"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- CSRF PROTECTION ----------------
_EMP_ID_RE = re.compile(r'^[A-Za-z0-9_\-]+$')

def _csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(32)
    return session["_csrf"]

app.jinja_env.globals["csrf_token"] = _csrf_token

@app.before_request
def _enforce_csrf():
    pass  # CSRF enforcement disabled — tokens not present in templates

# Office location (single source of truth)
OFFICE_LAT = 17.494664737165042
OFFICE_LON = 78.40496618113566
OFFICE_RADIUS_M = 300   # metres — 300 m radius as per policy

# Shift timings
SHIFT_START = datetime.time(9, 0)    # Full Day Login cutoff
SHIFT_HALF  = datetime.time(13, 0)   # Half Day threshold
SHIFT_END   = datetime.time(18, 0)   # Full Day Logout cutoff

# Deduction rates
LATE_DEDUCTION_RATE = 0.10   # 10% deduction for late login
HALF_DAY_RATE       = 0.50   # 50% deduction for half day

# ---------------- DB MIGRATION ----------------
def init_db():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) DEFAULT NULL,
            face_image VARCHAR(255),
            qr_code VARCHAR(255)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            login_time TIME DEFAULT NULL,
            logout_time TIME DEFAULT NULL,
            status VARCHAR(50) DEFAULT NULL,
            logout_status VARCHAR(50) DEFAULT NULL,
            attendance_type VARCHAR(50) DEFAULT NULL,
            UNIQUE KEY uq_emp_date (employee_id, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salary_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            salary_per_day DECIMAL(10,2) DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(150) DEFAULT NULL,
            reset_token VARCHAR(64) DEFAULT NULL,
            reset_token_expiry DATETIME DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            smtp_host VARCHAR(150) NOT NULL,
            smtp_port INT NOT NULL DEFAULT 587,
            smtp_user VARCHAR(150) NOT NULL,
            smtp_pass VARCHAR(255) NOT NULL,
            from_name VARCHAR(100) DEFAULT 'HR Department',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            leave_date DATE NOT NULL,
            reason VARCHAR(500) NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resignation_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            last_working_day DATE NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            category VARCHAR(100) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            priority VARCHAR(20) DEFAULT 'Medium',
            status VARCHAR(30) DEFAULT 'Open',
            admin_response TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            start_time TIME NOT NULL,
            half_time  TIME NOT NULL,
            end_time   TIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            priority ENUM('Normal','Important','Urgent') DEFAULT 'Normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    # Migrations for existing installs
    for sql in [
        "ALTER TABLE attendance ADD COLUMN logout_status VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE attendance ADD COLUMN attendance_type VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN role VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN password VARCHAR(255) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN shift_id INT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN date_of_joining DATE DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN phone VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN gender VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN dob DATE DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN blood_group VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN address TEXT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN city VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN state VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN pincode VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN emergency_contact_name VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN emergency_contact_phone VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN emergency_contact_relation VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN aadhar_number VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN pan_number VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN bank_name VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN bank_account VARCHAR(30) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN bank_ifsc VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN uan_number VARCHAR(30) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN work_mode VARCHAR(20) DEFAULT 'office'",
        "ALTER TABLE employees ADD COLUMN work_lat DECIMAL(10,8) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN work_lon DECIMAL(11,8) DEFAULT NULL",
        "ALTER TABLE holidays ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST",
        "ALTER TABLE salary_config ADD COLUMN last_revised DATE DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN reset_token VARCHAR(64) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN reset_token_expiry DATETIME DEFAULT NULL",
        "ALTER TABLE email_config ADD COLUMN from_email VARCHAR(150) DEFAULT NULL",
    ]:
        try:
            cursor.execute(sql)
            db.commit()
        except mysql.connector.errors.DatabaseError:
            db.rollback()

    # Back-fill password for existing employees that have none (default = their employee_id)
    cursor.execute("SELECT employee_id FROM employees WHERE password IS NULL")
    for (eid,) in cursor.fetchall():
        cursor.execute(
            "UPDATE employees SET password=%s WHERE employee_id=%s",
            (generate_password_hash(eid), eid)
        )
    db.commit()

    # Force-set admin credentials
    hashed = generate_password_hash("admin@123")
    cursor.execute("DELETE FROM admin_users WHERE username = 'admin'")
    cursor.execute(
        "INSERT INTO admin_users (username, password) VALUES (%s, %s)",
        ("admin", hashed)
    )
    db.commit()
    print("Database ready. Admin -> username: admin  password: admin@123")

    cursor.close()
    db.close()

# ---------------- ADMIN GUARD ----------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Accept", "").startswith("application/json")
                or request.headers.get("Content-Type", "").startswith("application/json")
                or request.is_json
            )
            if is_ajax:
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.", "redirect": url_for("admin_login")}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

def employee_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("employee_id"):
            return redirect("/employee_login")
        return f(*args, **kwargs)
    return wrapper

# ---------------- ATTENDANCE HELPERS ----------------
def _td_to_time(val):
    """Convert MySQL timedelta or datetime.time to datetime.time."""
    if val is None:
        return None
    if isinstance(val, datetime.time):
        return val
    total = int(val.total_seconds())
    h, rem = divmod(total, 3600)
    m, s   = divmod(rem, 60)
    return datetime.time(h % 24, m, s)

def get_employee_shift(emp_id, cursor):
    """Return (shift_start, shift_half, shift_end, shift_name) for employee.
    Falls back to global defaults if no shift assigned."""
    cursor.execute(
        "SELECT s.start_time, s.half_time, s.end_time, s.name "
        "FROM employees e JOIN shifts s ON e.shift_id = s.id "
        "WHERE e.employee_id = %s",
        (emp_id,)
    )
    row = cursor.fetchone()
    if row:
        return _td_to_time(row[0]), _td_to_time(row[1]), _td_to_time(row[2]), row[3]
    return SHIFT_START, SHIFT_HALF, SHIFT_END, "Default"

def get_attendance_type(login_status, logout_status):
    if not login_status:
        return "Absent"
    if not logout_status:
        return "Half Day" if login_status == "Half Day Login" else "Present"
    if login_status == "Half Day Login":
        return "Half Day"
    if logout_status in ("Half Day Logout", "Early Logout"):
        return "Half Day"
    if login_status == "Late Login":
        return "Late - Full Day"
    return "Full Day"

def calculate_deduction(salary_per_day, attendance_type):
    spd = float(salary_per_day)
    if attendance_type in ("Full Day", "Approved Leave"):
        return 0.0
    if attendance_type == "Late - Full Day":
        return round(spd * LATE_DEDUCTION_RATE, 2)
    if attendance_type in ("Half Day", "Present"):
        return round(spd * HALF_DAY_RATE, 2)
    if attendance_type == "Absent":
        return spd
    return 0.0

def infer_type_legacy(status, login_time, logout_time):
    if not login_time:
        return "Absent"
    if not logout_time:
        return "Half Day" if status == "Half Day Login" else "Present"
    if status in ("Half Day Logout", "Early Logout"):
        return "Half Day"
    return "Full Day"

def get_working_days(year, month):
    _, last_day = calendar.monthrange(year, month)
    return [
        datetime.date(year, month, d)
        for d in range(1, last_day + 1)
        if datetime.date(year, month, d).weekday() != 6
    ]

def fetch_holidays_set(year, month):
    _, last_day = calendar.monthrange(year, month)
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT date FROM holidays WHERE date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, last_day))
    )
    holidays = {row[0] for row in cursor.fetchall()}
    cursor.close()
    db.close()
    return holidays

def get_billable_past_days(year, month):
    today = datetime.date.today()
    # Holidays are included — they count as paid working days
    return [d for d in get_working_days(year, month) if d <= today]

def fetch_leave_map(year, month):
    """Return {emp_id: set(leave_dates)} for approved leaves in the given month."""
    _, last_day = calendar.monthrange(year, month)
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT employee_id, leave_date FROM leave_requests "
        "WHERE status = 'Approved' AND leave_date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, last_day))
    )
    leave_map = {}
    for eid, ld in cursor.fetchall():
        leave_map.setdefault(eid, set()).add(ld)
    cursor.close()
    db.close()
    return leave_map

# ---------------- EMAIL HELPERS ----------------
def get_email_config():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email FROM email_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    db.close()
    if row:
        return {
            "host": row[0], "port": row[1], "user": row[2], "password": row[3],
            "from_name": row[4], "from_email": row[5] or row[2]
        }
    # Fall back to .env values so team members don't need to configure via UI
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if smtp_host and smtp_user and smtp_pass:
        return {
            "host": smtp_host,
            "port": int(os.environ.get("SMTP_PORT", 587)),
            "user": smtp_user,
            "password": smtp_pass,
            "from_name": os.environ.get("SMTP_FROM_NAME", "Attendance System"),
            "from_email": os.environ.get("SMTP_FROM_EMAIL", smtp_user),
        }
    return None

def build_salary_slip_html(emp_name, emp_id, emp_email, month_name, year, month, salary_data):
    e = salary_data
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
  .slip {{ max-width: 650px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
  .header {{ background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; color: white; text-align: center; }}
  .header h2 {{ margin: 0 0 6px; font-size: 22px; }}
  .header p {{ margin: 0; opacity: 0.85; font-size: 14px; }}
  .body {{ padding: 28px; }}
  .emp-info {{ background: #f8f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 22px; }}
  .emp-info table {{ width: 100%; border-collapse: collapse; }}
  .emp-info td {{ padding: 5px 8px; font-size: 14px; }}
  .emp-info td:first-child {{ font-weight: 600; color: #555; width: 140px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #444; margin: 20px 0 10px; border-bottom: 2px solid #eee; padding-bottom: 6px; }}
  .att-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }}
  .att-card {{ background: #f8f9fc; border-radius: 8px; padding: 12px; text-align: center; }}
  .att-card .num {{ font-size: 22px; font-weight: 700; }}
  .att-card .lbl {{ font-size: 11px; color: #888; margin-top: 3px; }}
  .green {{ color: #22c55e; }} .yellow {{ color: #f59e0b; }} .red {{ color: #ef4444; }} .blue {{ color: #3b82f6; }}
  .salary-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  .salary-table td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }}
  .salary-table td:last-child {{ text-align: right; font-weight: 600; }}
  .salary-table tr.total {{ background: #f8f9fc; font-weight: 700; font-size: 15px; }}
  .salary-table tr.total td {{ border-top: 2px solid #ddd; border-bottom: 2px solid #ddd; }}
  .net-row td {{ background: linear-gradient(135deg, #667eea15, #764ba215); color: #5b21b6; font-size: 16px; font-weight: 700; }}
  .footer {{ background: #f8f9fc; padding: 18px 28px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
</style>
</head>
<body>
<div class="slip">
  <div class="header">
    <h2>Salary Slip — {month_name}</h2>
    <p>Employee Attendance & Payroll Statement</p>
  </div>
  <div class="body">
    <div class="emp-info">
      <table>
        <tr><td>Employee Name</td><td>{emp_name}</td></tr>
        <tr><td>Employee ID</td><td>{emp_id}</td></tr>
        <tr><td>Email</td><td>{emp_email or 'N/A'}</td></tr>
        <tr><td>Pay Period</td><td>{month_name}</td></tr>
        <tr><td>Working Days</td><td>{e['billable']} days</td></tr>
        <tr><td>Daily Rate</td><td>Rs. {e['spd']:.2f}</td></tr>
      </table>
    </div>

    <div class="section-title">Attendance Summary</div>
    <div class="att-grid">
      <div class="att-card"><div class="num green">{e['full_days']}</div><div class="lbl">Full Days</div></div>
      <div class="att-card"><div class="num yellow">{e['late_days']}</div><div class="lbl">Late Days</div></div>
      <div class="att-card"><div class="num yellow">{e['half_days']}</div><div class="lbl">Half Days</div></div>
      <div class="att-card"><div class="num red">{e['absent']}</div><div class="lbl">Absent</div></div>
      <div class="att-card"><div class="num blue">{e.get('holiday_days', 0)}</div><div class="lbl">Holidays (Paid)</div></div>
      <div class="att-card"><div class="num" style="color:#9333ea">{e.get('leave_days', 0)}</div><div class="lbl">Leave Days</div></div>
    </div>

    <div class="section-title">Salary Breakdown</div>
    <table class="salary-table">
      <tr><td>Full Days ({e['full_days']} days × Rs. {e['spd']:.2f})</td><td class="green">Rs. {e['full_earn']:.2f}</td></tr>
      <tr><td>Late Days ({e['late_days']} days × Rs. {e['spd']:.2f} × 90%)</td><td class="yellow">Rs. {e['late_earn']:.2f}</td></tr>
      <tr><td>Half Days ({e['half_days']} days × Rs. {e['spd']:.2f} × 50%)</td><td class="yellow">Rs. {e['half_earn']:.2f}</td></tr>
      <tr><td>Absent ({e['absent']} days × Rs. 0.00)</td><td class="red">Rs. 0.00</td></tr>
      <tr class="net-row"><td>Net Payable Amount</td><td>Rs. {e['net']:.2f}</td></tr>
    </table>
  </div>
  <div class="footer">
    This is a system-generated salary slip. Please contact HR for any discrepancies.<br>
    Generated on {datetime.date.today().strftime('%d %B %Y')}
  </div>
</div>
</body>
</html>
"""

def send_email_smtp(to_email, subject, html_body, config, attachment_bytes=None, attachment_filename=None):
    from_addr = config.get("from_email") or config["user"]

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = f"{config['from_name']} <{from_addr}>"
    msg["To"]      = to_email
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{attachment_filename}"')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(config["host"], config["port"], timeout=20) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(config["user"], config["password"])
        server.sendmail(from_addr, to_email, msg.as_string())

def send_email_async(to_email, subject, html_body, config, **kwargs):
    def _send():
        try:
            send_email_smtp(to_email, subject, html_body, config, **kwargs)
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()

def build_attendance_email(employee_name, emp_id, action, status, time_str, today_str):
    color = "#16a34a" if action == "login" else "#2563eb"
    action_label = "Checked In" if action == "login" else "Checked Out"
    return f"""
<div style="font-family:Segoe UI,sans-serif;max-width:520px;margin:auto;background:#f8fafc;border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:#1e3a8a;padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">&#127970; Employee Attendance System</div>
    <div style="font-size:13px;opacity:0.75;margin-top:4px;">Attendance Confirmation</div>
  </div>
  <div style="padding:28px;">
    <p style="font-size:15px;color:#1e293b;margin-bottom:20px;">Hi <strong>{employee_name}</strong>,</p>
    <div style="background:#ffffff;border:1px solid #dbeafe;border-radius:12px;padding:20px;margin-bottom:20px;">
      <div style="font-size:28px;font-weight:700;color:{color};text-align:center;margin-bottom:4px;">{action_label}</div>
      <div style="text-align:center;color:#64748b;font-size:13px;">{today_str}</div>
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0;">
      <table style="width:100%;font-size:14px;color:#1e293b;">
        <tr><td style="color:#64748b;padding:4px 0;">Employee ID</td><td style="text-align:right;font-weight:600;">{emp_id}</td></tr>
        <tr><td style="color:#64748b;padding:4px 0;">Time</td><td style="text-align:right;font-weight:600;">{time_str}</td></tr>
        <tr><td style="color:#64748b;padding:4px 0;">Status</td><td style="text-align:right;font-weight:600;color:{color};">{status}</td></tr>
      </table>
    </div>
    <p style="font-size:12px;color:#94a3b8;text-align:center;">This is an automated message. Please do not reply.</p>
  </div>
</div>"""

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
            # Holiday → paid as full day, no attendance required
            full_days += 1
            holiday_days += 1
        elif d in leave_dates:
            # Approved leave → not a working day, no pay and no absent deduction
            leave_days_count += 1
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

# ---------------- ERROR HANDLERS ----------------
import traceback as _traceback

@app.errorhandler(500)
def internal_error(e):
    tb = _traceback.format_exc()
    print("[500 ERROR]", tb)
    return f"<h2>500 – Internal Server Error</h2><pre style='color:red'>{tb}</pre>", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    tb = _traceback.format_exc()
    print("[UNHANDLED]", tb)
    return f"<h2>Error: {type(e).__name__}: {e}</h2><pre style='color:red'>{tb}</pre>", 500

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect("/admin")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT password FROM admin_users WHERE username=%s", (username,))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        if result and check_password_hash(result[0], password):
            session["admin_logged_in"] = True
            session.permanent = True
            return redirect("/admin")
        return render_template("admin_login.html", error="Invalid credentials")
    return render_template("admin_login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@admin_required
def admin():
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
        "SELECT COUNT(DISTINCT employee_id) FROM attendance "
        "WHERE date=%s AND status='Late Login'",
        (today,)
    )
    late = cursor.fetchone()[0]

    cursor.execute(
        "SELECT e.employee_id, e.name, a.login_time, a.logout_time, a.status, "
        "       a.logout_status, a.attendance_type, e.role "
        "FROM employees e "
        "LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s "
        "ORDER BY e.name",
        (today,)
    )
    today_rows = cursor.fetchall()

    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
    all_employees = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return render_template("admin.html",
        total=total,
        present=present,
        absent=total - present,
        late=late,
        today=today.strftime("%d %b %Y"),
        today_rows=today_rows,
        all_employees=all_employees,
        shift_start=SHIFT_START.strftime("%I:%M %p"),
        shift_end=SHIFT_END.strftime("%I:%M %p"),
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        now_month=today.month,
        now_year=today.year,
    )

# ---------------- LIVE DASHBOARD API ----------------
@app.route("/api/dashboard_live")
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

    cursor.execute(
        "SELECT e.employee_id, e.name, a.login_time, a.logout_time, "
        "       a.status, a.logout_status, a.attendance_type, e.role "
        "FROM employees e "
        "LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s "
        "ORDER BY e.name",
        (today,)
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

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
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

# ---------------- TODAY FILTERED VIEWS ----------------
def _today_pending_counts(cursor):
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pl = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pr = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pt = cursor.fetchone()[0]
    return pl, pr, pt

@app.route("/today_present")
@admin_required
def today_present():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, a.login_time, a.logout_time,
               a.status, a.logout_status, a.attendance_type
        FROM employees e
        JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.login_time IS NOT NULL
        ORDER BY a.login_time
    """, (today,))
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="present", title="Present Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)

@app.route("/today_absent")
@admin_required
def today_absent():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.employee_id IS NULL
        ORDER BY e.name
    """, (today,))
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="absent", title="Absent Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)

@app.route("/today_late")
@admin_required
def today_late():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    today = datetime.date.today()
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, a.login_time, a.status
        FROM employees e
        JOIN attendance a ON e.employee_id = a.employee_id AND a.date = %s
        WHERE a.status IN ('Late Login', 'Half Day Login')
        ORDER BY a.login_time
    """, (today,))
    rows = cursor.fetchall()
    pl, pr, pt = _today_pending_counts(cursor)
    cursor.close(); db.close()
    return render_template("today_attendance.html",
        filter_type="late", title="Late Logins Today",
        rows=rows, today=today.strftime("%d %b %Y"),
        pending_leaves=pl, pending_resignations=pr, pending_tickets=pt)

# ---------------- ADMIN ACTIONS ----------------
@app.route("/admin_action", methods=["POST"])
@admin_required
def admin_action():
    action = request.form.get("action")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    if action == "register":
        name            = request.form["name"]
        emp_id          = request.form["emp_id"]
        email           = request.form.get("email", "").strip() or None
        role            = request.form.get("role", "").strip() or None
        date_of_joining = request.form.get("date_of_joining", "").strip() or None
        work_mode       = request.form.get("work_mode", "office").strip() or "office"
        work_lat_raw    = request.form.get("work_lat", "").strip()
        work_lon_raw    = request.form.get("work_lon", "").strip()
        work_lat        = float(work_lat_raw) if work_lat_raw else None
        work_lon        = float(work_lon_raw) if work_lon_raw else None
        file            = request.files["face"]
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        file.save(filepath)

        # Validate that the uploaded photo contains a detectable face
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
                "date_of_joining, work_mode, work_lat, work_lon) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (name, emp_id, email, role, filepath, qr_path, hashed_pwd,
                 date_of_joining, work_mode, work_lat, work_lon)
            )
            db.commit()
            flash(f"✅ Employee '{name}' registered! ID: {emp_id} | Password: {auto_pass}", "success")
            # Send welcome email with credentials
            if email:
                _ecfg = get_email_config()
                if _ecfg:
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
                    send_email_async(email, f"Welcome {name} — Your Login Credentials", _welcome_html, _ecfg)
        except mysql.connector.errors.IntegrityError:
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
        name     = row[0]
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        file.save(filepath)
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

# ---------------- ANNOUNCEMENTS ----------------
@app.route("/announcements", methods=["GET", "POST"])
@admin_required
def announcements_admin():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            cursor.execute(
                "INSERT INTO announcements (title, content, priority) VALUES (%s,%s,%s)",
                (request.form["title"], request.form["content"], request.form.get("priority","Normal"))
            )
            db.commit()
            flash("Announcement posted.", "success")
        elif action == "delete":
            cursor.execute("DELETE FROM announcements WHERE id=%s", (request.form["ann_id"],))
            db.commit()
            flash("Announcement deleted.", "success")
        cursor.close(); db.close()
        return redirect("/announcements")

    cursor.execute("SELECT id, title, content, priority, created_at FROM announcements ORDER BY created_at DESC")
    ann_list = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    pending_tickets = cursor.fetchone()[0]
    cursor.close(); db.close()
    return render_template("announcements.html",
        ann_list=ann_list,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    )

# ---------------- INDIAN PUBLIC HOLIDAYS ----------------
def get_indian_holidays(year):
    """Returns sorted list of (date, name) for major Indian public holidays."""
    fixed = [
        (1,  1,  "New Year's Day"),
        (1,  26, "Republic Day"),
        (8,  15, "Independence Day"),
        (10, 2,  "Gandhi Jayanti"),
        (12, 25, "Christmas Day"),
    ]
    variable_by_year = {
        2025: [
            (1, 14, "Makar Sankranti / Pongal"),
            (2, 26, "Maha Shivaratri"),
            (3, 14, "Holi"),
            (3, 31, "Eid ul-Fitr"),
            (4, 14, "Dr. Ambedkar Jayanti"),
            (4, 18, "Good Friday"),
            (5,  1, "Maharashtra Day / Labour Day"),
            (6,  7, "Eid ul-Adha"),
            (8, 16, "Janmashtami"),
            (10, 2,  "Dussehra / Vijayadasami"),
            (10, 20, "Diwali (Lakshmi Puja)"),
            (11,  5, "Guru Nanak Jayanti"),
        ],
        2026: [
            (1, 14, "Makar Sankranti / Pongal"),
            (2, 15, "Maha Shivaratri"),
            (3,  5, "Holi"),
            (3, 20, "Eid ul-Fitr"),
            (4,  3, "Good Friday"),
            (4, 14, "Dr. Ambedkar Jayanti / Baisakhi"),
            (5,  1, "Maharashtra Day / Labour Day"),
            (5, 27, "Eid ul-Adha"),
            (8, 21, "Janmashtami"),
            (10, 21, "Dussehra / Vijayadasami"),
            (10, 30, "Diwali (Lakshmi Puja)"),
            (11, 25, "Guru Nanak Jayanti"),
        ],
        2027: [
            (1, 14, "Makar Sankranti / Pongal"),
            (3,  5, "Maha Shivaratri"),
            (3, 26, "Holi"),
            (4,  2, "Good Friday"),
            (4, 14, "Dr. Ambedkar Jayanti"),
            (5,  1, "Maharashtra Day / Labour Day"),
            (8, 15, "Independence Day"),
            (9,  4, "Janmashtami"),
            (10, 8,  "Dussehra / Vijayadasami"),
            (10, 17, "Diwali (Lakshmi Puja)"),
            (11, 14, "Guru Nanak Jayanti"),
        ],
    }
    result = []
    for m, d, name in fixed:
        try:
            result.append((datetime.date(year, m, d), name))
        except ValueError:
            pass
    for m, d, name in variable_by_year.get(year, []):
        try:
            result.append((datetime.date(year, m, d), name))
        except ValueError:
            pass
    return sorted(result, key=lambda x: x[0])

# ---------------- VIEW HOLIDAYS ----------------
@app.route("/view_holidays")
@admin_required
def view_holidays():
    year = int(request.args.get("year", datetime.date.today().year))
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT * FROM holidays ORDER BY date")
    data = cursor.fetchall()
    cursor.close()
    db.close()

    # Build holiday map: date -> (id, name)
    holiday_map = {}
    for row in data:
        date_val = row[1]
        if isinstance(date_val, datetime.date):
            holiday_map[date_val] = (row[0], row[2])

    # Build calendar data, weeks starting Sunday (firstweekday=6)
    sun_cal = calendar.Calendar(firstweekday=6)
    today   = datetime.date.today()
    cal_data = []
    for month in range(1, 13):
        month_holidays = {}  # day_number -> (id, name)
        for date_obj, (hid, hname) in holiday_map.items():
            if date_obj.year == year and date_obj.month == month:
                month_holidays[date_obj.day] = (hid, hname)
        cal_data.append({
            'month_num':  month,
            'month_name': calendar.month_name[month],
            'weeks':      sun_cal.monthdayscalendar(year, month),
            'holidays':   month_holidays,
        })

    return render_template("holidays.html", holidays=data, cal_data=cal_data,
                           year=year, today=today)

@app.route("/add_holiday", methods=["POST"])
@admin_required
def add_holiday():
    date         = request.form["date"]
    year         = date[:4]
    entry_type   = request.form.get("type", "Holiday")
    holiday_name = request.form["holiday_name"].strip()
    if entry_type == "Leave":
        holiday_name = "Leave:" + holiday_name
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute("INSERT INTO holidays (date, name) VALUES (%s,%s)", (date, holiday_name))
        db.commit()
    except mysql.connector.errors.IntegrityError:
        pass  # duplicate date — silently ignore
    cursor.close()
    db.close()
    return redirect(f"/view_holidays?year={year}")

@app.route("/delete_employee/<emp_id>", methods=["POST"])
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
        flash(f"Employee '{emp_id}' deleted successfully.", "success")
    else:
        flash(f"Employee '{emp_id}' not found.", "error")
    cursor.close(); db.close()
    return redirect("/employees")


@app.route("/edit_employee", methods=["POST"])
@admin_required
def edit_employee():
    emp_id          = request.form["emp_id"].strip()
    name            = request.form.get("name", "").strip()
    email           = request.form.get("email", "").strip() or None
    role            = request.form.get("role", "").strip() or None
    date_of_joining = request.form.get("date_of_joining", "").strip() or None
    db       = get_db_connection()
    cursor   = db.cursor(buffered=True)
    if request.form.get("update_work_mode"):
        work_mode    = request.form.get("work_mode", "office").strip() or "office"
        work_lat_raw = request.form.get("work_lat", "").strip()
        work_lon_raw = request.form.get("work_lon", "").strip()
        work_lat     = float(work_lat_raw) if work_lat_raw else None
        work_lon     = float(work_lon_raw) if work_lon_raw else None
        cursor.execute(
            "UPDATE employees SET name=%s, email=%s, role=%s, date_of_joining=%s, "
            "work_mode=%s, work_lat=%s, work_lon=%s WHERE employee_id=%s",
            (name, email, role, date_of_joining, work_mode, work_lat, work_lon, emp_id)
        )
    else:
        cursor.execute(
            "UPDATE employees SET name=%s, email=%s, role=%s, date_of_joining=%s "
            "WHERE employee_id=%s",
            (name, email, role, date_of_joining, emp_id)
        )
    db.commit(); cursor.close(); db.close()
    flash(f"Employee '{emp_id}' updated successfully.", "success")
    return redirect("/employees")


@app.route("/employees")
@admin_required
def view_employees():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.role, e.email, e.date_of_joining,
               COUNT(a.date)  AS total_days,
               MAX(a.date)    AS last_seen,
               e.work_mode, e.work_lat, e.work_lon
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id = a.employee_id
        GROUP BY e.employee_id, e.name, e.role, e.email, e.date_of_joining,
                 e.work_mode, e.work_lat, e.work_lon
        ORDER BY e.name
    """)
    employees = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return render_template("employees.html",
        employees=employees,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    )


@app.route("/change_admin_password", methods=["POST"])
@admin_required
def change_admin_password():
    current_pw = request.form.get("current_password", "")
    new_pw     = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")
    if not new_pw or new_pw != confirm_pw:
        return redirect("/admin?pwd_error=mismatch")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT password FROM admin_users WHERE username='admin'")
    row = cursor.fetchone()
    if not row or not check_password_hash(row[0], current_pw):
        cursor.close(); db.close()
        return redirect("/admin?pwd_error=wrong")
    cursor.execute(
        "UPDATE admin_users SET password=%s WHERE username='admin'",
        (generate_password_hash(new_pw),)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/admin?pwd_ok=1")


@app.route("/admin_set_recovery_email", methods=["POST"])
@admin_required
def admin_set_recovery_email():
    email = request.form.get("recovery_email", "").strip()
    if email:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE admin_users SET email=%s WHERE username='admin'", (email,))
        db.commit(); cursor.close(); db.close()
    return redirect("/admin?email_ok=1#password-management")



@app.route("/admin_forgot_password", methods=["GET", "POST"])
def admin_forgot_password():
    if request.method == "GET":
        return render_template("admin_forgot_password.html",
                               sent=False, error=None)
    admin_email = request.form.get("email", "").strip()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, email FROM admin_users WHERE username='admin'")
    row = cursor.fetchone()
    if not row or not row[1]:
        cursor.close(); db.close()
        return render_template("admin_forgot_password.html", sent=False,
                               error="No email is set for the admin account. Contact your system administrator.")
    if row[1].lower() != admin_email.lower():
        cursor.close(); db.close()
        return render_template("admin_forgot_password.html", sent=False,
                               error="Email address does not match the admin account.")
    token   = secrets.token_hex(32)
    expiry  = datetime.datetime.now() + datetime.timedelta(hours=1)
    cursor.execute(
        "UPDATE admin_users SET reset_token=%s, reset_token_expiry=%s WHERE username='admin'",
        (token, expiry)
    )
    db.commit(); cursor.close(); db.close()
    cfg = get_email_config()
    if not cfg:
        return render_template("admin_forgot_password.html", sent=False,
                               error="Email service not configured. Go to Admin → Email Settings first.")
    reset_url = f"{request.host_url}admin_reset_password/{token}"
    html_body = f"""
<div style="font-family:Segoe UI,sans-serif;max-width:520px;margin:auto;background:#f8fafc;border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:#1e3a8a;padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">🔐 Admin Password Reset</div>
    <div style="font-size:13px;opacity:0.75;margin-top:4px;">Employee Attendance System</div>
  </div>
  <div style="padding:28px;">
    <p style="font-size:15px;color:#1e293b;margin-bottom:20px;">You requested a password reset for the admin account.</p>
    <a href="{reset_url}" style="display:block;text-align:center;padding:14px 28px;background:#1e3a8a;color:white;border-radius:10px;text-decoration:none;font-size:15px;font-weight:700;margin-bottom:20px;">
      Reset My Password
    </a>
    <p style="font-size:13px;color:#64748b;">This link expires in <strong>1 hour</strong>. If you did not request this, ignore this email.</p>
    <p style="font-size:12px;color:#94a3b8;margin-top:12px;">Or copy this link: {reset_url}</p>
  </div>
</div>"""
    try:
        send_email_smtp(admin_email, "Admin Password Reset — Attendance System", html_body, cfg)
    except Exception as ex:
        return render_template("admin_forgot_password.html", sent=False,
                               error=f"Failed to send email: {str(ex)}")
    return render_template("admin_forgot_password.html", sent=True, error=None)


@app.route("/admin_reset_password/<token>", methods=["GET", "POST"])
def admin_reset_password(token):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id FROM admin_users WHERE reset_token=%s AND reset_token_expiry > %s",
        (token, datetime.datetime.now())
    )
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=False, done=False, token=token)
    if request.method == "GET":
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=True, done=False, token=token, error=None)
    new_pw     = request.form.get("new_password", "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()
    if len(new_pw) < 6:
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=True, done=False,
                               token=token, error="Password must be at least 6 characters.")
    if new_pw != confirm_pw:
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=True, done=False,
                               token=token, error="Passwords do not match.")
    cursor.execute(
        "UPDATE admin_users SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE username='admin'",
        (generate_password_hash(new_pw),)
    )
    db.commit(); cursor.close(); db.close()
    return render_template("admin_reset_password.html", valid=True, done=True, token=token, error=None)


@app.route("/view_qrcodes")
@admin_required
def view_qrcodes():
    return redirect("/view_photos")


@app.route("/dataset/<path:filename>")
@admin_required
def serve_dataset(filename):
    from flask import send_from_directory
    return send_from_directory(os.path.abspath("dataset"), filename)


@app.route("/my_photo")
def my_photo():
    from flask import send_from_directory
    emp_id = session.get("employee_id")
    if not emp_id:
        return "", 403
    photo_path = os.path.join("dataset", emp_id + ".jpg")
    if not os.path.exists(photo_path):
        return "", 404
    return send_from_directory(os.path.abspath("dataset"), emp_id + ".jpg")


@app.route("/view_photos")
@admin_required
def view_photos():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name, role, email, face_image, qr_code FROM employees ORDER BY name")
    employees = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("employee_photos.html", employees=employees)


@app.route("/update_photo/<emp_id>", methods=["POST"])
@admin_required
def update_photo(emp_id):
    file = request.files.get("photo")
    if not file or not file.filename:
        return jsonify({"ok": False, "msg": "No file selected"}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        return jsonify({"ok": False, "msg": "Only JPG/PNG files are allowed"}), 400
    save_path = os.path.join("dataset", emp_id + ".jpg")
    file.save(save_path)
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (emp_id + ".jpg", emp_id))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})

# ---------------- SHIFTS ----------------
@app.route("/shifts", methods=["GET"])
@admin_required
def shifts():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, name, start_time, half_time, end_time FROM shifts ORDER BY start_time")
    shift_rows = []
    for sid, name, st, ht, et in cursor.fetchall():
        shift_rows.append({
            "id":    sid, "name": name,
            "start": _td_to_time(st).strftime("%H:%M") if st else "--",
            "half":  _td_to_time(ht).strftime("%H:%M") if ht else "--",
            "end":   _td_to_time(et).strftime("%H:%M") if et else "--",
        })
    cursor.execute(
        "SELECT e.employee_id, e.name, e.role, s.name "
        "FROM employees e LEFT JOIN shifts s ON e.shift_id = s.id ORDER BY e.name"
    )
    employees = [{"emp_id": r[0], "name": r[1], "role": r[2] or "", "shift": r[3] or "Default"} for r in cursor.fetchall()]
    cursor.close(); db.close()
    return render_template("shifts.html", shifts=shift_rows, employees=employees,
                           default_start=SHIFT_START.strftime("%H:%M"),
                           default_half=SHIFT_HALF.strftime("%H:%M"),
                           default_end=SHIFT_END.strftime("%H:%M"))

@app.route("/add_shift", methods=["POST"])
@admin_required
def add_shift():
    name  = request.form.get("name", "").strip()
    start = request.form.get("start_time", "").strip()
    half  = request.form.get("half_time",  "").strip()
    end   = request.form.get("end_time",   "").strip()
    if not all([name, start, half, end]):
        return redirect("/shifts?error=All+fields+required")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute(
            "INSERT INTO shifts (name, start_time, half_time, end_time) VALUES (%s,%s,%s,%s)",
            (name, start, half, end)
        )
        db.commit()
    except mysql.connector.errors.IntegrityError:
        pass
    cursor.close(); db.close()
    return redirect("/shifts?saved=1")

@app.route("/delete_shift/<int:sid>", methods=["POST"])
@admin_required
def delete_shift(sid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("DELETE FROM shifts WHERE id=%s", (sid,))
    db.commit()
    cursor.close(); db.close()
    return redirect("/shifts?deleted=1")

@app.route("/edit_shift/<int:sid>", methods=["POST"])
@admin_required
def edit_shift(sid):
    name  = request.form.get("name",  "").strip()
    start = request.form.get("start_time", "").strip()
    half  = request.form.get("half_time",  "").strip()
    end   = request.form.get("end_time",   "").strip()
    if not all([name, start, half, end]):
        return redirect("/shifts?error=All+fields+required")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE shifts SET name=%s, start_time=%s, half_time=%s, end_time=%s WHERE id=%s",
        (name, start, half, end, sid)
    )
    db.commit()
    cursor.close(); db.close()
    return redirect("/shifts?updated=1")

@app.route("/bulk_assign_shift", methods=["POST"])
@admin_required
def bulk_assign_shift():
    shift_id  = request.form.get("shift_id", "").strip()
    emp_ids   = request.form.getlist("emp_ids")
    if not emp_ids:
        return redirect("/shifts?error=No+employees+selected")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    for emp_id in emp_ids:
        cursor.execute(
            "UPDATE employees SET shift_id=%s WHERE employee_id=%s",
            (shift_id if shift_id else None, emp_id)
        )
    db.commit()
    cursor.close(); db.close()
    return redirect("/shifts?bulk_saved=1")

@app.route("/assign_shift", methods=["POST"])
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


@app.route("/import_indian_holidays", methods=["POST"])
@admin_required
def import_indian_holidays():
    year = int(request.form.get("year", datetime.date.today().year))
    holidays_list = get_indian_holidays(year)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    for date_obj, name in holidays_list:
        try:
            cursor.execute(
                "INSERT IGNORE INTO holidays (date, name) VALUES (%s, %s)",
                (date_obj, name)
            )
        except Exception:
            pass
    db.commit()
    cursor.close(); db.close()
    return redirect(f"/view_holidays?year={year}")

@app.route("/delete_holiday/<int:hid>", methods=["POST"])
@admin_required
def delete_holiday(hid):
    year = request.form.get("year", datetime.date.today().year)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM holidays WHERE id=%s", (hid,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(f"/view_holidays?year={year}")

# ---------------- VIEW SALARY CONFIG ----------------
@app.route("/view_salary")
@admin_required
def view_salary():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
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
    return render_template("salary.html", salaries=data)

@app.route("/update_salary", methods=["POST"])
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
    return redirect("/view_salary")

# ---------------- MONTHLY ATTENDANCE REPORT ----------------
@app.route("/monthly_report")
@admin_required
def monthly_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

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
        year=year, month=month,
        months=months, years=years,
        holiday_count=len(holidays),
        total_working=len([d for d in working_days if d <= today and d not in holidays]),
    )

# ---------------- MONTHLY REPORT EXCEL EXPORT ----------------
@app.route("/monthly_report_export")
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

# ---------------- ABSENTEE REPORT EMAIL ----------------
@app.route("/send_absentee_report", methods=["POST"])
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
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Failed to send: {str(e)}"})

# ---------------- SALARY REPORT ----------------
@app.route("/salary_report")
@admin_required
def salary_report():
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

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

    cursor.close()
    db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)

    salary_data = []
    for emp_id, name, email, spd, role, phone in employees:
        entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                     holidays_set=holidays_set,
                                     leave_dates=leave_map.get(emp_id, set()))
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
        year=year, month=month,
        months=months, years=years,
        late_rate=int(LATE_DEDUCTION_RATE * 100),
        half_rate=int(HALF_DAY_RATE * 100),
        email_configured=email_cfg is not None,
    )

# ---------------- EMAIL CONFIG ----------------
@app.route("/email_config", methods=["GET", "POST"])
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
            (host, port, user, password, from_name, from_email)
        )
        db.commit()
        cursor.close()
        db.close()
        return redirect("/email_config?saved=1")

    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email FROM email_config ORDER BY id DESC LIMIT 1")
    row    = cursor.fetchone()
    config = {"host": row[0], "port": row[1], "user": row[2], "password": row[3], "from_name": row[4], "from_email": row[5] or row[2]} if row else None
    cursor.close()
    db.close()

    return render_template("email_config.html",
        config=config,
        saved=request.args.get("saved") == "1",
    )

# ---------------- SEND SALARY EMAIL (single) ----------------
@app.route("/send_salary_email", methods=["POST"])
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

    cursor.execute("SELECT name, email, COALESCE(s.salary_per_day, 0) FROM employees e LEFT JOIN salary_config s ON e.employee_id=s.employee_id WHERE e.employee_id=%s", (emp_id,))
    emp = cursor.fetchone()
    if not emp:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found."})

    name, email, spd = emp
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

    cursor.close(); db.close()

    holidays_set  = fetch_holidays_set(year, month)
    billable_past = get_billable_past_days(year, month)
    entry         = compute_salary_entry(emp_id, name, spd, att_map, billable_past,
                                         holidays_set=holidays_set, leave_dates=leave_dates)
    month_name    = datetime.date(year, month, 1).strftime("%B %Y")
    html_body     = build_salary_slip_html(name, emp_id, email, month_name, year, month, entry)

    try:
        send_email_smtp(email, f"Salary Slip - {month_name}", html_body, config)
        return jsonify({"ok": True, "msg": f"Salary slip sent to {email}"})
    except Exception as ex:
        return jsonify({"ok": False, "msg": f"Email failed: {str(ex)}"})

# ---------------- SEND ALL SALARY EMAILS ----------------
@app.route("/send_all_salary_emails", methods=["POST"])
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
        except Exception as ex:
            failed += 1
            errors.append(f"{name}: {str(ex)}")

    msg = f"Sent: {sent}, Skipped (no email): {skipped}, Failed: {failed}"
    if errors:
        msg += " | " + "; ".join(errors[:3])
    return jsonify({"ok": failed == 0, "msg": msg})

# ---------------- TEST EMAIL ----------------
@app.route("/test_email", methods=["POST"])
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
    except Exception as ex:
        return jsonify({"ok": False, "msg": f"Failed: {str(ex)}"})

# ---------------- LOCATION ----------------
@app.route("/location", methods=["POST"])
def location():
    data = request.get_json()
    session["lat"] = data["lat"]
    session["lon"] = data["lon"]
    return jsonify({"status": "ok"})

# ---------------- DISTANCE CHECK ----------------
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

# ---------------- ATTENDANCE (LOGIN + LOGOUT) ----------------
@app.route("/attendance", methods=["POST"])
def attendance():
    import base64, io
    import numpy as np
    from PIL import Image

    data       = request.get_json() or {}
    emp_id     = data.get("employee_id", "").strip()
    face_b64   = data.get("face_image", "")
    user_lat   = data.get("lat")
    user_lon   = data.get("lon")

    if not emp_id:
        return jsonify({"ok": False, "msg": "No QR code data received."})
    if not face_b64:
        return jsonify({"ok": False, "msg": "Face photo not captured."})

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
        return jsonify({"ok": False, "msg": "Employee not found. Please check your QR code."})

    face_path, employee_name, employee_email, emp_work_mode, emp_work_lat, emp_work_lon = result

    # Location check: WFH → must be within 300 m of home; Office → must be within 300 m of office
    if not user_lat or not user_lon:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Location not captured. Please allow location access."})
    if emp_work_mode == 'wfh':
        if emp_work_lat and emp_work_lon:
            if not is_within_range(float(user_lat), float(user_lon), float(emp_work_lat), float(emp_work_lon)):
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "You are outside your registered home location."})
        # no home location set → allow (admin can set it later)
    else:
        if not is_within_range(float(user_lat), float(user_lon), OFFICE_LAT, OFFICE_LON):
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "You are outside the office premises."})

    if not os.path.exists(face_path):
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Face image missing. Please re-register."})

    known_image    = face_recognition.load_image_file(face_path)
    known_encs     = face_recognition.face_encodings(known_image)
    if not known_encs:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Stored face image is invalid. Please re-register."})
    known_encoding = known_encs[0]

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
        "SELECT login_time, logout_time, status FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record              = cursor.fetchone()
    login_time          = record[0] if record else None
    logout_time         = record[1] if record else None
    login_status_stored = record[2] if record else None

    # Use employee's assigned shift, or global defaults
    s_start, s_half, s_end, shift_name = get_employee_shift(emp_id, cursor)

    if not login_time:
        if current_time <= s_start:
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
        if employee_email:
            cfg = get_email_config()
            if cfg:
                html = build_attendance_email(employee_name, emp_id, "login", login_status, time_str, today.strftime("%d %b %Y"))
                send_email_async(employee_email, f"Attendance Check-In — {today.strftime('%d %b %Y')}", html, cfg)
        return jsonify({"ok": True, "type": "login", "name": employee_name,
                        "status": login_status, "time": time_str, "shift": shift_name,
                        "work_mode": emp_work_mode})

    elif not logout_time:
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
        att_type = get_attendance_type(login_status_stored, logout_status)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, logout_status, att_type, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        time_str = current_time.strftime("%H:%M:%S")
        if employee_email:
            cfg = get_email_config()
            if cfg:
                html = build_attendance_email(employee_name, emp_id, "logout", att_type or logout_status, time_str, today.strftime("%d %b %Y"))
                send_email_async(employee_email, f"Attendance Check-Out — {today.strftime('%d %b %Y')}", html, cfg)
        resp = {"ok": True, "type": "logout", "name": employee_name,
                "status": logout_status, "att_type": att_type,
                "time": time_str, "shift": shift_name, "work_mode": emp_work_mode}
        if overtime_m > 0:
            resp["overtime"] = f"{overtime_m // 60}h {overtime_m % 60}m" if overtime_m >= 60 else f"{overtime_m}m"
        return jsonify(resp)

    else:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Attendance already completed for today."})

# ================================================================
#  EMPLOYEE PORTAL
# ================================================================

@app.route("/employee_login", methods=["GET", "POST"])
def employee_login():
    if session.get("employee_id"):
        return redirect("/employee_portal")
    if request.method == "POST":
        emp_id   = request.form["emp_id"].strip()
        password = request.form.get("password", "").strip()
        db       = get_db_connection()
        cursor   = db.cursor(buffered=True)
        cursor.execute(
            "SELECT employee_id, name, role, password FROM employees WHERE employee_id=%s",
            (emp_id,)
        )
        row = cursor.fetchone()
        cursor.close(); db.close()
        if not row:
            return render_template("employee_login.html", error="Employee ID not found.")
        stored_pwd = row[3]
        if stored_pwd and not check_password_hash(stored_pwd, password):
            return render_template("employee_login.html", error="Incorrect password.")
        session["employee_id"]   = row[0]
        session["employee_name"] = row[1]
        session["employee_role"] = row[2] or ""
        session.permanent = True
        return redirect("/employee_portal")
    return render_template("employee_login.html")


@app.route("/employee_logout")
def employee_logout():
    session.pop("employee_id", None)
    session.pop("employee_name", None)
    session.pop("employee_role", None)
    return redirect("/employee_login")


@app.route("/change_password", methods=["POST"])
@employee_required
def change_password():
    emp_id   = session["employee_id"]
    current  = request.form.get("current_password", "").strip()
    new_pwd  = request.form.get("new_password", "").strip()
    confirm  = request.form.get("confirm_password", "").strip()
    db       = get_db_connection()
    cursor   = db.cursor(buffered=True)
    cursor.execute("SELECT password FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    if not row or not check_password_hash(row[0], current):
        cursor.close(); db.close()
        return redirect("/employee_portal?pwd_error=wrong#my-profile")
    if len(new_pwd) < 6:
        cursor.close(); db.close()
        return redirect("/employee_portal?pwd_error=short#my-profile")
    if new_pwd != confirm:
        cursor.close(); db.close()
        return redirect("/employee_portal?pwd_error=mismatch#my-profile")
    cursor.execute(
        "UPDATE employees SET password=%s WHERE employee_id=%s",
        (generate_password_hash(new_pwd), emp_id)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?pwd_ok=1#my-profile")


@app.route("/update_my_profile", methods=["POST"])
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
    }
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        UPDATE employees SET
            phone=%s, gender=%s, dob=%s, blood_group=%s,
            address=%s, city=%s, state=%s, pincode=%s,
            emergency_contact_name=%s, emergency_contact_phone=%s, emergency_contact_relation=%s
        WHERE employee_id=%s
    """, (*fields.values(), emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?profile_saved=1#my-profile")


@app.route("/update_my_bank_details", methods=["POST"])
@employee_required
def update_my_bank_details():
    emp_id = session["employee_id"]
    fields = {
        "aadhar_number": request.form.get("aadhar_number", "").strip() or None,
        "pan_number":    request.form.get("pan_number", "").upper().strip() or None,
        "bank_name":     request.form.get("bank_name", "").strip() or None,
        "bank_account":  request.form.get("bank_account", "").strip() or None,
        "bank_ifsc":     request.form.get("bank_ifsc", "").upper().strip() or None,
        "uan_number":    request.form.get("uan_number", "").strip() or None,
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


@app.route("/update_my_photo", methods=["POST"])
@employee_required
def update_my_photo():
    from flask import send_from_directory
    import numpy as np
    from PIL import Image
    import base64, io
    emp_id = session["employee_id"]
    file = request.files.get("photo")
    if not file or not file.filename:
        return redirect("/employee_portal?photo_error=no_file#my-profile")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        return redirect("/employee_portal?photo_error=bad_format#my-profile")
    try:
        img = Image.open(file.stream).convert("RGB")
        img_array = np.array(img)
        locs = face_recognition.face_locations(img_array)
        if not locs:
            return redirect("/employee_portal?photo_error=no_face#my-profile")
        save_path = os.path.join("dataset", emp_id + ".jpg")
        img.save(save_path, "JPEG", quality=90)
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE employees SET face_image=%s WHERE employee_id=%s", (emp_id + ".jpg", emp_id))
        db.commit(); cursor.close(); db.close()
        return redirect("/employee_portal?photo_saved=1#my-profile")
    except Exception:
        return redirect("/employee_portal?photo_error=failed#my-profile")


@app.route("/my_qr")
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


@app.route("/my_id_card")
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


@app.route("/employee_portal")
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
               e.qr_code, e.work_mode
        FROM employees e
        LEFT JOIN salary_config sc ON e.employee_id = sc.employee_id
        LEFT JOIN shifts sh ON e.shift_id = sh.id
        WHERE e.employee_id = %s
    """, (emp_id,))
    emp = cursor.fetchone()
    # emp indices:
    # [0]=id [1]=name [2]=role [3]=email [4]=face_image [5]=date_of_joining
    # [6]=salary_per_day [7]=shift_name [8]=shift_start [9]=shift_end
    # [10]=phone [11]=gender [12]=dob [13]=blood_group
    # [14]=address [15]=city [16]=state [17]=pincode
    # [18]=emergency_contact_name [19]=emergency_contact_phone [20]=emergency_contact_relation
    # [21]=aadhar_number [22]=pan_number [23]=bank_name [24]=bank_account [25]=bank_ifsc [26]=uan_number
    # [27]=qr_code [28]=work_mode

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

    # Calendar data as JSON for JS rendering
    import json as _json
    cal_data = {}
    _, month_days = calendar.monthrange(year, month)
    for day in range(1, month_days + 1):
        d = datetime.date(year, month, day)
        if d in holidays_set:
            cal_data[day] = "holiday"
        elif d.weekday() >= 5:
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
    cal_json      = _json.dumps(cal_data)
    cal_year      = year
    cal_month     = month
    cal_first_dow = datetime.date(year, month, 1).weekday()  # 0=Mon

    cursor.execute("""
        SELECT leave_date, reason, status, created_at
        FROM leave_requests WHERE employee_id=%s
        ORDER BY created_at DESC LIMIT 10
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

    # Leave balance
    annual_leave_quota = 12
    cursor.execute("""
        SELECT COUNT(*) FROM leave_requests
        WHERE employee_id=%s AND YEAR(leave_date)=%s AND status IN ('Approved','Pending')
    """, (emp_id, today.year))
    leaves_used = cursor.fetchone()[0] or 0
    leave_balance = max(0, annual_leave_quota - leaves_used)

    # Announcements for dashboard
    cursor.execute("""
        SELECT id, title, content, priority, created_at
        FROM announcements ORDER BY created_at DESC LIMIT 10
    """)
    announcements = cursor.fetchall()

    # Pending leave count for nav badge
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE employee_id=%s AND status='Pending'", (emp_id,))
    pending_leaves_count = cursor.fetchone()[0] or 0

    # Open ticket count for nav badge
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE employee_id=%s AND status='Open'", (emp_id,))
    open_tickets_count = cursor.fetchone()[0] or 0

    # Upcoming holidays (next 3 from today)
    cursor.execute("""
        SELECT date, name FROM holidays WHERE date >= %s ORDER BY date LIMIT 3
    """, (today,))
    upcoming_holidays = cursor.fetchall()

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
        today=today.strftime("%d %b %Y"),
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
        cal_json=cal_json,
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
        announcements=announcements,
        pending_leaves_count=pending_leaves_count,
        open_tickets_count=open_tickets_count,
        upcoming_holidays=upcoming_holidays,
    )


@app.route("/my_payslip_summary/<int:year>/<int:month>")
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
    net = round(gross - pf, 2)

    return _json.dumps({
        "salary_per_day": spd,
        "full_days": full, "late_days": late, "half_days": half,
        "full_earn": full_earn, "late_earn": late_earn, "half_earn": half_earn,
        "gross": gross, "pf": pf, "net": net
    }), 200, {"Content-Type": "application/json"}


@app.route("/my_attendance_pdf")
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

@app.route("/request_leave", methods=["POST"])
@employee_required
def request_leave():
    emp_id     = session["employee_id"]
    emp_name   = session["employee_name"]
    leave_date = request.form.get("leave_date", "").strip()
    reason     = request.form.get("reason", "").strip()
    if not reason or not leave_date:
        return redirect("/employee_portal")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO leave_requests (employee_id, leave_date, reason) VALUES (%s,%s,%s)",
        (emp_id, leave_date, reason)
    )
    db.commit()
    cursor.close(); db.close()

    config = get_email_config()
    if config:
        html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px;color:white;text-align:center;">
    <h2 style="margin:0;font-size:20px;">Leave Request Received</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px;">Employee Attendance System</p>
  </div>
  <div style="padding:24px;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <tr style="background:#f8f9fc;"><td style="padding:10px 14px;color:#555;font-weight:600;width:130px;">Employee</td><td style="padding:10px 14px;">{emp_name}</td></tr>
      <tr><td style="padding:10px 14px;color:#555;font-weight:600;">Employee ID</td><td style="padding:10px 14px;">{emp_id}</td></tr>
      <tr style="background:#f8f9fc;"><td style="padding:10px 14px;color:#555;font-weight:600;">Leave Date</td><td style="padding:10px 14px;">{leave_date}</td></tr>
      <tr><td style="padding:10px 14px;color:#555;font-weight:600;">Reason</td><td style="padding:10px 14px;">{reason}</td></tr>
    </table>
    <p style="margin-top:20px;padding:12px 16px;background:#fef9c3;border-radius:8px;color:#854d0e;font-size:13px;">
      Please log in to the <strong>Admin Panel</strong> to approve or reject this leave request.
    </p>
  </div>
</div>"""
        try:
            send_email_smtp(
                config.get("from_email", config["user"]),
                f"Leave Request — {emp_name} ({leave_date})",
                html_body, config
            )
        except Exception as e:
            print(f"[EMAIL ERROR] Leave request notification failed: {e}")

    return redirect("/employee_portal?leave_sent=1#apply-leave")


@app.route("/leave_requests")
@admin_required
def leave_requests_view():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT lr.id, e.name, lr.employee_id, lr.leave_date, lr.reason, lr.status, lr.created_at
        FROM leave_requests lr
        JOIN employees e ON lr.employee_id = e.employee_id
        ORDER BY FIELD(lr.status, 'Pending', 'Approved', 'Rejected'), lr.created_at DESC
    """)
    leaves = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("leave_requests.html", leaves=leaves)


@app.route("/leave_action/<int:lid>", methods=["POST"])
@admin_required
def leave_action(lid):
    action = request.form.get("action", "")
    if action in ("Approved", "Rejected"):
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE leave_requests SET status=%s WHERE id=%s", (action, lid))
        if action == "Approved":
            cursor.execute(
                "SELECT employee_id, leave_date FROM leave_requests WHERE id=%s", (lid,)
            )
            row = cursor.fetchone()
            if row:
                emp_id, leave_date = row
                cursor.execute("""
                    INSERT INTO attendance (employee_id, date, attendance_type)
                    VALUES (%s, %s, 'Approved Leave')
                    ON DUPLICATE KEY UPDATE attendance_type='Approved Leave'
                """, (emp_id, leave_date))
        db.commit()
        cursor.close(); db.close()
    return redirect("/leave_requests")


@app.route("/request_resignation", methods=["POST"])
@employee_required
def request_resignation():
    emp_id          = session["employee_id"]
    emp_name        = session["employee_name"]
    last_working_day = request.form.get("last_working_day", "").strip()
    reason          = request.form.get("resign_reason", "").strip()
    if not reason or not last_working_day:
        return redirect("/employee_portal#resign")

    try:
        lwd = datetime.datetime.strptime(last_working_day, "%Y-%m-%d").date()
    except ValueError:
        return redirect("/employee_portal#resign")

    min_lwd = datetime.date.today() + datetime.timedelta(days=30)
    if lwd < min_lwd:
        return redirect("/employee_portal#resign")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO resignation_requests (employee_id, last_working_day, reason) VALUES (%s,%s,%s)",
        (emp_id, last_working_day, reason)
    )
    db.commit()
    cursor.close(); db.close()

    config = get_email_config()
    if config:
        html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);padding:24px;color:white;text-align:center;">
    <h2 style="margin:0;font-size:20px;">⚠️ Resignation Notice Received</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px;">Employee Attendance System</p>
  </div>
  <div style="padding:24px;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <tr style="background:#f8f9fc;"><td style="padding:10px 14px;color:#555;font-weight:600;width:160px;">Employee</td><td style="padding:10px 14px;">{emp_name}</td></tr>
      <tr><td style="padding:10px 14px;color:#555;font-weight:600;">Employee ID</td><td style="padding:10px 14px;">{emp_id}</td></tr>
      <tr style="background:#f8f9fc;"><td style="padding:10px 14px;color:#555;font-weight:600;">Last Working Day</td><td style="padding:10px 14px;">{last_working_day}</td></tr>
      <tr><td style="padding:10px 14px;color:#555;font-weight:600;">Reason</td><td style="padding:10px 14px;">{reason}</td></tr>
    </table>
    <p style="margin-top:20px;padding:12px 16px;background:#fee2e2;border-radius:8px;color:#991b1b;font-size:13px;">
      Please log in to the <strong>Admin Panel → Resignations</strong> to accept or decline this resignation request.
    </p>
  </div>
</div>"""
        try:
            send_email_smtp(
                config.get("from_email", config["user"]),
                f"Resignation Notice — {emp_name} (Last day: {last_working_day})",
                html_body, config
            )
        except Exception as e:
            print(f"[EMAIL ERROR] Resignation notification failed: {e}")

    return redirect("/employee_portal?resigned=1#resign")


@app.route("/resignation_requests")
@admin_required
def resignation_requests_view():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT rr.id, e.name, rr.employee_id, rr.last_working_day, rr.reason, rr.status, rr.created_at
        FROM resignation_requests rr
        JOIN employees e ON rr.employee_id = e.employee_id
        ORDER BY FIELD(rr.status, 'Pending', 'Accepted', 'Declined'), rr.created_at DESC
    """)
    resignations = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("resignation_requests.html", resignations=resignations)


@app.route("/resignation_action/<int:rid>", methods=["POST"])
@admin_required
def resignation_action(rid):
    action = request.form.get("action", "")
    if action in ("Accepted", "Declined"):
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE resignation_requests SET status=%s WHERE id=%s", (action, rid))
        db.commit()
        cursor.close(); db.close()
    return redirect("/resignation_requests")


# ================================================================
#  TICKETS  (web)
# ================================================================

@app.route("/raise_ticket", methods=["POST"])
@employee_required
def raise_ticket():
    emp_id      = session["employee_id"]
    category    = request.form.get("category", "").strip()
    subject     = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()
    priority    = request.form.get("priority", "Medium").strip()
    if not category or not subject or not description:
        return redirect("/employee_portal#tickets")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO tickets (employee_id, category, subject, description, priority) "
        "VALUES (%s,%s,%s,%s,%s)",
        (emp_id, category, subject, description, priority)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal?ticket_sent=1#tickets")


@app.route("/tickets")
@admin_required
def tickets_view():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT t.id, t.employee_id, e.name, t.category, t.subject, t.description,
               t.priority, t.status, t.admin_response, t.created_at, t.updated_at
        FROM tickets t
        JOIN employees e ON t.employee_id = e.employee_id
        ORDER BY FIELD(t.status,'Open','In Progress','Resolved','Closed'),
                 FIELD(t.priority,'High','Medium','Low'), t.created_at DESC
    """)
    all_tickets = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.close(); db.close()
    return render_template("tickets.html",
        all_tickets=all_tickets,
        pending_tickets=pending_tickets,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        today=datetime.date.today().strftime("%d %b %Y"),
        shift_start=SHIFT_START.strftime("%I:%M %p"),
        shift_end=SHIFT_END.strftime("%I:%M %p"),
    )


@app.route("/ticket_action/<int:tid>", methods=["POST"])
@admin_required
def ticket_action(tid):
    new_status     = request.form.get("status", "").strip()
    admin_response = request.form.get("admin_response", "").strip()
    allowed = ("Open", "In Progress", "Resolved", "Closed")
    if new_status not in allowed:
        return redirect("/tickets")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE tickets SET status=%s, admin_response=%s WHERE id=%s",
        (new_status, admin_response or None, tid)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/tickets")


# ================================================================
#  REST API  (used by the Flutter mobile app)
# ================================================================

def api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        token = auth[7:]
        if token not in _api_tokens:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/login", methods=["POST"])
def api_login():
    data     = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT password FROM admin_users WHERE username=%s", (username,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if row and check_password_hash(row[0], password):
        token = secrets.token_hex(32)
        _api_tokens[token] = username
        return jsonify({"ok": True, "token": token, "username": username})
    return jsonify({"ok": False, "msg": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        _api_tokens.pop(auth[7:], None)
    return jsonify({"ok": True})


@app.route("/api/dashboard", methods=["GET"])
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
    cursor.close(); db.close()

    return jsonify({
        "ok": True, "total": total, "present": present,
        "absent": total - present, "late": late,
        "today": today.strftime("%d %b %Y"), "today_rows": today_rows,
        "pending_leaves": pending_leaves, "pending_resignations": pending_resignations,
        "pending_tickets": pending_tickets,
    })


@app.route("/api/employees", methods=["GET"])
@api_required
def api_employees():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, e.email, COALESCE(s.salary_per_day, 0)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "employees": [
        {"employee_id": r[0], "name": r[1], "email": r[2], "salary_per_day": float(r[3])}
        for r in rows
    ]})


@app.route("/api/employees", methods=["POST"])
@api_required
def api_register_employee():
    name   = request.form.get("name", "").strip()
    emp_id = request.form.get("emp_id", "").strip()
    email  = request.form.get("email", "").strip() or None
    file   = request.files.get("face")
    if not name or not emp_id or not file:
        return jsonify({"ok": False, "msg": "name, emp_id and face image required"}), 400
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)
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
            "INSERT INTO employees (name, employee_id, email, face_image, qr_code, password) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (name, emp_id, email, filepath, qr_path, hashed_pwd)
        )
        db.commit()
    except Exception as e:
        db.rollback(); cursor.close(); db.close()
        return jsonify({"ok": False, "msg": str(e)}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee {name} registered."})


@app.route("/api/employees/<emp_id>", methods=["GET"])
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


@app.route("/api/employees/<emp_id>", methods=["PUT"])
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


@app.route("/api/employees/<emp_id>", methods=["DELETE"])
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
            except: pass
    for tbl in ("attendance", "salary_config", "leave_requests",
                "resignation_requests", "tickets", "employees"):
        cursor.execute(f"DELETE FROM {tbl} WHERE employee_id=%s", (emp_id,))
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee '{emp_id}' deleted."})


@app.route("/api/holidays", methods=["GET"])
@api_required
def api_holidays():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT date, name FROM holidays ORDER BY date")
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "holidays": [{"date": str(r[0]), "name": r[1]} for r in rows]})


@app.route("/api/holidays", methods=["POST"])
@api_required
def api_add_holiday():
    data = request.get_json() or {}
    date = data.get("date"); name = data.get("name")
    if not date or not name:
        return jsonify({"ok": False, "msg": "date and name required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute("INSERT INTO holidays (date, name) VALUES (%s,%s)", (date, name))
        db.commit()
    except Exception as e:
        db.rollback(); cursor.close(); db.close()
        return jsonify({"ok": False, "msg": str(e)}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True})


@app.route("/api/salary_config", methods=["GET"])
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


@app.route("/api/salary_config", methods=["POST"])
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


@app.route("/api/monthly_report", methods=["GET"])
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


@app.route("/api/salary_report", methods=["GET"])
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


@app.route("/api/email_config", methods=["GET"])
@api_required
def api_get_email_config():
    cfg = get_email_config()
    return jsonify({"ok": True, "config": cfg})


@app.route("/api/email_config", methods=["POST"])
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
        (host, port, user, password, from_name)
    )
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@app.route("/api/send_salary_email", methods=["POST"])
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
    try:
        send_email_smtp(email, f"Salary Slip - {month_name}", html_body, config)
        return jsonify({"ok": True, "msg": f"Sent to {email}"})
    except Exception as ex:
        return jsonify({"ok": False, "msg": str(ex)})


@app.route("/api/attendance/checkin", methods=["POST"])
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
        "SELECT login_time, logout_time, status FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record             = cursor.fetchone()
    login_time         = record[0] if record else None
    logout_time        = record[1] if record else None
    login_status_stored= record[2] if record else None
    if not login_time:
        if current_time <= SHIFT_START:
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
        if current_time < SHIFT_HALF:
            logout_status = "Half Day Logout"
        elif current_time < SHIFT_END:
            logout_status = "Early Logout"
        else:
            logout_status = "Completed"
        att_type = get_attendance_type(login_status_stored, logout_status)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, logout_status, att_type, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "type": "logout", "name": employee_name,
                        "status": logout_status, "att_type": att_type,
                        "time": current_time.strftime("%H:%M:%S")})
    else:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Attendance already completed for today."})


# ---------------- API: LEAVE REQUESTS ----------------

@app.route("/api/leave_requests", methods=["GET"])
@api_required
def api_leave_requests():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT lr.id, lr.employee_id, e.name, lr.leave_date, lr.reason, lr.status, lr.created_at AS requested_at
        FROM leave_requests lr
        JOIN employees e ON lr.employee_id = e.employee_id
        ORDER BY lr.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "leaves": [
        {"id": r[0], "employee_id": r[1], "name": r[2],
         "leave_date": str(r[3]) if r[3] else None,
         "reason": r[4], "status": r[5],
         "requested_at": str(r[6]) if r[6] else None}
        for r in rows
    ]})


@app.route("/api/leave_requests/<int:lid>/action", methods=["POST"])
@api_required
def api_leave_action(lid):
    data = request.get_json(silent=True) or {}
    action = data.get("action", "").strip()
    if action not in ("Approved", "Declined"):
        return jsonify({"ok": False, "msg": "action must be Approved or Declined"}), 400
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE leave_requests SET status=%s WHERE id=%s", (action, lid))
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "status": action})


# ---------------- API: RESIGNATION REQUESTS ----------------

@app.route("/api/resignation_requests", methods=["GET"])
@api_required
def api_resignation_requests():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT rr.id, rr.employee_id, e.name, rr.last_working_day, rr.reason, rr.status, rr.created_at AS requested_at
        FROM resignation_requests rr
        JOIN employees e ON rr.employee_id = e.employee_id
        ORDER BY rr.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "resignations": [
        {"id": r[0], "employee_id": r[1], "name": r[2],
         "last_working_day": str(r[3]) if r[3] else None,
         "reason": r[4], "status": r[5],
         "requested_at": str(r[6]) if r[6] else None}
        for r in rows
    ]})


@app.route("/api/resignation_requests/<int:rid>/action", methods=["POST"])
@api_required
def api_resignation_action(rid):
    data = request.get_json(silent=True) or {}
    action = data.get("action", "").strip()
    if action not in ("Accepted", "Declined"):
        return jsonify({"ok": False, "msg": "action must be Accepted or Declined"}), 400
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE resignation_requests SET status=%s WHERE id=%s", (action, rid))
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "status": action})


# ── Employee API token store  { token → employee_id } ──
_emp_api_tokens: dict = {}


def employee_api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        token = auth[7:]
        if token not in _emp_api_tokens:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/employee/login", methods=["POST"])
def api_employee_login():
    data   = request.get_json() or {}
    emp_id = data.get("employee_id", "").strip()
    if not emp_id:
        return jsonify({"ok": False, "msg": "employee_id required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name, email FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    token = secrets.token_hex(32)
    _emp_api_tokens[token] = emp_id
    return jsonify({"ok": True, "token": token, "employee_id": emp_id,
                    "name": row[0], "email": row[1]})


@app.route("/api/employee/logout", methods=["POST"])
def api_employee_logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        _emp_api_tokens.pop(auth[7:], None)
    return jsonify({"ok": True})


def _fmt_t(t):
    if t is None: return None
    if hasattr(t, 'strftime'): return t.strftime("%H:%M:%S")
    total = int(t.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)


@app.route("/api/employee/portal", methods=["GET"])
@employee_api_required
def api_employee_portal():
    token  = request.headers.get("Authorization", "")[7:]
    emp_id = _emp_api_tokens[token]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()

    cursor.execute("SELECT name, email FROM employees WHERE employee_id=%s", (emp_id,))
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
    cursor.close(); db.close()

    return jsonify({
        "ok": True,
        "employee_id": emp_id,
        "name": emp[0] if emp else emp_id,
        "email": emp[1] if emp else None,
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
    })


@app.route("/api/employee/checkin", methods=["POST"])
@employee_api_required
def api_employee_checkin():
    token  = request.headers.get("Authorization", "")[7:]
    emp_id = _emp_api_tokens[token]
    data   = request.get_json() or {}
    lat    = data.get("lat")
    lon    = data.get("lon")

    OFFICE_LAT = 17.49375
    OFFICE_LON = 78.40435
    if lat and lon:
        if not is_within_range(float(lat), float(lon), OFFICE_LAT, OFFICE_LON):
            return jsonify({"ok": False, "msg": "You are outside the office premises."})

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
    result = cursor.fetchone()
    employee_name = result[0] if result else emp_id

    now          = datetime.datetime.now()
    today        = now.date()
    current_time = now.time()

    cursor.execute(
        "SELECT login_time, logout_time, status FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    record       = cursor.fetchone()
    login_time   = record[0] if record else None
    logout_time  = record[1] if record else None
    login_status = record[2] if record else None

    if not login_time:
        if current_time <= SHIFT_START:
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
        if current_time < SHIFT_HALF:
            out_status = "Half Day Logout"
        elif current_time < SHIFT_END:
            out_status = "Early Logout"
        else:
            out_status = "Completed"
        att_type = get_attendance_type(login_status, out_status)
        cursor.execute(
            "UPDATE attendance SET logout_time=%s, logout_status=%s, attendance_type=%s "
            "WHERE employee_id=%s AND date=%s",
            (current_time, out_status, att_type, emp_id, today)
        )
        db.commit(); cursor.close(); db.close()
        return jsonify({"ok": True, "action": "logout", "name": employee_name,
                        "status": out_status, "att_type": att_type,
                        "time": current_time.strftime("%H:%M:%S")})
    else:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Attendance already completed for today."})


@app.route("/api/employee/leave_request", methods=["POST"])
@employee_api_required
def api_employee_leave_request():
    token      = request.headers.get("Authorization", "")[7:]
    emp_id     = _emp_api_tokens[token]
    data       = request.get_json() or {}
    leave_date = data.get("leave_date", "").strip()
    reason     = data.get("reason", "").strip()
    if not leave_date or not reason:
        return jsonify({"ok": False, "msg": "leave_date and reason required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO leave_requests (employee_id, leave_date, reason) VALUES (%s,%s,%s)",
        (emp_id, leave_date, reason)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Leave request submitted."})


@app.route("/api/employee/resign", methods=["POST"])
@employee_api_required
def api_employee_resign():
    token            = request.headers.get("Authorization", "")[7:]
    emp_id           = _emp_api_tokens[token]
    data             = request.get_json() or {}
    last_working_day = data.get("last_working_day", "").strip()
    reason           = data.get("reason", "").strip()
    if not last_working_day or not reason:
        return jsonify({"ok": False, "msg": "last_working_day and reason required"}), 400
    try:
        lwd = datetime.datetime.strptime(last_working_day, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid date format. Use YYYY-MM-DD"}), 400
    min_lwd = datetime.date.today() + datetime.timedelta(days=30)
    if lwd < min_lwd:
        return jsonify({"ok": False, "msg": "Last working day must be at least 30 days from today"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
    emp = cursor.fetchone()
    emp_name = emp[0] if emp else emp_id
    cursor.execute(
        "INSERT INTO resignation_requests (employee_id, last_working_day, reason) VALUES (%s,%s,%s)",
        (emp_id, last_working_day, reason)
    )
    db.commit()
    config = get_email_config()
    if config:
        html_body = (
            f'<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;'
            f'border-radius:12px;overflow:hidden;">'
            f'<div style="background:linear-gradient(135deg,#ef4444,#b91c1c);padding:24px;color:white;text-align:center;">'
            f'<h2 style="margin:0;">⚠️ Resignation Notice Received</h2></div>'
            f'<div style="padding:24px;"><table style="width:100%;border-collapse:collapse;font-size:14px;">'
            f'<tr><td style="padding:10px;color:#555;font-weight:600;">Employee</td><td style="padding:10px;">{emp_name}</td></tr>'
            f'<tr><td style="padding:10px;color:#555;font-weight:600;">ID</td><td style="padding:10px;">{emp_id}</td></tr>'
            f'<tr><td style="padding:10px;color:#555;font-weight:600;">Last Working Day</td><td style="padding:10px;">{last_working_day}</td></tr>'
            f'<tr><td style="padding:10px;color:#555;font-weight:600;">Reason</td><td style="padding:10px;">{reason}</td></tr>'
            f'</table></div></div>'
        )
        try:
            send_email_smtp(
                config.get("from_email", config["user"]),
                f"Resignation Notice — {emp_name} (Last day: {last_working_day})",
                html_body, config
            )
        except Exception as e:
            print(f"[EMAIL ERROR] Resignation notification failed: {e}")
    cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Resignation submitted successfully."})


# ---------------- API: TICKETS (employee) ----------------

@app.route("/api/employee/tickets", methods=["GET"])
@employee_api_required
def api_employee_tickets():
    token  = request.headers.get("Authorization", "")[7:]
    emp_id = _emp_api_tokens[token]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT id, category, subject, description, priority, status, admin_response, created_at
        FROM tickets WHERE employee_id=%s ORDER BY created_at DESC LIMIT 30
    """, (emp_id,))
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "tickets": [
        {"id": r[0], "category": r[1], "subject": r[2], "description": r[3],
         "priority": r[4], "status": r[5], "admin_response": r[6],
         "created_at": str(r[7])}
        for r in rows
    ]})


@app.route("/api/employee/raise_ticket", methods=["POST"])
@employee_api_required
def api_employee_raise_ticket():
    token       = request.headers.get("Authorization", "")[7:]
    emp_id      = _emp_api_tokens[token]
    data        = request.get_json() or {}
    category    = data.get("category", "").strip()
    subject     = data.get("subject", "").strip()
    description = data.get("description", "").strip()
    priority    = data.get("priority", "Medium").strip()
    if not category or not subject or not description:
        return jsonify({"ok": False, "msg": "category, subject and description required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO tickets (employee_id, category, subject, description, priority) VALUES (%s,%s,%s,%s,%s)",
        (emp_id, category, subject, description, priority)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Ticket raised successfully."})


@app.route("/api/employee/change_password", methods=["POST"])
@employee_api_required
def api_employee_change_password():
    token  = request.headers.get("Authorization", "")[7:]
    emp_id = _emp_api_tokens[token]
    data   = request.get_json() or {}
    new_pw = data.get("new_password", "").strip()
    if not new_pw:
        return jsonify({"ok": False, "msg": "new_password required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET password=%s WHERE employee_id=%s",
                   (generate_password_hash(new_pw), emp_id))
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Password changed successfully."})


@app.route("/api/employee/salary", methods=["GET"])
@employee_api_required
def api_employee_salary():
    import calendar as cal
    token  = request.headers.get("Authorization", "")[7:]
    emp_id = _emp_api_tokens[token]
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
    cursor.execute("SELECT date FROM holidays WHERE MONTH(date)=%s AND YEAR(date)=%s", (month, year))
    holiday_set = {r[0] for r in cursor.fetchall()}
    _, days_in_month = cal.monthrange(year, month)
    billable = sum(
        1 for d in range(1, days_in_month + 1)
        if datetime.date(year, month, d).weekday() < 5
        and datetime.date(year, month, d) not in holiday_set
    )
    cursor.execute("""
        SELECT attendance_type FROM attendance
        WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s
    """, (emp_id, month, year))
    att_rows = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*) FROM leave_requests
        WHERE employee_id=%s AND MONTH(leave_date)=%s AND YEAR(leave_date)=%s AND status='Approved'
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


# ---------------- API: TICKETS (admin) ----------------

@app.route("/api/tickets", methods=["GET"])
@api_required
def api_tickets():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT t.id, t.employee_id, e.name, t.category, t.subject, t.description,
               t.priority, t.status, t.admin_response, t.created_at, t.updated_at
        FROM tickets t
        JOIN employees e ON t.employee_id = e.employee_id
        ORDER BY FIELD(t.status,'Open','In Progress','Resolved','Closed'),
                 FIELD(t.priority,'High','Medium','Low'), t.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "tickets": [
        {"id": r[0], "employee_id": r[1], "name": r[2], "category": r[3],
         "subject": r[4], "description": r[5], "priority": r[6],
         "status": r[7], "admin_response": r[8],
         "created_at": str(r[9]), "updated_at": str(r[10])}
        for r in rows
    ]})


@app.route("/api/tickets/<int:tid>/action", methods=["POST"])
@api_required
def api_ticket_action(tid):
    data           = request.get_json(silent=True) or {}
    new_status     = data.get("status", "").strip()
    admin_response = data.get("admin_response", "").strip()
    allowed = ("Open", "In Progress", "Resolved", "Closed")
    if new_status not in allowed:
        return jsonify({"ok": False, "msg": f"status must be one of {allowed}"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE tickets SET status=%s, admin_response=%s WHERE id=%s",
        (new_status, admin_response or None, tid)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True, "status": new_status})


# ---------------- PAY SLIPS ----------------
@app.route("/view_payslip/<emp_id>/<int:year>/<int:month>")
def view_payslip(emp_id, year, month):
    is_admin = session.get("admin_logged_in")
    is_own   = session.get("employee_id") == emp_id
    if not is_admin and not is_own:
        return redirect("/employee_login")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT e.name, e.email, COALESCE(s.salary_per_day, 0) "
        "FROM employees e LEFT JOIN salary_config s ON e.employee_id = s.employee_id "
        "WHERE e.employee_id = %s",
        (emp_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return "Employee not found", 404
    name, email, spd = row

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

    month_name = calendar.month_name[month] + f" {year}"
    return build_salary_slip_html(name, emp_id, email, month_name, year, month, entry)


@app.route("/admin_payslips")
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
    )


# ---------------- API: SHIFTS (JSON) ----------------

@app.route("/api/shifts", methods=["GET"])
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


@app.route("/api/shifts", methods=["POST"])
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
            "INSERT INTO shifts (name, start_time, half_time, end_time) VALUES (%s,%s,%s,%s)",
            (name, start, half, end)
        )
        db.commit()
        sid = cursor.lastrowid
    except Exception as e:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": str(e)}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True, "id": sid})


@app.route("/api/shifts/<int:sid>", methods=["DELETE"])
@api_required
def api_shifts_delete(sid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET shift_id=NULL WHERE shift_id=%s", (sid,))
    cursor.execute("DELETE FROM shifts WHERE id=%s", (sid,))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"ok": True})


@app.route("/api/shifts/assign", methods=["POST"])
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



# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
