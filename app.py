from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
from flask_cors import CORS
import cv2
import datetime
import face_recognition
from database import get_db_connection
from qr_generator import generate_qr
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os
import math
import calendar
import mysql.connector
import smtplib
import ssl
import secrets
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

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
app.secret_key = "super-secret-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = 1800

UPLOAD_FOLDER = "dataset"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
            password VARCHAR(255) NOT NULL
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
    db.commit()

    # Migrations for existing installs
    for sql in [
        "ALTER TABLE attendance ADD COLUMN logout_status VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE attendance ADD COLUMN attendance_type VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN role VARCHAR(100) DEFAULT NULL",
    ]:
        try:
            cursor.execute(sql)
            db.commit()
        except mysql.connector.errors.DatabaseError:
            db.rollback()

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
    if attendance_type == "Full Day":
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
    today    = datetime.date.today()
    holidays = fetch_holidays_set(year, month)
    return [d for d in get_working_days(year, month) if d not in holidays and d <= today]

# ---------------- EMAIL HELPERS ----------------
def get_email_config():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name FROM email_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    db.close()
    if row:
        return {"host": row[0], "port": row[1], "user": row[2], "password": row[3], "from_name": row[4]}
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
  .att-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }}
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

def send_email_smtp(to_email, subject, html_body, config):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{config['from_name']} <{config['user']}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(config["user"], config["password"])
        server.sendmail(config["user"], to_email, msg.as_string())

def compute_salary_entry(emp_id, name, spd, att_map, billable_past):
    emp_att = att_map.get(emp_id, {})
    full_days = half_days = late_days = absent_days = 0

    for d in billable_past:
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

    spd_f      = float(spd)
    full_earn  = round(full_days  * spd_f, 2)
    late_earn  = round(late_days  * spd_f * (1 - LATE_DEDUCTION_RATE), 2)
    half_earn  = round(half_days  * spd_f * (1 - HALF_DAY_RATE), 2)
    net        = round(full_earn + late_earn + half_earn, 2)
    gross      = round(spd_f * len(billable_past), 2)
    deduction  = round(gross - net, 2)

    return {
        "emp_id":     emp_id,
        "name":       name,
        "spd":        round(spd_f, 2),
        "billable":   len(billable_past),
        "full_days":  full_days,
        "half_days":  half_days,
        "late_days":  late_days,
        "absent":     absent_days,
        "full_earn":  full_earn,
        "late_earn":  late_earn,
        "half_earn":  half_earn,
        "gross":      gross,
        "absent_ded": round(absent_days * spd_f, 2),
        "half_ded":   round(half_days   * spd_f * HALF_DAY_RATE, 2),
        "late_ded":   round(late_days   * spd_f * LATE_DEDUCTION_RATE, 2),
        "deduction":  deduction,
        "net":        net,
    }

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
        if username == "admin" and password == "admin@123":
            session["admin_logged_in"] = True
            session.permanent = True
            return redirect("/admin")
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
    )

# ---------------- ADMIN ACTIONS ----------------
@app.route("/admin_action", methods=["POST"])
@admin_required
def admin_action():
    action = request.form.get("action")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    if action == "register":
        name     = request.form["name"]
        emp_id   = request.form["emp_id"]
        email    = request.form.get("email", "").strip() or None
        role     = request.form.get("role", "").strip() or None
        file     = request.files["face"]
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
        file.save(filepath)
        qr_path  = generate_qr(emp_id)
        cursor.execute(
            "INSERT INTO employees (name, employee_id, email, role, face_image, qr_code) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, emp_id, email, role, filepath, qr_path)
        )
        db.commit()

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

# ---------------- VIEW HOLIDAYS ----------------
@app.route("/view_holidays")
@admin_required
def view_holidays():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT * FROM holidays ORDER BY date")
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("holidays.html", holidays=data)

@app.route("/add_holiday", methods=["POST"])
@admin_required
def add_holiday():
    date         = request.form["date"]
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
    return redirect("/view_holidays")

@app.route("/delete_holiday/<int:hid>", methods=["POST"])
@admin_required
def delete_holiday(hid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM holidays WHERE id=%s", (hid,))
    db.commit()
    cursor.close()
    db.close()
    return redirect("/view_holidays")

# ---------------- VIEW SALARY CONFIG ----------------
@app.route("/view_salary")
@admin_required
def view_salary():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0), e.role
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
    emp_id = request.form["emp_id"]
    salary = request.form["salary"]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT 1 FROM salary_config WHERE employee_id=%s", (emp_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE salary_config SET salary_per_day=%s WHERE employee_id=%s", (salary, emp_id))
    else:
        cursor.execute("INSERT INTO salary_config (employee_id, salary_per_day) VALUES (%s,%s)", (emp_id, salary))
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

    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
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

# ---------------- SALARY REPORT ----------------
@app.route("/salary_report")
@admin_required
def salary_report():
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
        FROM attendance
        WHERE date BETWEEN %s AND %s
    """, (datetime.date(year, month, 1), datetime.date(year, month, last_day)))

    att_map = {}
    for row in cursor.fetchall():
        att_map.setdefault(row[0], {})[row[1]] = row

    billable_past = get_billable_past_days(year, month)
    cursor.close()
    db.close()

    salary_data = []
    for emp_id, name, email, spd in employees:
        entry = compute_salary_entry(emp_id, name, spd, att_map, billable_past)
        entry["email"] = email
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
        host      = request.form["smtp_host"].strip()
        port      = int(request.form["smtp_port"])
        user      = request.form["smtp_user"].strip()
        password  = request.form["smtp_pass"].strip()
        from_name = request.form.get("from_name", "HR Department").strip()

        cursor.execute("DELETE FROM email_config")
        cursor.execute(
            "INSERT INTO email_config (smtp_host, smtp_port, smtp_user, smtp_pass, from_name) VALUES (%s,%s,%s,%s,%s)",
            (host, port, user, password, from_name)
        )
        db.commit()
        cursor.close()
        db.close()
        return redirect("/email_config?saved=1")

    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name FROM email_config ORDER BY id DESC LIMIT 1")
    row    = cursor.fetchone()
    config = {"host": row[0], "port": row[1], "user": row[2], "password": row[3], "from_name": row[4]} if row else None
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

    cursor.close(); db.close()

    billable_past = get_billable_past_days(year, month)
    entry         = compute_salary_entry(emp_id, name, spd, att_map, billable_past)
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

    cursor.close(); db.close()

    billable_past = get_billable_past_days(year, month)
    month_name    = datetime.date(year, month, 1).strftime("%B %Y")

    sent = skipped = failed = 0
    errors = []

    for emp_id, name, email, spd in employees:
        if not email:
            skipped += 1
            continue
        entry     = compute_salary_entry(emp_id, name, spd, att_map, billable_past)
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
    return (R * c) <= 30

# ---------------- ATTENDANCE (LOGIN + LOGOUT) ----------------
@app.route("/attendance")
def attendance():
    OFFICE_LAT = 17.494664737165042
    OFFICE_LON = 78.40496618113566

    user_lat = session.get("lat")
    user_lon = session.get("lon")

    if not user_lat or not user_lon:
        return jsonify({"ok": False, "msg": "Location not captured. Please allow location access."})

    if not is_within_range(float(user_lat), float(user_lon), OFFICE_LAT, OFFICE_LON):
        return jsonify({"ok": False, "msg": "You are outside the office premises."})

    cap = None
    db  = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return jsonify({"ok": False, "msg": "Camera not accessible."})

        detector       = cv2.QRCodeDetector()
        qr_employee_id = None

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            data, _, _ = detector.detectAndDecode(frame)
            cv2.putText(frame, "Show QR Code", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            if data:
                qr_employee_id = data.strip()
                break
            cv2.imshow("QR Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return jsonify({"ok": False, "msg": "Scanner closed."})

        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT face_image, name FROM employees WHERE employee_id=%s",
            (qr_employee_id,)
        )
        result = cursor.fetchone()

        if not result:
            return jsonify({"ok": False, "msg": "Employee not found."})

        face_path, employee_name = result

        if not os.path.exists(face_path):
            return jsonify({"ok": False, "msg": "Face image missing for this employee. Please re-register."})

        known_image = face_recognition.load_image_file(face_path)
        enc         = face_recognition.face_encodings(known_image)
        if not enc:
            return jsonify({"ok": False, "msg": "Stored face image is invalid."})

        known_encoding = enc[0]

        now          = datetime.datetime.now()
        today        = now.date()
        current_time = now.time()

        cursor.execute(
            "SELECT login_time, logout_time, status FROM attendance WHERE employee_id=%s AND date=%s",
            (qr_employee_id, today)
        )
        record              = cursor.fetchone()
        login_time          = record[0] if record else None
        logout_time         = record[1] if record else None
        login_status_stored = record[2] if record else None

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locs)

            for face_enc, _ in zip(encs, locs):
                if True in face_recognition.compare_faces([known_encoding], face_enc):

                    if not login_time:
                        if current_time <= SHIFT_START:
                            login_status = "Full Day Login"
                        elif current_time <= SHIFT_HALF:
                            login_status = "Late Login"
                        else:
                            login_status = "Half Day Login"

                        cursor.execute(
                            "INSERT INTO attendance (employee_id, date, login_time, status) "
                            "VALUES (%s,%s,%s,%s)",
                            (qr_employee_id, today, current_time, login_status)
                        )
                        db.commit()

                        return jsonify({
                            "ok":     True,
                            "type":   "login",
                            "name":   employee_name,
                            "status": login_status,
                            "time":   current_time.strftime("%H:%M:%S"),
                        })

                    elif not logout_time:
                        if current_time < SHIFT_HALF:
                            logout_status = "Half Day Logout"
                        elif current_time < SHIFT_END:
                            logout_status = "Early Logout"
                        else:
                            logout_status = "Completed"

                        att_type = get_attendance_type(login_status_stored, logout_status)

                        cursor.execute(
                            "UPDATE attendance "
                            "SET logout_time=%s, logout_status=%s, attendance_type=%s "
                            "WHERE employee_id=%s AND date=%s",
                            (current_time, logout_status, att_type, qr_employee_id, today)
                        )
                        db.commit()

                        return jsonify({
                            "ok":       True,
                            "type":     "logout",
                            "name":     employee_name,
                            "status":   logout_status,
                            "att_type": att_type,
                            "time":     current_time.strftime("%H:%M:%S"),
                        })

                    else:
                        return jsonify({"ok": False, "msg": "Attendance already completed for today."})

            cv2.imshow("Face Verification", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        return jsonify({"ok": False, "msg": "Face verification failed."})

    except Exception as e:
        return jsonify({"ok": False, "msg": "Scanner error: " + str(e)})
    finally:
        try:
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()
        except Exception:
            pass

# ================================================================
#  EMPLOYEE PORTAL
# ================================================================

@app.route("/employee_login", methods=["GET", "POST"])
def employee_login():
    if session.get("employee_id"):
        return redirect("/employee_portal")
    if request.method == "POST":
        emp_id = request.form["emp_id"].strip()
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT employee_id, name, role FROM employees WHERE employee_id=%s",
            (emp_id,)
        )
        row = cursor.fetchone()
        cursor.close(); db.close()
        if row:
            session["employee_id"]   = row[0]
            session["employee_name"] = row[1]
            session["employee_role"] = row[2] or ""
            session.permanent = True
            return redirect("/employee_portal")
        return render_template("employee_login.html", error="Employee ID not found.")
    return render_template("employee_login.html")


@app.route("/employee_logout")
def employee_logout():
    session.pop("employee_id", None)
    session.pop("employee_name", None)
    session.pop("employee_role", None)
    return redirect("/employee_login")


@app.route("/employee_portal")
@employee_required
def employee_portal():
    emp_id = session["employee_id"]
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute(
        "SELECT employee_id, name, role, email FROM employees WHERE employee_id=%s",
        (emp_id,)
    )
    emp = cursor.fetchone()

    today = datetime.date.today()
    cursor.execute(
        "SELECT login_time, logout_time, status, logout_status, attendance_type "
        "FROM attendance WHERE employee_id=%s AND date=%s",
        (emp_id, today)
    )
    today_att = cursor.fetchone()

    year  = today.year
    month = today.month
    _, last_day = calendar.monthrange(year, month)
    cursor.execute("""
        SELECT date, login_time, logout_time, status, logout_status, attendance_type
        FROM attendance
        WHERE employee_id=%s AND date BETWEEN %s AND %s
        ORDER BY date DESC
    """, (emp_id, datetime.date(year, month, 1), datetime.date(year, month, last_day)))
    monthly_att = cursor.fetchall()

    billable_past = get_billable_past_days(year, month)
    att_by_date   = {r[0]: r for r in monthly_att}
    full_days = half_days = late_days = absent_days = 0
    for d in billable_past:
        row = att_by_date.get(d)
        if row:
            _, login_t, logout_t, status, _ls, att_type = row
            final = att_type if att_type else infer_type_legacy(status, login_t, logout_t)
            if   final == "Full Day":               full_days   += 1
            elif final == "Late - Full Day":        late_days   += 1
            elif final in ("Half Day", "Present"):  half_days   += 1
            else:                                   absent_days += 1
        else:
            absent_days += 1

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

    cursor.close(); db.close()

    return render_template("employee_portal.html",
        emp=emp,
        today=today.strftime("%d %b %Y"),
        today_att=today_att,
        monthly_att=monthly_att,
        full_days=full_days, late_days=late_days,
        half_days=half_days, absent_days=absent_days,
        billable=len(billable_past),
        my_leaves=my_leaves,
        my_resignation=my_resignation,
        my_tickets=my_tickets,
        leave_sent=request.args.get("leave_sent") == "1",
        resigned=request.args.get("resigned") == "1",
        ticket_sent=request.args.get("ticket_sent") == "1",
        month_name=today.strftime("%B %Y"),
    )


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
                config["user"],
                f"Leave Request — {emp_name} ({leave_date})",
                html_body, config
            )
        except Exception:
            pass

    return redirect("/employee_portal?leave_sent=1")


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
                config["user"],
                f"Resignation Notice — {emp_name} (Last day: {last_working_day})",
                html_body, config
            )
        except Exception:
            pass

    return redirect("/employee_portal?resigned=1")


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
    # Hard-coded admin shortcut
    if username == "admin" and password == "admin@123":
        token = secrets.token_hex(32)
        _api_tokens[token] = username
        return jsonify({"ok": True, "token": token, "username": username})
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
    cursor.close(); db.close()

    return jsonify({
        "ok": True, "total": total, "present": present,
        "absent": total - present, "late": late,
        "today": today.strftime("%d %b %Y"), "today_rows": today_rows,
        "pending_leaves": pending_leaves, "pending_resignations": pending_resignations,
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
    qr_path  = generate_qr(emp_id)
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    try:
        cursor.execute(
            "INSERT INTO employees (name, employee_id, email, face_image, qr_code) VALUES (%s,%s,%s,%s,%s)",
            (name, emp_id, email, filepath, qr_path)
        )
        db.commit()
    except Exception as e:
        db.rollback(); cursor.close(); db.close()
        return jsonify({"ok": False, "msg": str(e)}), 400
    cursor.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee {name} registered."})


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
                if final == "Full Day": full_days += 1
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
    OFFICE_LAT = 17.494664737165042
    OFFICE_LON = 78.40496618113566
    if lat and lon:
        if not is_within_range(float(lat), float(lon), OFFICE_LAT, OFFICE_LON):
            return jsonify({"ok": False, "msg": "You are outside the office premises."})
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found."})
    employee_name = result[0]
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

    OFFICE_LAT = 17.494664737165042
    OFFICE_LON = 78.40496618113566
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
                config["user"],
                f"Resignation Notice — {emp_name} (Last day: {last_working_day})",
                html_body, config
            )
        except Exception:
            pass
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


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
