from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import cv2
import uuid
from werkzeug.utils import secure_filename
import datetime
import html as _html
import face_recognition
from database import get_db_connection
from qr_generator import generate_qr
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash as _gen_pw_hash
def generate_password_hash(pw, **kw):
    return _gen_pw_hash(pw, method='pbkdf2:sha256')
from functools import wraps
from contextlib import contextmanager
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
from werkzeug.exceptions import HTTPException
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv

load_dotenv()

import logging
import sys

# Structured logging
_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.setFormatter(logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","msg":%(message)s}'
))
app_log = logging.getLogger("attendance")
app_log.addHandler(_log_handler)
app_log.setLevel(logging.INFO)

# ── Startup: warn if critical env vars are missing ──
_missing_env = [k for k in ("DB_HOST", "DB_USER", "DB_PASS", "DB_NAME") if not os.environ.get(k)]
if _missing_env:
    import warnings
    warnings.warn(
        f"Missing required environment variables: {', '.join(_missing_env)}. "
        "Copy .env.example to .env and fill in the values.",
        stacklevel=2
    )

app = Flask(__name__)
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
_allowed_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else "*"
CORS(app, resources={r"/api/*": {"origins": _allowed_origins}})

_REDIS_URL = os.environ.get("REDIS_URL", "memory://")
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=_REDIS_URL,
    default_limits=[],
)

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


@app.route("/healthz")
def healthz():
    """Health check for load balancers."""
    from database import get_db_connection as _hc_get_db
    try:
        conn = _hc_get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close(); conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 503


# Jinja2 filter: handles both datetime.time and datetime.timedelta from MySQL
@app.template_filter("fmt_time")
def fmt_time_filter(value):
    if value is None:
        return "--"
    if isinstance(value, str):
        return value
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
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("APP_ENV", "development") == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = 1800

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
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
    if request.method != "POST":
        return
    if request.path.startswith("/api/"):
        return  # API routes use Bearer-token auth
    if request.is_json:
        return  # JSON fetch requests can't be forged cross-site (CORS blocks custom headers)
    token = session.get("_csrf")
    submitted = (request.form.get("_csrf_token")
                 or request.headers.get("X-CSRF-Token")
                 or request.headers.get("X-CSRFToken"))
    if not token or not submitted or not secrets.compare_digest(str(token), str(submitted)):
        return jsonify({"ok": False, "msg": "Session expired. Please refresh and try again."}), 403


@app.before_request
def _resolve_tenant():
    """Determine the tenant database for this request and store it in g.tenant_db."""
    from flask import g as _g

    # Skip for static files and special paths
    skip_prefixes = ("/static/", "/healthz", "/create_org", "/super_admin")
    if any(request.path.startswith(p) for p in skip_prefixes):
        return

    # 1. Already resolved in this session
    if session.get("tenant_db"):
        _g.tenant_db = session["tenant_db"]
        return

    # 2. Subdomain resolution
    host = request.host.split(":")[0]  # strip port
    parts = host.split(".")
    if len(parts) >= 3:
        subdomain = parts[0]
        try:
            from database import get_master_db
            conn = get_master_db()
            cur = conn.cursor(buffered=True)
            cur.execute(
                "SELECT db_name FROM tenants WHERE subdomain=%s AND status='active'",
                (subdomain,)
            )
            row = cur.fetchone()
            cur.close(); conn.close()
            if row:
                _g.tenant_db = row[0]
                session["tenant_db"] = row[0]
                return
        except Exception:
            pass  # master DB not yet set up — fall through to default

    # 3. Default single-tenant fallback
    _g.tenant_db = os.environ.get("DB_NAME", "employee_attendance")


_CSRF_HEAD_RE = re.compile(rb'</head>', re.IGNORECASE)
_CSRF_BODY_RE = re.compile(rb'</body>', re.IGNORECASE)
_CSRF_SCRIPT  = (
    b'<script>(function(){'
    b'var m=document.querySelector(\'meta[name="csrf-token"]\');'
    b'if(!m)return;'
    b'window._csrfToken=function(){return m.content;};'
    b'var _of=window.fetch;'
    b'window.fetch=function(u,o){'
    b'o=o||{};'
    b'var mt=(o.method||"GET").toUpperCase();'
    b'if(mt==="POST"||mt==="PUT"||mt==="PATCH"||mt==="DELETE"){'
    b'if(o.headers instanceof Headers){'
    b'if(!o.headers.has("X-CSRF-Token"))o.headers.set("X-CSRF-Token",m.content);'
    b'}else{o.headers=Object.assign({},o.headers||{});'
    b'if(!o.headers["X-CSRF-Token"])o.headers["X-CSRF-Token"]=m.content;}}'
    b'return _of.call(this,u,o);};'
    b'document.addEventListener("DOMContentLoaded",function(){'
    b'document.querySelectorAll("form").forEach(function(f){'
    b'if(f.method.toLowerCase()==="post"&&!f.querySelector(\'[name="_csrf_token"]\')){'
    b'var i=document.createElement("input");'
    b'i.type="hidden";i.name="_csrf_token";i.value=m.content;'
    b'f.prepend(i);}});});})();</script>'
)

@app.after_request
def _inject_csrf_meta(response):
    """Inject CSRF meta tag and auto-inject script into every HTML page."""
    if response.status_code >= 300 or not response.content_type.startswith("text/html"):
        return response
    try:
        token = _csrf_token()
        meta  = f'<meta name="csrf-token" content="{token}" />'.encode()
        data  = response.get_data()
        data  = _CSRF_HEAD_RE.sub(meta + b'</head>', data, count=1)
        data  = _CSRF_BODY_RE.sub(_CSRF_SCRIPT + b'</body>', data, count=1)
        response.set_data(data)
    except Exception:
        pass
    return response

# ---------------- COMPANY SETTINGS ----------------
def get_company_settings():
    try:
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT company_name, company_tagline, company_logo, currency_symbol, timezone, setup_done, COALESCE(company_code,'') FROM company_settings LIMIT 1")
        row = cursor.fetchone()
        cursor.close(); db.close()
        if row:
            return {"company_name": row[0], "company_tagline": row[1],
                    "company_logo": row[2], "currency_symbol": row[3],
                    "company_code": row[6],
                    "timezone": row[4], "setup_done": bool(row[5])}
    except Exception:
        pass
    return {"company_name": "My Company", "company_tagline": "Employee Attendance System",
            "company_logo": None, "currency_symbol": "₹", "timezone": "Asia/Kolkata",
            "setup_done": False, "company_code": ""}

@app.context_processor
def inject_company():
    return {"co": get_company_settings()}

# Office location — read from .env so no restart needed for coord changes
OFFICE_LAT = float(os.environ.get("OFFICE_LAT", "17.494664737165042"))
OFFICE_LON = float(os.environ.get("OFFICE_LON", "78.40496618113566"))
OFFICE_RADIUS_M = 300   # metres — 300 m radius as per policy

# Shift timings (overridden by DB on startup via load_default_shift())
SHIFT_START = datetime.time(9, 0)    # Full Day Login cutoff
SHIFT_HALF  = datetime.time(13, 0)   # Half Day threshold
SHIFT_END   = datetime.time(18, 0)   # Full Day Logout cutoff

def load_default_shift():
    global SHIFT_START, SHIFT_HALF, SHIFT_END
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        cur.execute("SELECT shift_start, shift_half, shift_end FROM company_settings LIMIT 1")
        row = cur.fetchone()
        cur.close(); db.close()
        if row and row[0]:
            def _to_time(v):
                if isinstance(v, datetime.timedelta):
                    total = int(v.total_seconds())
                    return datetime.time(total // 3600, (total % 3600) // 60)
                if isinstance(v, datetime.time):
                    return v
                return datetime.time(9, 0)
            SHIFT_START = _to_time(row[0])
            SHIFT_HALF  = _to_time(row[1])
            SHIFT_END   = _to_time(row[2])
    except Exception:
        pass

# Deduction rates
LATE_DEDUCTION_RATE = 0.10   # 10% deduction for late login
HALF_DAY_RATE       = 0.50   # 50% deduction for half day

# ---------------- IMAGE UPLOAD VALIDATION ----------------
_ALLOWED_IMG_EXT  = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
_ALLOWED_IMG_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif'}

def _validate_image_file(file):
    """Return (ok, error_msg). Checks extension and MIME type before saving."""
    if not file or not file.filename:
        return False, "No file selected."
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_IMG_EXT:
        return False, f"Invalid file type '{ext}'. Only JPG, PNG, WEBP or BMP allowed."
    ct = (file.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in _ALLOWED_IMG_MIME:
        return False, f"Invalid content type '{ct}'. Only image files accepted."
    return True, ""


# ── PII Encryption ────────────────────────────────────────────────
# Set ENCRYPTION_KEY in .env: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
from cryptography.fernet import Fernet, InvalidToken as _FernetInvalid

_ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "").encode()
_fernet = None
if _ENCRYPTION_KEY:
    try:
        _fernet = Fernet(_ENCRYPTION_KEY)
    except Exception:
        pass

def encrypt_pii(value: str) -> str:
    """Encrypt a PII string. Returns original value if encryption not configured."""
    if not value or not _fernet:
        return value
    return _fernet.encrypt(value.encode()).decode()

def decrypt_pii(value: str) -> str:
    """Decrypt a PII string. Returns original value if decryption fails (handles legacy plaintext)."""
    if not value or not _fernet:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except (_FernetInvalid, Exception):
        return value  # legacy plaintext — return as-is


# ---------------- DB CONTEXT MANAGER ----------------
@contextmanager
def _db():
    """Open a DB connection + buffered cursor; always close both on exit."""
    conn   = get_db_connection()
    cursor = conn.cursor(buffered=True)
    try:
        yield cursor, conn
    finally:
        try:  cursor.close()
        except Exception: pass
        try:  conn.close()
        except Exception: pass

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
        CREATE TABLE IF NOT EXISTS payroll_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pf_employee_pct DECIMAL(5,2) DEFAULT 12.00,
            pf_employer_pct DECIMAL(5,2) DEFAULT 12.00,
            professional_tax DECIMAL(8,2) DEFAULT 200.00,
            tds_annual_pct DECIMAL(5,2) DEFAULT 0.00,
            pf_basic_cap DECIMAL(10,2) DEFAULT 15000.00
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
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            recipient_type ENUM('admin', 'employee') NOT NULL,
            employee_id VARCHAR(50) NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS break_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            break_name VARCHAR(100) NOT NULL,
            break_time TIME NOT NULL,
            duration_minutes INT NOT NULL DEFAULT 10,
            is_active TINYINT(1) DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_goals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(150) NOT NULL,
            description TEXT,
            incentive_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_incentives (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            goal_id INT NOT NULL,
            month INT NOT NULL,
            year INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            notes TEXT,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_experience (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            company VARCHAR(150) NOT NULL,
            designation VARCHAR(100) NOT NULL,
            from_year VARCHAR(10) NOT NULL,
            to_year VARCHAR(10) DEFAULT NULL,
            is_current TINYINT(1) DEFAULT 0,
            description TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_education (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            degree VARCHAR(150) NOT NULL,
            institution VARCHAR(200) NOT NULL,
            year_of_passing VARCHAR(10) DEFAULT NULL,
            percentage VARCHAR(20) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_types (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            annual_quota INT NOT NULL DEFAULT 12,
            is_paid TINYINT(1) DEFAULT 1,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_balances (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            leave_type_id INT NOT NULL,
            year INT NOT NULL,
            total_days INT NOT NULL DEFAULT 0,
            used_days DECIMAL(4,1) NOT NULL DEFAULT 0,
            UNIQUE KEY uq_emp_lt_yr (employee_id, leave_type_id, year)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            doc_type VARCHAR(100) NOT NULL,
            original_name VARCHAR(255) NOT NULL,
            stored_name VARCHAR(255) NOT NULL,
            uploaded_by VARCHAR(20) DEFAULT 'admin',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            quarter TINYINT NOT NULL,
            year INT NOT NULL,
            overall_rating DECIMAL(3,1) DEFAULT 0,
            reviewer_feedback TEXT,
            employee_comment TEXT,
            status VARCHAR(20) DEFAULT 'Draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_emp_qtr_yr (employee_id, quarter, year)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_kpis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            review_id INT NOT NULL,
            kpi_title VARCHAR(200) NOT NULL,
            description TEXT,
            target VARCHAR(200),
            achievement VARCHAR(200),
            weight INT DEFAULT 20,
            rating TINYINT DEFAULT 0,
            comments TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overtime_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            shift_end TIME NOT NULL,
            actual_logout TIME NOT NULL,
            ot_minutes INT NOT NULL DEFAULT 0,
            ot_pay DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'Pending',
            notes TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_ot_emp_date (employee_id, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_template_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            template_id INT NOT NULL,
            task_title VARCHAR(300) NOT NULL,
            task_description TEXT,
            requires_document TINYINT(1) DEFAULT 0,
            due_days INT DEFAULT 7,
            sort_order INT DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_onboarding (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            template_id INT NOT NULL,
            assigned_date DATE NOT NULL,
            due_date DATE,
            status VARCHAR(20) DEFAULT 'In Progress',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_onboarding_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            onboarding_id INT NOT NULL,
            template_task_id INT NOT NULL,
            employee_id VARCHAR(50) NOT NULL,
            task_title VARCHAR(300) NOT NULL,
            task_description TEXT,
            requires_document TINYINT(1) DEFAULT 0,
            due_days INT DEFAULT 7,
            status VARCHAR(20) DEFAULT 'Pending',
            completed_at TIMESTAMP NULL,
            document_path VARCHAR(500),
            admin_notes TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compoff_balance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL UNIQUE,
            earned_minutes INT DEFAULT 0,
            used_minutes INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            token VARCHAR(64) PRIMARY KEY,
            token_type VARCHAR(20) NOT NULL DEFAULT 'admin',
            identity VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regularization_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            request_date DATE NOT NULL,
            login_time TIME DEFAULT NULL,
            logout_time TIME DEFAULT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            admin_note TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME DEFAULT NULL,
            UNIQUE KEY uq_emp_reg_date (employee_id, request_date)
        )
    """)
    db.commit()
    # Seed default leave types if empty
    cursor.execute("SELECT COUNT(*) FROM leave_types")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO leave_types (name, annual_quota, is_paid) VALUES (%s,%s,%s)",
            [
                ("Casual Leave",    12,  1),
                ("Sick Leave",      12,  1),
                ("Earned Leave",    15,  1),
                ("Maternity Leave", 90,  1),
                ("Paternity Leave",  5,  1),
                ("Comp-off",         0,  1),
            ]
        )
        db.commit()
    # Ensure Comp-off leave type exists
    cursor.execute("SELECT id FROM leave_types WHERE name='Comp-off' LIMIT 1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO leave_types (name, annual_quota, is_paid) VALUES ('Comp-off', 0, 1)")
        db.commit()
    # Seed default breaks if table is empty
    cursor.execute("SELECT COUNT(*) FROM break_config")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO break_config (break_name, break_time, duration_minutes) VALUES (%s, %s, %s)",
            [
                ("Coffee Break 1", "11:00:00", 10),
                ("Lunch Break",    "13:00:00", 60),
                ("Coffee Break 2", "16:00:00", 10),
            ]
        )
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
        "ALTER TABLE employees ADD COLUMN about_me TEXT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN manager_name VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN department VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN is_active TINYINT(1) DEFAULT 1",
        "ALTER TABLE leave_requests ADD COLUMN leave_type_id INT DEFAULT NULL",
        "ALTER TABLE leave_requests ADD COLUMN is_half_day TINYINT(1) DEFAULT 0",
        "ALTER TABLE leave_requests ADD COLUMN half_day_session VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE company_settings ADD COLUMN company_code VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'",
        "ALTER TABLE attendance ADD COLUMN worked_minutes INT DEFAULT 0",
        "ALTER TABLE attendance ADD COLUMN last_relogin TIME DEFAULT NULL",
        "ALTER TABLE salary_config ADD COLUMN monthly_ctc DECIMAL(12,2) DEFAULT 0",
        "ALTER TABLE salary_config ADD COLUMN basic_pct INT DEFAULT 50",
        "ALTER TABLE company_settings ADD COLUMN compoff_min_ot_minutes INT DEFAULT 120",
        "ALTER TABLE company_settings ADD COLUMN compoff_minutes_per_day INT DEFAULT 480",
        "ALTER TABLE employees ADD COLUMN joining_date DATE DEFAULT NULL",
    ]:
        try:
            cursor.execute(sql)
            db.commit()
        except mysql.connector.errors.DatabaseError:
            db.rollback()

    # Back-fill password for existing employees that have none (default PIN = 1234)
    cursor.execute("SELECT employee_id FROM employees WHERE password IS NULL")
    for (eid,) in cursor.fetchall():
        cursor.execute(
            "UPDATE employees SET password=%s WHERE employee_id=%s",
            (generate_password_hash('1234'), eid)
        )
    db.commit()

    # One-time migration: reset ALL employees to default PIN 1234
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _applied_migrations (
                name VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        cursor.execute("SELECT 1 FROM _applied_migrations WHERE name='default_pin_1234'")
        if not cursor.fetchone():
            cursor.execute("UPDATE employees SET password=%s", (generate_password_hash('1234'),))
            cursor.execute("INSERT INTO _applied_migrations (name) VALUES ('default_pin_1234')")
            db.commit()
    except Exception:
        pass

    # Migration: add force_pin_change column and flag employees on default PIN
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN force_pin_change TINYINT(1) DEFAULT 0")
        db.commit()
    except mysql.connector.errors.DatabaseError:
        db.rollback()
    try:
        cursor.execute("SELECT 1 FROM _applied_migrations WHERE name='force_pin_change_flag'")
        if not cursor.fetchone():
            default_hash = generate_password_hash('1234')
            cursor.execute("SELECT employee_id, password FROM employees")
            for eid, pwd_hash in cursor.fetchall():
                if pwd_hash and check_password_hash(pwd_hash, '1234'):
                    cursor.execute("UPDATE employees SET force_pin_change=1 WHERE employee_id=%s", (eid,))
            cursor.execute("INSERT INTO _applied_migrations (name) VALUES ('force_pin_change_flag')")
            db.commit()
    except Exception:
        pass

    # Create company_settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_name VARCHAR(200) DEFAULT 'My Company',
            company_tagline VARCHAR(300) DEFAULT 'Employee Attendance System',
            company_logo VARCHAR(255) DEFAULT NULL,
            currency_symbol VARCHAR(10) DEFAULT '₹',
            timezone VARCHAR(60) DEFAULT 'Asia/Kolkata',
            setup_done TINYINT(1) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    # Add default shift columns if not present
    for col, default in [("shift_start","09:00:00"), ("shift_half","13:00:00"), ("shift_end","18:00:00")]:
        try:
            cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col} TIME DEFAULT '{default}'")
            db.commit()
        except Exception:
            pass

    cursor.execute("SELECT COUNT(*) FROM company_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO company_settings (setup_done) VALUES (0)")
        db.commit()

    # Seed admin from env — only if no admin exists yet
    _admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip()
    _admin_pass = os.environ.get("ADMIN_PASSWORD", "").strip()
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    admin_count = cursor.fetchone()[0]
    if admin_count == 0 and _admin_pass:
        cursor.execute(
            "INSERT INTO admin_users (username, password) VALUES (%s, %s)",
            (_admin_user, generate_password_hash(_admin_pass))
        )
        db.commit()
        app_log.info('"Admin created: username=%s"', _admin_user)
        admin_count = 1
    elif admin_count == 0 and not _admin_pass:
        app_log.warning('"ADMIN_PASSWORD not set in .env — complete setup via /setup"')

    # Auto-mark setup done for existing installs that already have an admin
    if admin_count > 0:
        cursor.execute("UPDATE company_settings SET setup_done=1 WHERE setup_done=0")
        db.commit()

    cursor.close()
    db.close()


def assign_leave_balances_for_employee(cursor, employee_id, year=None):
    """Auto-assign leave balances for all active leave types for a new/existing employee."""
    if year is None:
        year = datetime.date.today().year
    cursor.execute("SELECT id, annual_quota FROM leave_types WHERE is_active=1")
    for lt_id, quota in cursor.fetchall():
        cursor.execute("""
            INSERT INTO leave_balances (employee_id, leave_type_id, year, total_days, used_days)
            VALUES (%s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE total_days=IF(total_days=0, VALUES(total_days), total_days)
        """, (employee_id, lt_id, year, quota))


def init_master_db():
    """Create the att_master database and its tenants table if they don't exist."""
    try:
        import mysql.connector as _mc
        root_conn = _mc.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASS", ""),
        )
        cur = root_conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS att_master CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute("USE att_master")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_name VARCHAR(200) NOT NULL,
                subdomain VARCHAR(100) UNIQUE NOT NULL,
                db_name VARCHAR(100) UNIQUE NOT NULL,
                admin_email VARCHAR(200) DEFAULT NULL,
                plan VARCHAR(50) DEFAULT 'starter',
                status VARCHAR(20) DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        root_conn.commit()
        cur.close()
        root_conn.close()
    except Exception as _e:
        app_log.warning('"init_master_db failed (non-fatal for single-tenant mode): %s"', _e)


def init_tenant_db(db_name: str):
    """Initialize schema in a freshly created tenant database."""
    from flask import g as _g
    _g.tenant_db = db_name
    init_db()


# ---------------- NOTIFICATION HELPER ----------------
def _create_notification(recipient_type, title, message, employee_id=None):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO notifications (recipient_type, employee_id, title, message) VALUES (%s,%s,%s,%s)",
            (recipient_type, employee_id, title, message)
        )
        db.commit()
        cursor.close(); db.close()
    except Exception:
        pass


# ---------------- ADMIN GUARD ----------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # If session has both admin and employee keys (tab conflict), clear and force re-login
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.clear()
            return redirect(url_for("admin_login"))
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
        # If session has both admin and employee keys (tab conflict), clear and force re-login
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.clear()
            return redirect("/employee_login")
        if not session.get("employee_id"):
            return redirect("/employee_login")
        return f(*args, **kwargs)
    return wrapper

def manager_or_admin_required(f):
    """Allow access to admin users whose role is 'admin' or 'manager'.

    Managers can access leave, attendance, and employee views but NOT
    salary, settings, or user management (enforced by the views themselves).
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Accept", "").startswith("application/json")
                or request.is_json
            )
            if is_ajax:
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.", "redirect": url_for("admin_login")}), 401
            return redirect(url_for("admin_login"))
        admin_role = session.get("admin_role", "admin")
        if admin_role not in ("admin", "manager"):
            return jsonify({"ok": False, "msg": "Insufficient permissions."}), 403
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

def classify_by_worked_minutes(login_status, total_minutes, s_start, s_end):
    """Classify attendance based on cumulative worked minutes vs shift length."""
    today_d = datetime.date.today()
    shift_mins = max(1, int((
        datetime.datetime.combine(today_d, s_end) -
        datetime.datetime.combine(today_d, s_start)
    ).total_seconds() / 60))
    if total_minutes >= shift_mins * 0.75:
        return "Late - Full Day" if login_status == "Late Login" else "Full Day"
    return "Half Day"

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

def detect_overtime(employee_id, date, logout_time):
    try:
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT s.end_time FROM employees e JOIN shifts s ON e.shift_id=s.id WHERE e.employee_id=%s",
            (employee_id,)
        )
        row = cursor.fetchone()
        shift_end = _td_to_time(row[0]) if row else SHIFT_END
        logout_t = _td_to_time(logout_time) if not isinstance(logout_time, datetime.time) else logout_time
        if logout_t is None or shift_end is None:
            cursor.close(); db.close(); return
        end_mins = shift_end.hour * 60 + shift_end.minute
        out_mins = logout_t.hour * 60 + logout_t.minute
        ot_minutes = out_mins - end_mins
        if ot_minutes < 30:
            cursor.close(); db.close(); return
        cursor.execute(
            "SELECT COALESCE(salary_per_day,0) FROM salary_config WHERE employee_id=%s",
            (employee_id,)
        )
        sc = cursor.fetchone()
        spd = float(sc[0]) if sc else 0.0
        ot_pay = round((spd / 8 / 60) * ot_minutes, 2)
        cursor.execute("""
            INSERT INTO overtime_records (employee_id, date, shift_end, actual_logout, ot_minutes, ot_pay, status)
            VALUES (%s,%s,%s,%s,%s,%s,'Pending')
            ON DUPLICATE KEY UPDATE actual_logout=VALUES(actual_logout), ot_minutes=VALUES(ot_minutes), ot_pay=VALUES(ot_pay)
        """, (employee_id, date, shift_end, logout_t, ot_minutes, ot_pay))
        db.commit()
        cursor.close(); db.close()
    except Exception:
        pass

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
    if emp_designation: emp_row_extra += f"<tr><td>Designation</td><td>{emp_designation}</td></tr>"
    if emp_dept:        emp_row_extra += f"<tr><td>Department</td><td>{emp_dept}</td></tr>"
    if pan:             emp_row_extra += f"<tr><td>PAN</td><td>{pan}</td></tr>"
    if uan:             emp_row_extra += f"<tr><td>UAN</td><td>{uan}</td></tr>"
    if bank_account:    emp_row_extra += f"<tr><td>Bank A/C</td><td>{'*'*len(bank_account[:-4]) + bank_account[-4:]}</td></tr>"
    if bank_name:       emp_row_extra += f"<tr><td>Bank</td><td>{bank_name}</td></tr>"

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
      <h1>{company_name or "Payslip"}</h1>
      <p>Salary Slip — {month_name}</p>
    </div>
    <div class="hdr-right">
      <div class="slip-num">Slip ID: {emp_id}-{year}{month:02d}</div>
      <div class="month">{month_name}</div>
    </div>
  </div>

  <div class="emp-bar">
    <table>
      <tr><td>Employee Name</td><td>{emp_name}</td></tr>
      <tr><td>Employee ID</td><td>{emp_id}</td></tr>
      <tr><td>Email</td><td>{emp_email or 'N/A'}</td></tr>
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
            app_log.error('"Email send failed to %s: %s"', to_email, e)
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

def get_employee_incentive_total(cursor, emp_id, year, month):
    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) FROM employee_incentives WHERE employee_id=%s AND year=%s AND month=%s",
        (emp_id, year, month)
    )
    return float(cursor.fetchone()[0])

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

def _error_page(code, icon, title, subtitle, hint):
    back_admin = session.get("admin_logged_in")
    back_emp   = session.get("employee_id")
    back_link  = "/admin" if back_admin else ("/employee_portal" if back_emp else "/")
    back_label = "Go to Admin Dashboard" if back_admin else ("Go to My Portal" if back_emp else "Go to Home")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{code} – {title}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:"Segoe UI",sans-serif}}
  body{{min-height:100vh;background:#f1f5f9;display:flex;align-items:center;justify-content:center;}}
  .box{{background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:52px 44px;text-align:center;max-width:480px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.08);}}
  .icon{{font-size:72px;margin-bottom:18px;}}
  .code{{font-size:80px;font-weight:900;line-height:1;color:#1e3a8a;margin-bottom:6px;}}
  .title{{font-size:22px;font-weight:700;color:#1e293b;margin-bottom:8px;}}
  .sub{{font-size:14px;color:#64748b;margin-bottom:6px;line-height:1.6;}}
  .hint{{font-size:12px;color:#94a3b8;margin-bottom:28px;}}
  a.btn{{display:inline-block;padding:12px 28px;background:#1e3a8a;color:#fff;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none;transition:0.2s;margin:4px;}}
  a.btn:hover{{background:#1d4ed8;}}
  a.sec{{display:inline-block;padding:12px 20px;background:#f1f5f9;color:#374151;border-radius:10px;font-size:14px;font-weight:600;text-decoration:none;transition:0.2s;margin:4px;border:1px solid #e2e8f0;}}
  a.sec:hover{{background:#e2e8f0;}}
</style></head><body>
<div class="box">
  <div class="icon">{icon}</div>
  <div class="code">{code}</div>
  <div class="title">{title}</div>
  <div class="sub">{subtitle}</div>
  <div class="hint">{hint}</div>
  <a href="{back_link}" class="btn">{back_label}</a>
  <a href="javascript:history.back()" class="sec">← Go Back</a>
</div>
</body></html>""", code

@app.errorhandler(404)
def not_found(e):
    return _error_page(404, "🔍", "Page Not Found",
        "The page you're looking for doesn't exist or has been moved.",
        "Check the URL or use one of the links below to get back on track.")

@app.errorhandler(403)
def forbidden(e):
    return _error_page(403, "🔒", "Access Denied",
        "You don't have permission to access this page.",
        "Please log in with the right account or contact your administrator.")

@app.errorhandler(500)
def internal_error(e):
    tb = _traceback.format_exc()
    app_log.error('"500 error: %s"', tb.replace('\n', '\\n'))
    return _error_page(500, "⚙️", "Internal Server Error",
        "Something went wrong on our end. The error has been logged.",
        "Please try again in a moment or contact your administrator.")

@app.errorhandler(Exception)
def unhandled_exception(e):
    if isinstance(e, HTTPException):
        return _error_page(e.code, "⚠️", e.name, e.description,
            "Use the buttons below to navigate back.")
    tb = _traceback.format_exc()
    app_log.error('"Unhandled exception: %s"', tb.replace('\n', '\\n'))
    return _error_page(500, "⚙️", "Unexpected Error",
        f"{type(e).__name__}: {e}",
        "The error has been logged. Please try again or contact your administrator.")

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- ADMIN LOGIN ----------------
@app.route("/setup", methods=["GET", "POST"])
def setup_wizard():
    co = get_company_settings()
    if co["setup_done"]:
        return redirect("/admin_login")

    error = None
    if request.method == "POST":
        company_name  = request.form.get("company_name", "").strip()
        company_tag   = request.form.get("company_tagline", "").strip()
        currency      = request.form.get("currency_symbol", "₹").strip()
        admin_user    = request.form.get("admin_username", "").strip()
        admin_pass    = request.form.get("admin_password", "").strip()
        admin_pass2   = request.form.get("admin_password2", "").strip()

        if not company_name:
            error = "Company name is required."
        elif not admin_user:
            error = "Admin username is required."
        elif len(admin_pass) < 6:
            error = "Password must be at least 6 characters."
        elif admin_pass != admin_pass2:
            error = "Passwords do not match."
        else:
            db = get_db_connection(); cursor = db.cursor(buffered=True)
            cursor.execute("UPDATE company_settings SET company_name=%s, company_tagline=%s, currency_symbol=%s, setup_done=1",
                           (company_name, company_tag or "Employee Attendance System", currency))
            cursor.execute("DELETE FROM admin_users")
            cursor.execute("INSERT INTO admin_users (username, password) VALUES (%s, %s)",
                           (admin_user, generate_password_hash(admin_pass)))
            db.commit(); cursor.close(); db.close()
            return redirect("/admin_login?setup=done")

    return render_template("setup.html", error=error)


@app.route("/admin_login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def admin_login():
    co = get_company_settings()
    if not co["setup_done"]:
        return redirect("/setup")
    if session.get("admin_logged_in"):
        return redirect("/admin")
    if session.get("employee_id"):
        return redirect("/employee_portal")
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "").strip()
        # Try admin credentials first
        with _db() as (cursor, db):
            cursor.execute("SELECT password, COALESCE(role,'admin') FROM admin_users WHERE username=%s", (identifier,))
            admin_row = cursor.fetchone()
        if admin_row and check_password_hash(admin_row[0], password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_role"] = admin_row[1]
            session.permanent = True
            return redirect("/admin")
        # Try employee credentials
        with _db() as (cursor, db):
            cursor.execute(
                "SELECT employee_id, name, role, password, COALESCE(force_pin_change,0) FROM employees WHERE employee_id=%s",
                (identifier,)
            )
            emp_row = cursor.fetchone()
        if emp_row:
            stored_pwd = emp_row[3]
            if stored_pwd and not check_password_hash(stored_pwd, password):
                return render_template("admin_login.html", error="Incorrect password.")
            session.clear()
            session["employee_id"]   = emp_row[0]
            session["employee_name"] = emp_row[1]
            session["employee_role"] = emp_row[2] or ""
            session.permanent = True
            if emp_row[4]:
                return redirect("/force_change_pin")
            return redirect("/employee_portal")
        return render_template("admin_login.html", error="Invalid credentials. Check your ID and password.")
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

    try:
        cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE status='Pending'")
        pending_ot = cursor.fetchone()[0]
    except Exception:
        pending_ot = 0

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

# ---------------- CHART DATA API ----------------
@app.route("/api/attendance_chart_data")
@admin_required
def attendance_chart_data():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    today  = datetime.date.today()

    # Last 30 days: present count per day
    cursor.execute("""
        SELECT a.date, COUNT(DISTINCT a.employee_id)
        FROM attendance a
        WHERE a.date >= %s AND a.date <= %s AND a.login_time IS NOT NULL
        GROUP BY a.date ORDER BY a.date
    """, (today - datetime.timedelta(days=29), today))
    present_by_day = {str(r[0]): r[1] for r in cursor.fetchall()}

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
    cursor.execute("""
        SELECT COALESCE(e.department, 'Unassigned'),
               COUNT(DISTINCT CASE WHEN a.login_time IS NOT NULL THEN e.employee_id END),
               COUNT(DISTINCT e.employee_id)
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND a.date=%s
        GROUP BY COALESCE(e.department, 'Unassigned')
        ORDER BY COALESCE(e.department, 'Unassigned')
    """, (today,))
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
        emp_id          = request.form["emp_id"].strip()
        email           = request.form.get("email", "").strip() or None
        role            = request.form.get("role", "").strip() or None
        date_of_joining = request.form.get("date_of_joining", "").strip() or None
        work_mode       = request.form.get("work_mode", "office").strip() or "office"
        work_lat_raw    = request.form.get("work_lat", "").strip()
        work_lon_raw    = request.form.get("work_lon", "").strip()
        work_lat        = float(work_lat_raw) if work_lat_raw else None
        work_lon        = float(work_lon_raw) if work_lon_raw else None
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
        file = request.files["face"]
        _img_ok, _img_err = _validate_image_file(file)
        if not _img_ok:
            flash(_img_err, "error")
            cursor.close(); db.close()
            return redirect("/admin")
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
        name = row[0]
        _img_ok, _img_err = _validate_image_file(file)
        if not _img_ok:
            flash(_img_err, "error")
            cursor.close(); db.close()
            return redirect("/admin")
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

# ---------------- SETTINGS (unified) ----------------
@app.route("/settings")
@admin_required
def settings_page():
    tab    = request.args.get("tab", "email")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Email config
    cursor.execute("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email FROM email_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    email_config = {"host": row[0], "port": row[1], "user": row[2], "password": row[3], "from_name": row[4], "from_email": row[5] or row[2]} if row else None

    # Shifts
    cursor.execute("SELECT id, name, start_time, half_time, end_time FROM shifts ORDER BY start_time")
    shift_rows = []
    for sid, sname, st, ht, et in cursor.fetchall():
        shift_rows.append({
            "id": sid, "name": sname,
            "start": _td_to_time(st).strftime("%H:%M") if st else "--",
            "half":  _td_to_time(ht).strftime("%H:%M") if ht else "--",
            "end":   _td_to_time(et).strftime("%H:%M") if et else "--",
        })
    cursor.execute("SELECT e.employee_id, e.name, e.role, s.name FROM employees e LEFT JOIN shifts s ON e.shift_id = s.id ORDER BY e.name")
    emp_list = [{"emp_id": r[0], "name": r[1], "role": r[2] or "", "shift": r[3] or "Default"} for r in cursor.fetchall()]

    # Breaks
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active FROM break_config ORDER BY break_time")
    breaks = cursor.fetchall()

    # Salary
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(s.salary_per_day, 0), e.role, s.last_revised,
               COALESCE(e.phone,''), COALESCE(e.email,'')
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
        ORDER BY e.name
    """)
    salaries = cursor.fetchall()

    # Announcements
    cursor.execute("SELECT id, title, content, priority, created_at FROM announcements ORDER BY created_at DESC")
    ann_list = cursor.fetchall()

    # Incentive goals
    cursor.execute("SELECT id, title, description, incentive_amount, is_active FROM incentive_goals ORDER BY created_at DESC")
    incentive_goals = cursor.fetchall()

    # Recent incentive awards (last 100)
    cursor.execute("""
        SELECT ei.id, e.name, ig.title, ei.month, ei.year, ei.amount, ei.notes, ei.awarded_at
        FROM employee_incentives ei
        JOIN employees e ON ei.employee_id = e.employee_id
        JOIN incentive_goals ig ON ei.goal_id = ig.id
        ORDER BY ei.awarded_at DESC
        LIMIT 100
    """)
    recent_incentives = cursor.fetchall()

    # Pending counts
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    pending_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(company_code,'') FROM company_settings LIMIT 1")
    _cr = cursor.fetchone()
    company_code = _cr[0] if _cr else ""

    cursor.close(); db.close()
    return render_template("settings.html",
        tab=tab,
        email_config=email_config,
        company_code=company_code,
        shifts=shift_rows,
        emp_list=emp_list,
        breaks=breaks,
        salaries=salaries,
        ann_list=ann_list,
        incentive_goals=incentive_goals,
        recent_incentives=recent_incentives,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        saved=request.args.get("saved") == "1",
        default_start=SHIFT_START.strftime("%H:%M"),
        default_half=SHIFT_HALF.strftime("%H:%M"),
        default_end=SHIFT_END.strftime("%H:%M"),
        now_month=datetime.date.today().month,
        now_year=datetime.date.today().year,
    )

# ---------------- SAVE COMPANY CODE ----------------
@app.route("/save_company_code", methods=["POST"])
@admin_required
def save_company_code():
    code = request.form.get("company_code", "").strip().upper()[:10]
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE company_settings SET company_code=%s", (code,))
    db.commit(); cursor.close(); db.close()
    flash(f"Company code set to '{code}'.", "success")
    return redirect("/settings?tab=email")


# ---------------- INCENTIVES ----------------

@app.route("/add_incentive_goal", methods=["POST"])
@admin_required
def add_incentive_goal():
    title  = request.form.get("title", "").strip()
    desc   = request.form.get("description", "").strip()
    amount = request.form.get("incentive_amount", "0").strip()
    if not title:
        return redirect("/settings?tab=incentives")
    try:
        amount = float(amount)
    except ValueError:
        amount = 0.0
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO incentive_goals (title, description, incentive_amount) VALUES (%s,%s,%s)",
        (title, desc, amount)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/settings?tab=incentives&saved=1")

@app.route("/edit_incentive_goal", methods=["POST"])
@admin_required
def edit_incentive_goal():
    gid    = request.form.get("goal_id")
    title  = request.form.get("title", "").strip()
    desc   = request.form.get("description", "").strip()
    amount = request.form.get("incentive_amount", "0").strip()
    active = 1 if request.form.get("is_active") else 0
    try:
        amount = float(amount)
    except ValueError:
        amount = 0.0
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE incentive_goals SET title=%s, description=%s, incentive_amount=%s, is_active=%s WHERE id=%s",
        (title, desc, amount, active, gid)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/settings?tab=incentives&saved=1")

@app.route("/delete_incentive_goal", methods=["POST"])
@admin_required
def delete_incentive_goal():
    gid = request.form.get("goal_id")
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_incentives WHERE goal_id=%s", (gid,))
    cursor.execute("DELETE FROM incentive_goals WHERE id=%s", (gid,))
    db.commit(); cursor.close(); db.close()
    return redirect("/settings?tab=incentives")

@app.route("/award_incentive", methods=["POST"])
@admin_required
def award_incentive():
    emp_id = request.form.get("employee_id", "").strip()
    goal_id = request.form.get("goal_id", "").strip()
    month  = int(request.form.get("month", datetime.date.today().month))
    year   = int(request.form.get("year",  datetime.date.today().year))
    amount = request.form.get("amount", "").strip()
    notes  = request.form.get("notes", "").strip()
    if not emp_id or not goal_id:
        return redirect("/settings?tab=incentives")
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    # If amount not given, use the goal's default amount
    if not amount:
        cursor.execute("SELECT incentive_amount FROM incentive_goals WHERE id=%s", (goal_id,))
        row = cursor.fetchone()
        amount = float(row[0]) if row else 0.0
    else:
        try:
            amount = float(amount)
        except ValueError:
            amount = 0.0
    cursor.execute(
        "INSERT INTO employee_incentives (employee_id, goal_id, month, year, amount, notes) VALUES (%s,%s,%s,%s,%s,%s)",
        (emp_id, goal_id, month, year, amount, notes)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/settings?tab=incentives&saved=1")

@app.route("/delete_incentive", methods=["POST"])
@admin_required
def delete_incentive():
    inc_id = request.form.get("incentive_id")
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_incentives WHERE id=%s", (inc_id,))
    db.commit(); cursor.close(); db.close()
    return redirect("/settings?tab=incentives")

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
        return redirect("/performance?tab=announcements")
    cursor.close(); db.close()
    return redirect("/performance?tab=announcements")

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


@app.route("/edit_employee/<emp_id>", methods=["GET"])
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
    return render_template("edit_employee.html", emp=emp)


@app.route("/employee_profile/<emp_id>")
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
            WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s
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
              AND YEAR(lr.leave_date)=%s
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
    )


@app.route("/edit_employee", methods=["POST"])
@admin_required
def edit_employee():
    emp_id          = request.form["emp_id"].strip()
    name            = request.form.get("name",            "").strip()
    email           = request.form.get("email",           "").strip() or None
    role            = request.form.get("role",            "").strip() or None
    date_of_joining = request.form.get("date_of_joining", "").strip() or None
    department      = request.form.get("department",      "").strip() or None
    manager_name    = request.form.get("manager_name",    "").strip() or None
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
        "department=%s, manager_name=%s, phone=%s, gender=%s, dob=%s, blood_group=%s, "
        "shift_id=%s, address=%s, city=%s, state=%s, pincode=%s, "
        "emergency_contact_name=%s, emergency_contact_phone=%s, emergency_contact_relation=%s, "
        "work_mode=%s, work_lat=%s, work_lon=%s "
        "WHERE employee_id=%s",
        (name, email, role, date_of_joining, department, manager_name,
         phone, gender, dob, blood_group, shift_id,
         address, city, state, pincode,
         ec_name, ec_phone, ec_rel,
         work_mode, work_lat, work_lon, emp_id)
    )
    db.commit(); cursor.close(); db.close()
    flash(f"Employee '{emp_id}' updated successfully.", "success")
    return redirect("/employees")


@app.route("/api/employee_info/<emp_id>")
@admin_required
def api_employee_info(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT employee_id, name, role, email, date_of_joining, "
        "work_mode, work_lat, work_lon, department, manager_name, face_image, qr_code, "
        "phone, gender, dob, blood_group, shift_id, "
        "address, city, state, pincode, "
        "emergency_contact_name, emergency_contact_phone, emergency_contact_relation "
        "FROM employees WHERE employee_id=%s", (emp_id,)
    )
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    (eid, name, role, email, doj, wm, wlat, wlon, dept, mgr, face_image, qr_code,
     phone, gender, dob, blood_group, shift_id,
     address, city, state, pincode,
     ec_name, ec_phone, ec_rel) = row
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


@app.route("/employees")
@admin_required
def view_employees():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
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
        "WHERE status='Approved' AND leave_date=CURDATE()"
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

    cursor.execute("SELECT id, name FROM shifts ORDER BY name")
    shifts = cursor.fetchall()
    cursor.execute(
        "SELECT DISTINCT department FROM employees "
        "WHERE department IS NOT NULL AND department != '' ORDER BY department"
    )
    departments = [r[0] for r in cursor.fetchall()]

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
        shifts=shifts,
        departments=departments,
        total=total,
        active_count=active_count,
        on_leave_count=on_leave_count,
        resigned_count=resigned_count,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    )


# ---------------- EMPLOYEE DETAIL PAGE ----------------
@app.route("/employee_detail/<emp_id>")
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
               SUM(CASE WHEN a.attendance_type LIKE 'Late%' OR a.status='Late Login' THEN 1 ELSE 0 END) AS late_days,
               COALESCE(sc.salary_per_day, 0) AS salary_per_day,
               e.about_me
        FROM employees e
        LEFT JOIN shifts s ON e.shift_id = s.id
        LEFT JOIN attendance a ON e.employee_id = a.employee_id
        LEFT JOIN salary_config sc ON e.employee_id = sc.employee_id
        WHERE e.employee_id = %s
        GROUP BY e.employee_id
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
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE employee_id=%s AND status='Approved' AND leave_date=CURDATE()", (emp_id,))
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
    )


# ---------------- ADD EMPLOYEE (from employees page) ----------------
@app.route("/add_employee_page", methods=["POST"])
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

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)

    test_img = face_recognition.load_image_file(filepath)
    if not face_recognition.face_encodings(test_img):
        os.remove(filepath)
        flash("No face detected in the uploaded photo. Please upload a clear, well-lit front-facing photo.", "error")
        cursor.close(); db.close()
        return redirect("/employees")

    qr_path   = generate_qr(emp_id)
    auto_pass = secrets.token_urlsafe(8)
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
        assign_leave_balances_for_employee(cursor, emp_id)
        db.commit()
        flash(f"Employee '{name}' registered! ID: {emp_id} | Password: {auto_pass}", "success")
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
    except Exception as ex:
        db.rollback()
        flash(f"Registration failed: {ex}", "error")
    cursor.close(); db.close()
    return redirect("/employees")


# ---------------- UPDATE EMPLOYEE PHOTO ----------------
@app.route("/update_employee_photo/<emp_id>", methods=["POST"])
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

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], emp_id + ".jpg")
    file.save(filepath)

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


# ---------------- REGENERATE QR ----------------
@app.route("/regenerate_qr/<emp_id>", methods=["POST"])
@admin_required
def regenerate_qr(emp_id):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id=%s", (emp_id,))
    if not cursor.fetchone():
        flash("Employee not found.", "error")
        cursor.close(); db.close()
        return redirect("/employees")
    qr_path = generate_qr(emp_id)
    cursor.execute("UPDATE employees SET qr_code=%s WHERE employee_id=%s", (qr_path, emp_id))
    db.commit()
    flash(f"QR code regenerated for '{emp_id}'.", "success")
    cursor.close(); db.close()
    return redirect("/employees")


# ---------------- LEAVE TYPES ADMIN ----------------
@app.route("/admin_leave_types", methods=["GET", "POST"])
@admin_required
def admin_leave_types():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "add":
            name    = request.form.get("name", "").strip()
            quota   = int(request.form.get("annual_quota", 12) or 12)
            is_paid = 1 if request.form.get("is_paid") else 0
            if name:
                cursor.execute(
                    "INSERT INTO leave_types (name, annual_quota, is_paid) VALUES (%s,%s,%s)",
                    (name, quota, is_paid)
                )
        elif action == "edit":
            lt_id   = int(request.form.get("lt_id", 0))
            name    = request.form.get("name", "").strip()
            quota   = int(request.form.get("annual_quota", 12) or 12)
            is_paid = 1 if request.form.get("is_paid") else 0
            if lt_id and name:
                cursor.execute(
                    "UPDATE leave_types SET name=%s, annual_quota=%s, is_paid=%s WHERE id=%s",
                    (name, quota, is_paid, lt_id)
                )
        elif action == "toggle":
            lt_id = int(request.form.get("lt_id", 0))
            if lt_id:
                cursor.execute(
                    "UPDATE leave_types SET is_active = 1 - is_active WHERE id=%s", (lt_id,)
                )
        elif action == "delete":
            lt_id = int(request.form.get("lt_id", 0))
            if lt_id:
                cursor.execute("DELETE FROM leave_types WHERE id=%s", (lt_id,))
        db.commit()
        cursor.close(); db.close()
        return redirect("/admin_leave_types")

    cursor.execute("SELECT id, name, annual_quota, is_paid, is_active FROM leave_types ORDER BY id")
    leave_types = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("leave_types_admin.html", leave_types=leave_types)


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
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/my_photo")
def my_photo():
    from flask import send_from_directory
    emp_id = session.get("employee_id")
    if not emp_id:
        return "", 403
    photo_path = os.path.join(UPLOAD_FOLDER, emp_id + ".jpg")
    if not os.path.exists(photo_path):
        return "", 404
    return send_from_directory(UPLOAD_FOLDER, emp_id + ".jpg")


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
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active FROM break_config ORDER BY break_time")
    breaks = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("shifts.html", shifts=shift_rows, employees=employees,
                           breaks=breaks,
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

@app.route("/update_default_shift", methods=["POST"])
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

# ---------------- AUTO GENERATE EMPLOYEE ID ----------------
@app.route("/api/generate_emp_id")
def generate_emp_id():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "not logged in"}), 401
    work_mode = request.args.get("work_mode", "office").strip().lower()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT COALESCE(company_code,'') FROM company_settings LIMIT 1")
    row = cursor.fetchone()
    code = (row[0] or "").strip().upper() if row else ""
    prefix = code
    cursor.execute("SELECT COUNT(*) FROM employees")
    total = cursor.fetchone()[0]
    cursor.close(); db.close()
    seq = total + 1
    emp_id = f"{prefix}{seq:03d}"
    return jsonify({"emp_id": emp_id, "code": code, "seq": seq})


# ---------------- BREAK CONFIG ----------------
@app.route("/api/breaks")
def api_breaks():
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

@app.route("/break_config")
@admin_required
def view_break_config():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, break_name, break_time, duration_minutes, is_active FROM break_config ORDER BY break_time")
    breaks = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("break_config.html", breaks=breaks,
                           shift_start=SHIFT_START.strftime("%I:%M %p"),
                           shift_end=SHIFT_END.strftime("%I:%M %p"))

@app.route("/add_break", methods=["POST"])
@admin_required
def add_break():
    name     = request.form["break_name"].strip()
    btime    = request.form["break_time"]
    duration = int(request.form.get("duration_minutes", 10))
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("INSERT INTO break_config (break_name, break_time, duration_minutes) VALUES (%s,%s,%s)",
                   (name, btime, duration))
    db.commit(); cursor.close(); db.close()
    flash("Break added successfully.", "success")
    return redirect("/shifts")

@app.route("/update_break/<int:bid>", methods=["POST"])
@admin_required
def update_break(bid):
    name     = request.form["break_name"].strip()
    btime    = request.form["break_time"]
    duration = int(request.form.get("duration_minutes", 10))
    active   = 1 if request.form.get("is_active") == "1" else 0
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE break_config SET break_name=%s, break_time=%s, duration_minutes=%s, is_active=%s WHERE id=%s",
        (name, btime, duration, active, bid)
    )
    db.commit(); cursor.close(); db.close()
    flash("Break updated.", "success")
    return redirect("/shifts")

@app.route("/delete_break/<int:bid>", methods=["POST"])
@admin_required
def delete_break(bid):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM break_config WHERE id=%s", (bid,))
    db.commit(); cursor.close(); db.close()
    flash("Break deleted.", "success")
    return redirect("/shifts")

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
    return redirect("/settings?tab=salary")

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

# ---------------- EMPLOYEE ATTENDANCE DETAIL ----------------
@app.route("/employee_attendance_detail/<emp_id>/<int:year>/<int:month>")
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
        year=year, month=month,
        months=months, years=years,
        full_days=full_days,
        late_days=late_days,
        half_days=half_days,
        absent=absent,
    )

# ---------------- MANUAL ATTENDANCE CORRECTION ----------------
@app.route("/correct_attendance", methods=["POST"])
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
        return redirect(request.referrer or "/monthly_report")

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        flash("Invalid date.", "error")
        return redirect(request.referrer or "/monthly_report")

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
        year=year, month=month,
        months=months, years=years,
        late_rate=int(LATE_DEDUCTION_RATE * 100),
        half_rate=int(HALF_DAY_RATE * 100),
        email_configured=email_cfg is not None,
    )


@app.route("/salary_report_export")
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
        return redirect("/settings?tab=email&saved=1")

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
        grace_time = (datetime.datetime.combine(today, s_start) + datetime.timedelta(minutes=15)).time()
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

# ================================================================
#  EMPLOYEE PORTAL
# ================================================================

@app.route("/employee_login", methods=["GET", "POST"])
def employee_login():
    return redirect("/admin_login")


@app.route("/employee_logout")
def employee_logout():
    session.clear()
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


@app.route("/force_change_pin", methods=["GET", "POST"])
@employee_required
def force_change_pin():
    emp_id = session["employee_id"]
    error  = None
    if request.method == "POST":
        new_pwd = request.form.get("new_password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        if len(new_pwd) < 6:
            error = "Password must be at least 6 characters."
        elif new_pwd != confirm:
            error = "Passwords do not match."
        elif new_pwd == "1234":
            error = "You cannot use '1234' as your password."
        else:
            db = get_db_connection()
            cursor = db.cursor(buffered=True)
            cursor.execute(
                "UPDATE employees SET password=%s, force_pin_change=0 WHERE employee_id=%s",
                (generate_password_hash(new_pwd), emp_id)
            )
            db.commit(); cursor.close(); db.close()
            return redirect("/employee_portal")
    return render_template("force_change_pin.html", error=error,
                           emp_name=session.get("employee_name", ""))


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


@app.route("/update_my_bank_details", methods=["POST"])
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




@app.route("/add_experience", methods=["POST"])
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


@app.route("/delete_experience/<int:entry_id>", methods=["POST"])
@employee_required
def delete_experience(entry_id):
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_experience WHERE id=%s AND employee_id=%s", (entry_id, emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal#my-profile")


@app.route("/add_education_entry", methods=["POST"])
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


@app.route("/delete_education_entry/<int:entry_id>", methods=["POST"])
@employee_required
def delete_education_entry(entry_id):
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM employee_education WHERE id=%s AND employee_id=%s", (entry_id, emp_id))
    db.commit(); cursor.close(); db.close()
    return redirect("/employee_portal#my-profile")


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


@app.route("/admin_id_card/<emp_id>")
@admin_required
def admin_id_card(emp_id):
    from PIL import Image, ImageDraw, ImageFont
    import io as _io2
    from flask import send_file

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
        return "Employee not found", 404

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
    view_mode = request.args.get("view") == "1"
    return send_file(buf,
                     as_attachment=not view_mode,
                     download_name=f"IDCard_{emp_id}.png",
                     mimetype="image/png")


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
               e.qr_code, e.work_mode, e.about_me, e.manager_name, e.department
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
               COALESCE(lt.name, '') AS leave_type_name
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
            WHERE employee_id=%s AND YEAR(leave_date)=%s AND status IN ('Approved','Pending')
        """, (emp_id, today.year))
        leaves_used   = cursor.fetchone()[0] or 0
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
        WHERE date >= %s AND YEAR(date) = %s
        ORDER BY date LIMIT 15
    """, (today, today.year))
    leave_holidays = cursor.fetchall()

    # Holiday calendar data for employee view
    hol_year = int(request.args.get("hol_year", today.year))
    cursor.execute("SELECT id, date, name FROM holidays WHERE YEAR(date)=%s ORDER BY date", (hol_year,))
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
            "SELECT date, shift_end, actual_logout, ot_minutes, ot_pay, status FROM overtime_records WHERE employee_id=%s AND YEAR(date)=%s ORDER BY date DESC LIMIT 20",
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
            "SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s AND status='Approved'",
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
            cursor.execute("SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s AND status='Approved'", (emp_id, pm2, py2))
            p_ot = float(cursor.fetchone()[0] or 0)
        except Exception:
            p_ot = 0.0
        recent_payslips.append({
            'month': calendar.month_name[pm2], 'year': py2,
            'gross': p_gross, 'incentives': p_inc, 'ot_pay': p_ot,
            'net': p_gross + p_inc + p_ot,
            'present': p_full + p_late + p_half, 'absent': p_absent,
        })

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
            "SELECT COALESCE(SUM(ot_pay),0) FROM overtime_records WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s AND status='Approved'",
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
    leave_start  = request.form.get("leave_date_start", "").strip()
    leave_end    = request.form.get("leave_date_end", "").strip() or leave_start
    reason       = request.form.get("reason", "").strip()
    leave_type_id_raw = request.form.get("leave_type_id", "").strip()
    leave_type_id = int(leave_type_id_raw) if leave_type_id_raw.isdigit() else None
    is_half_day      = 1 if request.form.get("is_half_day") else 0
    half_day_session = request.form.get("half_day_session", "Morning") if is_half_day else None
    if not reason or not leave_start:
        return redirect("/employee_portal")

    start_dt = datetime.date.fromisoformat(leave_start)
    # Half-day is always a single date; ignore end date
    if is_half_day:
        end_dt = start_dt
    else:
        end_dt = datetime.date.fromisoformat(leave_end) if leave_end else start_dt
        if end_dt < start_dt:
            end_dt = start_dt

    num_days = (end_dt - start_dt).days + 1
    if is_half_day:
        date_label = f"{leave_start} (Half Day – {half_day_session})"
    else:
        date_label = (leave_start if num_days == 1
                      else f"{leave_start} – {leave_end} ({num_days} days)")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cur = start_dt
    while cur <= end_dt:
        cursor.execute(
            "INSERT INTO leave_requests (employee_id, leave_date, reason, leave_type_id, is_half_day, half_day_session) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (emp_id, cur, reason, leave_type_id, is_half_day, half_day_session)
        )
        cur += datetime.timedelta(days=1)
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
      <tr style="background:#f8f9fc;"><td style="padding:10px 14px;color:#555;font-weight:600;">Leave Period</td><td style="padding:10px 14px;">{date_label}</td></tr>
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
                f"Leave Request — {emp_name} ({date_label})",
                html_body, config
            )
        except Exception as e:
            app_log.error('"Leave request notification email failed: %s"', e)

    return redirect("/employee_portal?leave_sent=1#apply-leave")


@app.route("/leave_balance")
@admin_required
def leave_balance():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    year = int(request.args.get("year", datetime.date.today().year))

    cursor.execute("SELECT company_name FROM company_settings LIMIT 1")
    row = cursor.fetchone()
    co = type('Co', (), {'company_name': row[0] if row else 'My Company'})()
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT id, name, annual_quota FROM leave_types WHERE is_active=1 ORDER BY id")
    leave_types = cursor.fetchall()

    # Auto-assign balances for employees who don't have them yet
    cursor.execute("SELECT employee_id FROM employees")
    all_emps = [r[0] for r in cursor.fetchall()]
    for eid in all_emps:
        assign_leave_balances_for_employee(cursor, eid, year)
    db.commit()

    # Fetch all balances
    cursor.execute("""
        SELECT e.employee_id, e.name, e.department,
               lt.id, lt.name, lb.total_days, lb.used_days
        FROM employees e
        JOIN leave_types lt ON lt.is_active=1
        LEFT JOIN leave_balances lb ON lb.employee_id=e.employee_id
            AND lb.leave_type_id=lt.id AND lb.year=%s
        ORDER BY e.name, lt.id
    """, (year,))
    rows = cursor.fetchall()

    # Group by employee
    from collections import defaultdict, OrderedDict
    emp_balances = OrderedDict()
    for emp_id, emp_name, dept, lt_id, lt_name, total, used in rows:
        if emp_id not in emp_balances:
            emp_balances[emp_id] = {'name': emp_name, 'dept': dept or '—', 'leaves': []}
        used = float(used or 0)
        total = int(total or 0)
        remaining = max(0, total - used)
        emp_balances[emp_id]['leaves'].append({
            'lt_id': lt_id, 'lt_name': lt_name,
            'total': total, 'used': used, 'remaining': remaining
        })

    cursor.close(); db.close()
    return render_template("leave_balance.html",
        co=co, year=year,
        leave_types=leave_types,
        emp_balances=emp_balances,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        shift_start="09:00 AM", shift_end="06:00 PM"
    )


@app.route("/set_leave_balance", methods=["POST"])
@admin_required
def set_leave_balance():
    emp_id = request.form.get("employee_id")
    lt_id  = int(request.form.get("leave_type_id"))
    total  = int(request.form.get("total_days", 0))
    year   = int(request.form.get("year", datetime.date.today().year))
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        INSERT INTO leave_balances (employee_id, leave_type_id, year, total_days, used_days)
        VALUES (%s, %s, %s, %s, 0)
        ON DUPLICATE KEY UPDATE total_days=%s
    """, (emp_id, lt_id, year, total, total))
    db.commit()
    cursor.close(); db.close()
    flash("Leave balance updated successfully.", "success")
    return redirect(f"/leave_balance?year={year}")


# ─────────────────────────── PERFORMANCE MANAGEMENT ───────────────────────────

RATING_LABELS = {0: "Not Rated", 1: "Unsatisfactory", 2: "Needs Improvement",
                 3: "Meets Expectations", 4: "Exceeds Expectations", 5: "Outstanding"}

@app.route("/performance")
@admin_required
def performance():
    today  = datetime.date.today()
    q      = int(request.args.get("quarter", (today.month - 1) // 3 + 1))
    yr     = int(request.args.get("year", today.year))
    dept   = request.args.get("dept", "")
    active_tab = request.args.get("tab", "performance")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    dept_filter = "AND e.department=%s" if dept else ""
    params = [yr, q] + ([dept] if dept else [])
    cursor.execute(f"""
        SELECT e.employee_id, e.name, COALESCE(e.role,''), COALESCE(e.department,''),
               pr.id, COALESCE(pr.overall_rating,0), COALESCE(pr.status,'—'),
               (SELECT COUNT(*) FROM performance_kpis pk WHERE pk.review_id=pr.id) AS kpi_count
        FROM employees e
        LEFT JOIN performance_reviews pr
            ON pr.employee_id=e.employee_id AND pr.year=%s AND pr.quarter=%s
        WHERE e.is_active=1 {dept_filter}
        ORDER BY e.name
    """, params)
    employees = cursor.fetchall()

    cursor.execute("SELECT DISTINCT COALESCE(department,'') FROM employees WHERE is_active=1 AND department IS NOT NULL AND department!='' ORDER BY 1")
    departments = [r[0] for r in cursor.fetchall()]

    # Announcements
    cursor.execute("SELECT id, title, content, priority, created_at FROM announcements ORDER BY created_at DESC")
    ann_list = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(company_name,'') FROM company_settings LIMIT 1")
    co = cursor.fetchone()
    cursor.close(); db.close()

    return render_template("performance.html",
        employees=employees, departments=departments,
        quarter=q, year=yr, selected_dept=dept,
        rating_labels=RATING_LABELS,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets, co=co,
        today=today,
        ann_list=ann_list,
        active_tab=active_tab,
    )


@app.route("/performance_review/<emp_id>", methods=["GET"])
@admin_required
def performance_review(emp_id):
    today = datetime.date.today()
    q     = int(request.args.get("quarter", (today.month - 1) // 3 + 1))
    yr    = int(request.args.get("year", today.year))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(e.role,''), COALESCE(e.department,''),
               COALESCE(e.email,''), COALESCE(e.phone,'')
        FROM employees e WHERE e.employee_id=%s
    """, (emp_id,))
    emp = cursor.fetchone()
    if not emp:
        cursor.close(); db.close()
        flash("Employee not found.", "error")
        return redirect("/performance")

    # Get or create review
    cursor.execute("""
        SELECT id, overall_rating, reviewer_feedback, employee_comment, status
        FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s
    """, (emp_id, q, yr))
    review = cursor.fetchone()

    kpis = []
    if review:
        cursor.execute("""
            SELECT id, kpi_title, description, target, achievement, weight, rating, comments
            FROM performance_kpis WHERE review_id=%s ORDER BY id
        """, (review[0],))
        kpis = cursor.fetchall()

    # Past reviews for history tab
    cursor.execute("""
        SELECT id, quarter, year, overall_rating, status, created_at
        FROM performance_reviews WHERE employee_id=%s ORDER BY year DESC, quarter DESC LIMIT 8
    """, (emp_id,))
    history = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(company_name,'') FROM company_settings LIMIT 1")
    co = cursor.fetchone()
    cursor.close(); db.close()

    return render_template("performance_review.html",
        emp=emp, review=review, kpis=kpis, history=history,
        quarter=q, year=yr, rating_labels=RATING_LABELS,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets, co=co
    )


@app.route("/performance_save_review", methods=["POST"])
@admin_required
def performance_save_review():
    emp_id   = request.form["employee_id"]
    q        = int(request.form["quarter"])
    yr       = int(request.form["year"])
    feedback = request.form.get("reviewer_feedback", "").strip()
    status   = request.form.get("status", "Draft")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        INSERT INTO performance_reviews (employee_id, quarter, year, reviewer_feedback, status)
        VALUES (%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE reviewer_feedback=%s, status=%s, updated_at=NOW()
    """, (emp_id, q, yr, feedback, status, feedback, status))
    db.commit()

    # Recalculate overall rating from KPIs
    cursor.execute("SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s", (emp_id, q, yr))
    rev = cursor.fetchone()
    if rev:
        cursor.execute("""
            SELECT weight, rating FROM performance_kpis WHERE review_id=%s AND rating > 0
        """, (rev[0],))
        kpi_rows = cursor.fetchall()
        if kpi_rows:
            total_weight = sum(r[0] for r in kpi_rows)
            weighted_sum = sum(r[0] * r[1] for r in kpi_rows)
            overall = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0
            cursor.execute("UPDATE performance_reviews SET overall_rating=%s WHERE id=%s", (overall, rev[0]))
            db.commit()

    cursor.close(); db.close()
    flash("Review saved successfully.", "success")
    return redirect(f"/performance_review/{emp_id}?quarter={q}&year={yr}")


@app.route("/performance_add_kpi", methods=["POST"])
@admin_required
def performance_add_kpi():
    emp_id = request.form["employee_id"]
    q      = int(request.form["quarter"])
    yr     = int(request.form["year"])
    title  = request.form.get("kpi_title", "").strip()
    desc   = request.form.get("description", "").strip()
    target = request.form.get("target", "").strip()
    weight = int(request.form.get("weight", 20))

    if not title:
        flash("KPI title is required.", "error")
        return redirect(f"/performance_review/{emp_id}?quarter={q}&year={yr}")

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Ensure review exists
    cursor.execute("""
        INSERT INTO performance_reviews (employee_id, quarter, year, status)
        VALUES (%s,%s,%s,'Draft')
        ON DUPLICATE KEY UPDATE updated_at=NOW()
    """, (emp_id, q, yr))
    db.commit()

    cursor.execute("SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s", (emp_id, q, yr))
    rev_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO performance_kpis (review_id, kpi_title, description, target, weight)
        VALUES (%s,%s,%s,%s,%s)
    """, (rev_id, title, desc, target, weight))
    db.commit()
    cursor.close(); db.close()
    flash("KPI added.", "success")
    return redirect(f"/performance_review/{emp_id}?quarter={q}&year={yr}")


@app.route("/performance_rate_kpi", methods=["POST"])
@admin_required
def performance_rate_kpi():
    kpi_id      = int(request.form["kpi_id"])
    emp_id      = request.form["employee_id"]
    q           = int(request.form["quarter"])
    yr          = int(request.form["year"])
    rating      = int(request.form.get("rating", 0))
    achievement = request.form.get("achievement", "").strip()
    comments    = request.form.get("comments", "").strip()

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        UPDATE performance_kpis SET rating=%s, achievement=%s, comments=%s WHERE id=%s
    """, (rating, achievement, comments, kpi_id))
    db.commit()

    # Recalculate overall rating
    cursor.execute("SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=%s AND year=%s", (emp_id, q, yr))
    rev = cursor.fetchone()
    if rev:
        cursor.execute("SELECT weight, rating FROM performance_kpis WHERE review_id=%s AND rating>0", (rev[0],))
        rows = cursor.fetchall()
        if rows:
            tw = sum(r[0] for r in rows); ws = sum(r[0]*r[1] for r in rows)
            cursor.execute("UPDATE performance_reviews SET overall_rating=%s WHERE id=%s",
                           (round(ws/tw, 1) if tw else 0, rev[0]))
            db.commit()

    cursor.close(); db.close()
    return redirect(f"/performance_review/{emp_id}?quarter={q}&year={yr}")


@app.route("/performance_delete_kpi", methods=["POST"])
@admin_required
def performance_delete_kpi():
    kpi_id = int(request.form["kpi_id"])
    emp_id = request.form["employee_id"]
    q      = int(request.form["quarter"])
    yr     = int(request.form["year"])
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM performance_kpis WHERE id=%s", (kpi_id,))
    db.commit()
    cursor.close(); db.close()
    return redirect(f"/performance_review/{emp_id}?quarter={q}&year={yr}")


@app.route("/my_performance")
@employee_required
def my_performance():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT pr.id, pr.quarter, pr.year, pr.overall_rating, pr.reviewer_feedback,
               pr.employee_comment, pr.status, pr.updated_at
        FROM performance_reviews pr
        WHERE pr.employee_id=%s ORDER BY pr.year DESC, pr.quarter DESC
    """, (emp_id,))
    reviews = cursor.fetchall()

    reviews_data = []
    for rev in reviews:
        cursor.execute("""
            SELECT kpi_title, target, achievement, weight, rating, comments
            FROM performance_kpis WHERE review_id=%s ORDER BY id
        """, (rev[0],))
        kpis = cursor.fetchall()
        reviews_data.append({"review": rev, "kpis": kpis})

    cursor.execute("SELECT name, COALESCE(role,''), COALESCE(department,''), face_image FROM employees WHERE employee_id=%s", (emp_id,))
    emp_info = cursor.fetchone()
    cursor.close(); db.close()

    return render_template("my_performance.html",
        reviews_data=reviews_data, emp_info=emp_info,
        emp_id=emp_id, rating_labels=RATING_LABELS
    )


@app.route("/performance_employee_comment", methods=["POST"])
@employee_required
def performance_employee_comment():
    rev_id  = int(request.form["review_id"])
    comment = request.form.get("comment", "").strip()
    emp_id  = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    # Only allow comment on own review
    cursor.execute("UPDATE performance_reviews SET employee_comment=%s WHERE id=%s AND employee_id=%s",
                   (comment, rev_id, emp_id))
    db.commit()
    cursor.close(); db.close()
    flash("Comment submitted.", "success")
    return redirect("/my_performance")


@app.route("/leave_requests")
@admin_required
def leave_requests_view():
    today  = datetime.date.today()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Leave requests with leave type name + half_day flag
    cursor.execute("""
        SELECT lr.id, e.name, lr.employee_id, lr.leave_date, lr.reason, lr.status, lr.created_at,
               COALESCE(lt.name, 'Leave Request') AS leave_type_name,
               COALESCE(lr.is_half_day, 0) AS is_half_day,
               lr.half_day_session
        FROM leave_requests lr
        JOIN employees e ON lr.employee_id = e.employee_id
        LEFT JOIN leave_types lt ON lr.leave_type_id = lt.id
        ORDER BY FIELD(lr.status, 'Pending', 'Approved', 'Rejected'), lr.created_at DESC
    """)
    leaves = cursor.fetchall()

    # Approved leave days used per employee this year (half-day = 0.5)
    cursor.execute("""
        SELECT employee_id,
               SUM(CASE WHEN COALESCE(is_half_day,0)=1 THEN 0.5 ELSE 1 END)
        FROM leave_requests
        WHERE YEAR(leave_date) = YEAR(CURDATE()) AND status = 'Approved'
        GROUP BY employee_id
    """)
    leave_used = {row[0]: float(row[1]) for row in cursor.fetchall()}

    # Leave types for balance display
    cursor.execute("SELECT id, name, annual_quota FROM leave_types WHERE is_active=1 ORDER BY id")
    leave_types_list = cursor.fetchall()

    # All tickets
    cursor.execute("""
        SELECT t.id, t.employee_id, e.name, t.category, t.subject, t.description,
               t.priority, t.status, t.admin_response, t.created_at, t.updated_at
        FROM tickets t
        JOIN employees e ON t.employee_id = e.employee_id
        ORDER BY FIELD(t.status,'Open','In Progress','Resolved','Closed'), t.created_at DESC
    """)
    all_tickets = cursor.fetchall()

    # Resignations
    cursor.execute("""
        SELECT rr.id, e.name, rr.employee_id, rr.last_working_day, rr.reason, rr.status, rr.created_at
        FROM resignation_requests rr
        JOIN employees e ON rr.employee_id = e.employee_id
        ORDER BY FIELD(rr.status, 'Pending', 'Accepted', 'Declined'), rr.created_at DESC
    """)
    resignations = cursor.fetchall()

    # Pending / open counts
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    pending_tickets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]

    cursor.close(); db.close()
    return render_template("leave_requests.html",
        leaves=leaves,
        leave_used=leave_used,
        leave_types_list=leave_types_list,
        all_tickets=all_tickets,
        resignations=resignations,
        pending_leaves=pending_leaves,
        pending_tickets=pending_tickets,
        pending_resignations=pending_resignations,
        today=today,
    )


@app.route("/leave_action/<int:lid>", methods=["POST"])
@admin_required
def leave_action(lid):
    action = request.form.get("action", "")
    if action not in ("Approved", "Rejected"):
        return redirect("/leave_requests")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Fetch leave + employee details before updating
    cursor.execute("""
        SELECT lr.employee_id, lr.leave_date, lr.reason,
               e.name, e.email, COALESCE(lr.is_half_day, 0)
        FROM leave_requests lr
        JOIN employees e ON e.employee_id = lr.employee_id
        WHERE lr.id = %s
    """, (lid,))
    leave_row = cursor.fetchone()

    # Fetch leave_type_id before updating
    cursor.execute("SELECT leave_type_id FROM leave_requests WHERE id=%s", (lid,))
    lt_row = cursor.fetchone()
    leave_type_id = lt_row[0] if lt_row else None

    cursor.execute("UPDATE leave_requests SET status=%s WHERE id=%s", (action, lid))

    if action == "Approved" and leave_row:
        emp_id, leave_date, _, _, _, is_half = leave_row
        att_type = 'Half Day' if is_half else 'Approved Leave'
        cursor.execute("""
            INSERT INTO attendance (employee_id, date, attendance_type)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE attendance_type=%s
        """, (emp_id, leave_date, att_type, att_type))
        # Deduct leave balance
        deduction = 0.5 if is_half else 1
        if leave_type_id:
            year = leave_date.year if hasattr(leave_date, 'year') else datetime.date.today().year
            cursor.execute("""
                INSERT INTO leave_balances (employee_id, leave_type_id, year, total_days, used_days)
                VALUES (%s, %s, %s,
                    (SELECT annual_quota FROM leave_types WHERE id=%s),
                    %s)
                ON DUPLICATE KEY UPDATE used_days = used_days + %s
            """, (emp_id, leave_type_id, year, leave_type_id, deduction, deduction))
            # Deduct comp-off balance if this is a Comp-off leave type
            cursor.execute("SELECT name FROM leave_types WHERE id=%s", (leave_type_id,))
            lt_name_row = cursor.fetchone()
            if lt_name_row and lt_name_row[0] == 'Comp-off':
                cfg_cur = db.cursor(buffered=True)
                cfg_cur.execute("SELECT COALESCE(compoff_minutes_per_day,480) FROM company_settings LIMIT 1")
                mpd_row = cfg_cur.fetchone()
                cfg_cur.close()
                mpd = int(mpd_row[0]) if mpd_row else 480
                deduct_minutes = int(deduction * mpd)
                cursor.execute("""
                    INSERT INTO compoff_balance (employee_id, earned_minutes, used_minutes)
                    VALUES (%s, 0, %s)
                    ON DUPLICATE KEY UPDATE used_minutes = used_minutes + %s
                """, (emp_id, deduct_minutes, deduct_minutes))

    db.commit()
    cursor.close(); db.close()

    # Send email + in-app notification to employee
    if leave_row:
        emp_id, leave_date, reason, emp_name, emp_email, _ = leave_row
        icon = "✅" if action == "Approved" else "❌"
        _create_notification(
            'employee',
            f"{icon} Leave Request {action}",
            f"Your leave request for {leave_date} has been {action.lower()}.",
            emp_id
        )
        if not emp_email:
            flash(f"Leave {action} but no email on record for {emp_name} — notification not sent.", "warning")
        else:
            cfg = get_email_config()
            if not cfg:
                flash("Leave updated but SMTP not configured — email not sent.", "warning")
            else:
                color    = "#16a34a" if action == "Approved" else "#dc2626"
                icon     = "✅" if action == "Approved" else "❌"
                date_str = leave_date.strftime('%d %b %Y') if hasattr(leave_date, 'strftime') else str(leave_date)
                html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="background:linear-gradient(135deg,{color},{color}cc);padding:24px;color:white;text-align:center;">
    <h2 style="margin:0;font-size:22px;">{icon} Leave {action}</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px;">Employee Attendance System</p>
  </div>
  <div style="padding:28px 32px;">
    <p style="font-size:15px;color:#1e293b;">Hi <strong>{emp_name}</strong>,</p>
    <p style="font-size:14px;color:#475569;margin-top:10px;">
      Your leave request for <strong>{date_str}</strong> has been
      <strong style="color:{color};">{action.lower()}</strong>.
    </p>
    <div style="background:#f8fafc;border-left:4px solid {color};border-radius:8px;padding:14px 18px;margin:20px 0;">
      <p style="margin:0;font-size:13px;color:#64748b;">📅 <strong>Date:</strong> {date_str}</p>
      <p style="margin:6px 0 0;font-size:13px;color:#64748b;">📝 <strong>Reason:</strong> {reason or '—'}</p>
      <p style="margin:6px 0 0;font-size:13px;color:#64748b;">📌 <strong>Status:</strong> <span style="color:{color};font-weight:700;">{action}</span></p>
    </div>
    <p style="font-size:13px;color:#94a3b8;margin-top:20px;">For queries, contact your HR administrator.</p>
  </div>
  <div style="background:#f1f5f9;padding:14px;text-align:center;font-size:11px;color:#94a3b8;">
    Employee Attendance System &bull; Automated Notification
  </div>
</div>"""
                try:
                    send_email_smtp(emp_email, f"Leave {action} — {date_str}", html_body, cfg)
                    flash(f"{icon} Leave {action} — email sent to {emp_email}", "success")
                except Exception as _e:
                    flash(f"Leave {action} but email failed: {_e}", "error")

    return redirect("/leave_requests")




@app.route("/leave_calendar")
@admin_required
def leave_calendar():
    import calendar as cal_mod
    from collections import defaultdict
    today = datetime.date.today()
    year  = int(request.args.get("year",  today.year))
    month = int(request.args.get("month", today.month))
    if month < 1:  month = 12; year -= 1
    if month > 12: month = 1;  year += 1

    _, last_day = cal_mod.monthrange(year, month)
    start_date  = datetime.date(year, month, 1)
    end_date    = datetime.date(year, month, last_day)

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT lr.leave_date, e.name, lr.employee_id,
               COALESCE(lr.is_half_day,0),
               COALESCE(lt.name,'Leave') AS leave_type,
               lr.half_day_session
        FROM leave_requests lr
        JOIN employees e ON lr.employee_id = e.employee_id
        LEFT JOIN leave_types lt ON lr.leave_type_id = lt.id
        WHERE lr.status = 'Approved'
          AND lr.leave_date BETWEEN %s AND %s
        ORDER BY lr.leave_date, e.name
    """, (start_date, end_date))
    cal_data = defaultdict(list)
    for ld, name, eid, half, ltype, session in cursor.fetchall():
        day = ld.day if hasattr(ld, 'day') else int(str(ld)[8:10])
        cal_data[day].append({"name": name, "emp_id": eid,
                               "is_half": bool(half), "leave_type": ltype,
                               "session": session or "Morning"})

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.close(); db.close()

    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1

    return render_template("leave_calendar.html",
        cal_weeks=cal_mod.monthcalendar(year, month),
        cal_data=dict(cal_data),
        year=year, month=month,
        month_name=cal_mod.month_name[month],
        today=today,
        prev_m=prev_m, prev_y=prev_y,
        next_m=next_m, next_y=next_y,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    )


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
            app_log.error('"Resignation notification email failed: %s"', e)

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
    if action not in ("Accepted", "Declined"):
        return redirect("/resignation_requests")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT rr.employee_id, rr.last_working_day, rr.reason,
               e.name, e.email
        FROM resignation_requests rr
        JOIN employees e ON e.employee_id = rr.employee_id
        WHERE rr.id = %s
    """, (rid,))
    resign_row = cursor.fetchone()
    cursor.execute("UPDATE resignation_requests SET status=%s WHERE id=%s", (action, rid))
    db.commit()
    cursor.close(); db.close()

    if resign_row:
        emp_id, lwd, reason, emp_name, emp_email = resign_row
        icon = "✅" if action == "Accepted" else "❌"
        _create_notification(
            'employee',
            f"{icon} Resignation {action}",
            f"Your resignation request has been {action.lower()}.",
            emp_id
        )
        if emp_email:
            cfg = get_email_config()
            if cfg:
                color   = "#16a34a" if action == "Accepted" else "#dc2626"
                icon    = "✅" if action == "Accepted" else "❌"
                lwd_str = lwd.strftime('%d %b %Y') if hasattr(lwd, 'strftime') else str(lwd)
                html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="background:linear-gradient(135deg,{color},{color}cc);padding:24px;color:white;text-align:center;">
    <h2 style="margin:0;font-size:22px;">{icon} Resignation {action}</h2>
    <p style="margin:4px 0 0;opacity:.85;font-size:13px;">Employee Attendance System</p>
  </div>
  <div style="padding:28px 32px;">
    <p style="font-size:15px;color:#1e293b;">Hi <strong>{emp_name}</strong>,</p>
    <p style="font-size:14px;color:#475569;margin-top:10px;">
      Your resignation request has been <strong style="color:{color};">{action.lower()}</strong>.
    </p>
    <div style="background:#f8fafc;border-left:4px solid {color};border-radius:8px;padding:14px 18px;margin:20px 0;">
      <p style="margin:0;font-size:13px;color:#64748b;">📅 <strong>Last Working Day:</strong> {lwd_str}</p>
      <p style="margin:6px 0 0;font-size:13px;color:#64748b;">📝 <strong>Reason:</strong> {reason or '—'}</p>
      <p style="margin:6px 0 0;font-size:13px;color:#64748b;">📌 <strong>Status:</strong> <span style="color:{color};font-weight:700;">{action}</span></p>
    </div>
    <p style="font-size:13px;color:#94a3b8;margin-top:20px;">For queries, contact your HR administrator.</p>
  </div>
  <div style="background:#f1f5f9;padding:14px;text-align:center;font-size:11px;color:#94a3b8;">
    Employee Attendance System &bull; Automated Notification
  </div>
</div>"""
                send_email_async(emp_email, f"Resignation {action} — {emp_name}", html_body, cfg)

    return redirect("/resignation_requests")


@app.route("/bulk_leave_action", methods=["POST"])
@admin_required
def bulk_leave_action():
    action   = request.form.get("action", "")
    raw_ids  = request.form.getlist("leave_ids")
    if action not in ("Approved", "Rejected") or not raw_ids:
        return redirect("/leave_requests")
    try:
        ids = [int(i) for i in raw_ids]
    except ValueError:
        return redirect("/leave_requests")

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    done   = 0
    cfg    = get_email_config()

    for lid in ids:
        cursor.execute("""
            SELECT lr.employee_id, lr.leave_date, lr.reason, e.name, e.email
            FROM leave_requests lr
            JOIN employees e ON e.employee_id = lr.employee_id
            WHERE lr.id = %s AND lr.status = 'Pending'
        """, (lid,))
        row = cursor.fetchone()
        if not row:
            continue
        emp_id, leave_date, reason, emp_name, emp_email = row
        cursor.execute("UPDATE leave_requests SET status=%s WHERE id=%s", (action, lid))
        if action == "Approved":
            cursor.execute("""
                INSERT INTO attendance (employee_id, date, attendance_type)
                VALUES (%s, %s, 'Approved Leave')
                ON DUPLICATE KEY UPDATE attendance_type='Approved Leave'
            """, (emp_id, leave_date))
        done += 1
        if emp_email and cfg:
            color    = "#16a34a" if action == "Approved" else "#dc2626"
            icon     = "✅" if action == "Approved" else "❌"
            date_str = leave_date.strftime('%d %b %Y') if hasattr(leave_date, 'strftime') else str(leave_date)
            html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
  <div style="background:{color};padding:20px;color:white;text-align:center;">
    <h2 style="margin:0;">{icon} Leave {action}</h2>
  </div>
  <div style="padding:24px;">
    <p>Hi <strong>{emp_name}</strong>, your leave request for <strong>{date_str}</strong> has been
    <strong style="color:{color};">{action.lower()}</strong>.</p>
    <p style="font-size:12px;color:#94a3b8;margin-top:16px;">Employee Attendance System &bull; Automated Notification</p>
  </div>
</div>"""
            send_email_async(emp_email, f"Leave {action} — {date_str}", html_body, cfg)

    db.commit()
    cursor.close(); db.close()
    flash(f"Bulk action: {action} applied to {done} leave request(s).", "success")
    return redirect("/leave_requests")


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
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if new_status not in allowed:
        return (jsonify({"ok": False, "msg": "Invalid status."}), 400) if is_ajax else redirect("/tickets")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT t.subject, t.category, t.priority, t.description,
               e.name, e.email
        FROM tickets t
        JOIN employees e ON t.employee_id = e.employee_id
        WHERE t.id = %s
    """, (tid,))
    row = cursor.fetchone()

    cursor.execute(
        "UPDATE tickets SET status=%s, admin_response=%s WHERE id=%s",
        (new_status, admin_response or None, tid)
    )
    db.commit(); cursor.close(); db.close()

    msg = ""
    msg_type = "success"
    if row and admin_response:
        subject_text, category, priority, description, emp_name, emp_email = row
        if emp_email:
            _ecfg = get_email_config()
            if _ecfg:
                status_color = {"Resolved": "#16a34a", "Closed": "#64748b",
                                "In Progress": "#d97706"}.get(new_status, "#2563eb")
                _html = f"""
<div style="font-family:'Segoe UI',sans-serif;max-width:560px;margin:0 auto;background:#f8fafc;border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:linear-gradient(135deg,#1e3a8a,#2563eb);padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">🎫 Ticket Update</div>
    <div style="font-size:13px;opacity:0.75;margin-top:4px;">Employee Attendance System</div>
  </div>
  <div style="padding:28px;">
    <p style="font-size:15px;color:#1e293b;margin-bottom:20px;">Hi <strong>{emp_name}</strong>, your ticket has been updated.</p>
    <div style="background:#fff;border:1px solid #dbeafe;border-radius:12px;padding:18px 20px;margin-bottom:20px;">
      <div style="font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Ticket Subject</div>
      <div style="font-size:15px;color:#1e293b;font-weight:700;margin-bottom:14px;">{subject_text}</div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <span style="background:#dbeafe;color:#1d4ed8;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">{category}</span>
        <span style="background:#fef9c3;color:#92400e;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">{priority} Priority</span>
        <span style="background:{status_color}22;color:{status_color};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">{new_status}</span>
      </div>
    </div>
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:12px;padding:18px 20px;margin-bottom:20px;">
      <div style="font-size:12px;color:#15803d;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Admin Response</div>
      <div style="font-size:14px;color:#1e293b;white-space:pre-line;">{admin_response}</div>
    </div>
    <p style="font-size:12px;color:#94a3b8;text-align:center;margin:0;">This is an automated message — please do not reply.</p>
  </div>
</div>"""
                try:
                    send_email_smtp(emp_email, f"Ticket Update: {subject_text}", _html, _ecfg)
                    msg = f"✅ Ticket updated — email sent to {emp_email}"
                except Exception as _e:
                    msg = f"⚠️ Ticket updated but email failed: {_e}"
                    msg_type = "warning"
            else:
                msg = "Ticket updated. SMTP not configured — email not sent."
                msg_type = "warning"
        else:
            msg = "Ticket updated. Employee has no email on record."
            msg_type = "warning"
    else:
        msg = "✅ Ticket status updated."

    if is_ajax:
        return jsonify({"ok": True, "msg": msg, "type": msg_type, "new_status": new_status})
    flash(msg, msg_type)
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
        with _db() as (cursor, _conn):
            # Clean up expired tokens opportunistically
            cursor.execute("DELETE FROM api_tokens WHERE expires_at < NOW()")
            _conn.commit()
            cursor.execute(
                "SELECT identity FROM api_tokens WHERE token=%s AND token_type='admin' AND expires_at > NOW()",
                (token,)
            )
            row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        from flask import g as _g
        _g.api_user = row[0]
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/login", methods=["POST"])
@limiter.limit("20 per minute")
def api_login():
    data     = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    with _db() as (cursor, conn):
        cursor.execute("SELECT password FROM admin_users WHERE username=%s", (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[0], password):
            token = secrets.token_hex(32)
            cursor.execute(
                "INSERT INTO api_tokens (token, token_type, identity, expires_at) "
                "VALUES (%s, 'admin', %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))",
                (token, username)
            )
            conn.commit()
            return jsonify({"ok": True, "token": token, "username": username})
    return jsonify({"ok": False, "msg": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        with _db() as (cursor, conn):
            cursor.execute("DELETE FROM api_tokens WHERE token=%s", (auth[7:],))
            conn.commit()
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
    cursor.execute("DELETE FROM attendance WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM salary_config WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM leave_requests WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM resignation_requests WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM tickets WHERE employee_id=%s", (emp_id,))
    cursor.execute("DELETE FROM employees WHERE employee_id=%s", (emp_id,))
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
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=15)).time()
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
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, leave_date FROM leave_requests WHERE id=%s", (lid,))
    row = cursor.fetchone()
    cursor.execute("UPDATE leave_requests SET status=%s WHERE id=%s", (action, lid))
    db.commit(); cursor.close(); db.close()
    if row:
        icon = "✅" if action == "Approved" else "❌"
        _create_notification(
            'employee',
            f"{icon} Leave Request {action}",
            f"Your leave request for {row[1]} has been {action.lower()}.",
            row[0]
        )
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
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, last_working_day FROM resignation_requests WHERE id=%s", (rid,))
    row = cursor.fetchone()
    cursor.execute("UPDATE resignation_requests SET status=%s WHERE id=%s", (action, rid))
    db.commit(); cursor.close(); db.close()
    if row:
        icon = "✅" if action == "Accepted" else "❌"
        _create_notification(
            'employee',
            f"{icon} Resignation {action}",
            f"Your resignation request (last working day: {row[1]}) has been {action.lower()}.",
            row[0]
        )
    return jsonify({"ok": True, "status": action})


def employee_api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        token = auth[7:]
        with _db() as (cursor, _conn):
            # Clean up expired tokens opportunistically
            cursor.execute("DELETE FROM api_tokens WHERE expires_at < NOW()")
            _conn.commit()
            cursor.execute(
                "SELECT identity FROM api_tokens WHERE token=%s AND token_type='employee' AND expires_at > NOW()",
                (token,)
            )
            row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        from flask import g as _g
        _g.api_emp_id = row[0]
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/employee/login", methods=["POST"])
def api_employee_login():
    data   = request.get_json() or {}
    emp_id = data.get("employee_id", "").strip()
    password = data.get("password", "").strip()
    if not emp_id:
        return jsonify({"ok": False, "msg": "employee_id required"}), 400
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT name, email, password FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    if not password:
        return jsonify({"ok": False, "msg": "Password required"}), 400
    if not row[2] or not check_password_hash(row[2], password):
        return jsonify({"ok": False, "msg": "Invalid password"}), 401
    token = secrets.token_hex(32)
    with _db() as (cursor, conn):
        cursor.execute(
            "INSERT INTO api_tokens (token, token_type, identity, expires_at) "
            "VALUES (%s, 'employee', %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))",
            (token, emp_id)
        )
        conn.commit()
    return jsonify({"ok": True, "token": token, "employee_id": emp_id,
                    "name": row[0], "email": row[1]})


@app.route("/api/employee/logout", methods=["POST"])
def api_employee_logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        with _db() as (cursor, conn):
            cursor.execute("DELETE FROM api_tokens WHERE token=%s", (auth[7:],))
            conn.commit()
    return jsonify({"ok": True})


@app.route("/api/employee/change-password", methods=["POST"])
@employee_api_required
def api_employee_change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "").strip()
    new_password     = data.get("new_password", "").strip()
    if not current_password or not new_password:
        return jsonify({"ok": False, "msg": "current_password and new_password required"}), 400
    if len(new_password) < 4:
        return jsonify({"ok": False, "msg": "New password must be at least 4 characters"}), 400
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


def _fmt_t(t):
    if t is None: return None
    if hasattr(t, 'strftime'): return t.strftime("%H:%M:%S")
    total = int(t.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)


@app.route("/api/employee/portal", methods=["GET"])
@employee_api_required
def api_employee_portal():
    from flask import g as _g
    emp_id = _g.api_emp_id
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
    cursor.execute(
        "SELECT COUNT(*) FROM notifications WHERE recipient_type='employee' AND employee_id=%s AND is_read=FALSE",
        (emp_id,)
    )
    unread_notifications = cursor.fetchone()[0]
    cursor.execute("""
        SELECT title, content, priority, created_at FROM announcements
        ORDER BY created_at DESC LIMIT 5
    """)
    ann_rows = cursor.fetchall()
    cursor.execute("SELECT role, department FROM employees WHERE employee_id=%s", (emp_id,))
    emp_extra = cursor.fetchone()
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
        "unread_notifications": unread_notifications,
        "role": emp_extra[0] if emp_extra else None,
        "department": emp_extra[1] if emp_extra else None,
        "announcements": [
            {"title": r[0], "content": r[1], "priority": r[2], "created_at": str(r[3])}
            for r in ann_rows
        ],
    })


@app.route("/api/employee/checkin", methods=["POST"])
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
        if work_mode == 'wfh':
            if work_lat and work_lon:
                if not is_within_range(float(lat), float(lon), float(work_lat), float(work_lon)):
                    cursor.close(); db.close()
                    return jsonify({"ok": False, "msg": "You are outside your registered home location."})
        else:
            if not is_within_range(float(lat), float(lon), OFFICE_LAT, OFFICE_LON):
                cursor.close(); db.close()
                return jsonify({"ok": False, "msg": "You are outside the office premises."})

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
    login_status        = record[2] if record else None
    worked_mins_stored  = (record[3] or 0) if record else 0
    last_relogin_stored = record[4] if record else None

    if not login_time:
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=15)).time()
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


@app.route("/api/employee/qr-face-checkin", methods=["POST"])
def api_employee_qr_face_checkin():
    """Public kiosk endpoint: QR code + face photo attendance marking (no auth token required)."""
    employee_id = request.form.get("employee_id", "").strip().upper()
    lat         = request.form.get("lat")
    lon         = request.form.get("lon")
    face_photo  = request.files.get("face_photo")

    if not employee_id:
        return jsonify({"ok": False, "msg": "employee_id required"}), 400

    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT name, work_mode, work_lat, work_lon FROM employees WHERE employee_id=%s",
        (employee_id,)
    )
    result = cursor.fetchone()
    if not result:
        cursor.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404
    employee_name, work_mode, work_lat, work_lon = result

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

    if face_photo:
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
        grace_time = (datetime.datetime.combine(today, SHIFT_START) + datetime.timedelta(minutes=15)).time()
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


@app.route("/api/employee/leave_request", methods=["POST"])
@employee_api_required
def api_employee_leave_request():
    from flask import g as _g
    emp_id     = _g.api_emp_id
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
    _create_notification(
        'admin',
        "📋 New Leave Request",
        f"Employee {emp_id} has submitted a leave request for {leave_date}. Reason: {reason}"
    )
    return jsonify({"ok": True, "msg": "Leave request submitted."})


@app.route("/api/employee/resign", methods=["POST"])
@employee_api_required
def api_employee_resign():
    from flask import g as _g
    emp_id           = _g.api_emp_id
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
    _create_notification(
        'admin',
        "📤 New Resignation Request",
        f"Employee {emp_name} ({emp_id}) has submitted a resignation. Last working day: {last_working_day}."
    )
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
            app_log.error('"Resignation notification email failed: %s"', e)
    cursor.close(); db.close()
    return jsonify({"ok": True, "msg": "Resignation submitted successfully."})


# ---------------- API: TICKETS (employee) ----------------

@app.route("/api/employee/tickets", methods=["GET"])
@employee_api_required
def api_employee_tickets():
    from flask import g as _g
    emp_id = _g.api_emp_id
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
    from flask import g as _g
    emp_id      = _g.api_emp_id
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



@app.route("/api/employee/salary", methods=["GET"])
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


# ---------------- API: EMPLOYEE — ATTENDANCE HISTORY ----------------

@app.route("/api/employee/attendance", methods=["GET"])
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
        WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s
        ORDER BY date DESC
    """, (emp_id, month, year))
    rows = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*), attendance_type FROM attendance
        WHERE employee_id=%s AND MONTH(date)=%s AND YEAR(date)=%s
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


# ---------------- API: EMPLOYEE — LEAVE HISTORY + BALANCE ----------------

@app.route("/api/employee/leaves", methods=["GET"])
@employee_api_required
def api_employee_leaves():
    from flask import g as _g
    emp_id = _g.api_emp_id
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT id, leave_date, reason, status, created_at
        FROM leave_requests WHERE employee_id=%s
        ORDER BY created_at DESC LIMIT 50
    """, (emp_id,))
    leaves = cursor.fetchall()
    approved = sum(1 for r in leaves if r[3] == "Approved")
    pending  = sum(1 for r in leaves if r[3] == "Pending")
    rejected = sum(1 for r in leaves if r[3] == "Rejected")
    cursor.close(); db.close()
    return jsonify({
        "ok": True,
        "summary": {"approved": approved, "pending": pending, "rejected": rejected, "total": len(leaves)},
        "leaves": [
            {"id": r[0], "leave_date": str(r[1]), "reason": r[2], "status": r[3], "created_at": str(r[4])}
            for r in leaves
        ],
    })


# ---------------- API: EMPLOYEE — HOLIDAYS ----------------

@app.route("/api/employee/holidays", methods=["GET"])
@employee_api_required
def api_employee_holidays():
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT date, name FROM holidays ORDER BY date")
    rows = cursor.fetchall()
    cursor.close(); db.close()
    today = datetime.date.today()
    return jsonify({
        "ok": True,
        "holidays": [
            {"date": str(r[0]), "name": r[1], "passed": r[0] < today}
            for r in rows
        ],
    })


# ---------------- API: EMPLOYEE — PROFILE ----------------

@app.route("/api/employee/profile", methods=["GET"])
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
               COALESCE(s.salary_per_day, 0), COALESCE(e.joining_date, e.date_of_joining)
        FROM employees e
        LEFT JOIN salary_config s ON e.employee_id = s.employee_id
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
            "bank_name": row[16], "bank_account": row[17], "bank_ifsc": row[18],
            "pan_number": row[19], "aadhar_number": row[20],
            "salary_per_day": float(row[21]),
            "join_date": str(row[22]) if row[22] else None,
            "photo_url": f"/dataset/{row[0]}.jpg",
        },
    })


@app.route("/api/employee/photo", methods=["POST"])
@employee_api_required
def api_employee_upload_photo():
    from flask import g as _g
    from PIL import Image
    emp_id = _g.api_emp_id
    file = request.files.get("photo")
    if not file:
        return jsonify({"ok": False, "msg": "No photo provided"}), 400
    ext = os.path.splitext(file.filename.lower())[1] if file.filename else ""
    if ext not in (".jpg", ".jpeg", ".png"):
        return jsonify({"ok": False, "msg": "Only JPG/PNG files allowed"}), 400
    try:
        img = Image.open(file.stream).convert("RGB")
        save_path = os.path.join(UPLOAD_FOLDER, emp_id + ".jpg")
        img.save(save_path, "JPEG", quality=85)
        return jsonify({"ok": True, "msg": "Photo uploaded successfully", "photo_url": f"/dataset/{emp_id}.jpg"})
    except Exception:
        return jsonify({"ok": False, "msg": "Failed to process image"}), 500


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


@app.route("/payroll_settings", methods=["GET", "POST"])
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
                    ON DUPLICATE KEY UPDATE salary_per_day=%s, monthly_ctc=%s, basic_pct=%s
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



# ================================================================
#  FEATURE 1: ANALYTICS
# ================================================================

@app.route("/analytics")
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

    cursor.execute(
        "SELECT COUNT(*) FROM employees WHERE MONTH(date_of_joining)=%s AND YEAR(date_of_joining)=%s",
        (today.month, today.year)
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
        cursor.execute("""
            SELECT COUNT(DISTINCT employee_id) FROM attendance
            WHERE MONTH(date)=%s AND YEAR(date)=%s AND login_time IS NOT NULL
        """, (m, y))
        present_records = cursor.fetchone()[0]
        expected = total_days * (total_employees or 1)
        present_pct = round(present_records / expected * 100, 1) if expected else 0
        monthly_series.append({
            'month_label': datetime.date(y, m, 1).strftime("%b %Y"),
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
            cursor.execute("""
                SELECT COUNT(DISTINCT employee_id) FROM attendance
                WHERE MONTH(date)=%s AND YEAR(date)=%s AND login_time IS NOT NULL
            """, (m, y))
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
        WHERE lr.status='Approved' AND YEAR(lr.leave_date)=%s
        GROUP BY lt.name ORDER BY cnt DESC
    """, (today.year,))
    leave_by_type = [{'name': r[0], 'count': r[1]} for r in cursor.fetchall()]

    cursor.execute("""
        SELECT e.employee_id, e.name,
               ROUND(COUNT(CASE WHEN a.login_time IS NOT NULL THEN 1 END) / GREATEST(DATEDIFF(LEAST(LAST_DAY(%s), %s), %s) + 1, 1) * 100, 1) AS pct
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND MONTH(a.date)=%s AND YEAR(a.date)=%s
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
        LEFT JOIN attendance a ON e.employee_id=a.employee_id AND MONTH(a.date)=%s AND YEAR(a.date)=%s
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
            except: continue
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
            AND MONTH(a.date)=%s AND YEAR(a.date)=%s
        GROUP BY e.employee_id, e.name
        HAVING total_days > 0 AND (present_days / total_days) < 0.5
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
    )


# ================================================================
#  FEATURE 2: DOCUMENT MANAGEMENT
# ================================================================

_DOC_ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

def _allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in _DOC_ALLOWED_EXT

def _doc_admin_ctx(cursor):
    cursor.execute("SELECT company_name FROM company_settings LIMIT 1")
    row = cursor.fetchone()
    co = type('Co', (), {'company_name': row[0] if row else 'My Company'})()
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    return co, pending_leaves, pending_resignations, pending_tickets


@app.route("/documents")
@admin_required
def documents():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    co, pending_leaves, pending_resignations, pending_tickets = _doc_admin_ctx(cursor)

    cursor.execute("SELECT employee_id, name FROM employees ORDER BY name")
    employees = cursor.fetchall()

    sel_emp = request.args.get('emp_id', '')
    sel_emp_name = ''

    if sel_emp:
        cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (sel_emp,))
        r = cursor.fetchone()
        sel_emp_name = r[0] if r else sel_emp
        cursor.execute("""
            SELECT d.id, d.employee_id, e.name, d.doc_type, d.original_name, d.stored_name,
                   d.uploaded_by, d.uploaded_at
            FROM employee_documents d JOIN employees e ON e.employee_id=d.employee_id
            WHERE d.employee_id=%s ORDER BY d.uploaded_at DESC
        """, (sel_emp,))
    else:
        cursor.execute("""
            SELECT d.id, d.employee_id, e.name, d.doc_type, d.original_name, d.stored_name,
                   d.uploaded_by, d.uploaded_at
            FROM employee_documents d JOIN employees e ON e.employee_id=d.employee_id
            ORDER BY d.uploaded_at DESC
        """)
    docs = cursor.fetchall()
    cursor.close(); db.close()

    return render_template("documents.html",
        co=co,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        employees=employees, docs=docs,
        sel_emp=sel_emp, sel_emp_name=sel_emp_name,
    )


@app.route("/upload_document", methods=["POST"])
@admin_required
def upload_document():
    emp_id   = request.form.get('employee_id', '').strip()
    doc_type = request.form.get('doc_type', '').strip()
    f        = request.files.get('document')
    if not emp_id or not doc_type or not f or not f.filename:
        flash("All fields required.", "danger")
        return redirect('/documents')
    if not _allowed_doc(f.filename):
        flash("Invalid file type. Allowed: pdf, jpg, jpeg, png, doc, docx", "danger")
        return redirect(f'/documents?emp_id={emp_id}')
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'employee_docs', emp_id)
    os.makedirs(folder, exist_ok=True)
    orig_name    = f.filename
    stored_name  = str(uuid.uuid4()) + '_' + secure_filename(orig_name)
    f.save(os.path.join(folder, stored_name))
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO employee_documents (employee_id, doc_type, original_name, stored_name, uploaded_by) VALUES (%s,%s,%s,%s,'admin')",
        (emp_id, doc_type, orig_name, stored_name)
    )
    db.commit(); cursor.close(); db.close()
    flash("Document uploaded successfully.", "success")
    redirect_to = request.form.get('redirect_to') or f'/documents?emp_id={emp_id}'
    return redirect(redirect_to)


@app.route("/delete_document/<int:did>", methods=["POST"])
@admin_required
def delete_document(did):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, stored_name FROM employee_documents WHERE id=%s", (did,))
    row = cursor.fetchone()
    if row:
        emp_id, stored_name = row
        fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'employee_docs', emp_id, stored_name)
        try:
            os.remove(fpath)
        except Exception:
            pass
        cursor.execute("DELETE FROM employee_documents WHERE id=%s", (did,))
        db.commit()
    cursor.close(); db.close()
    flash("Document deleted.", "success")
    return redirect(request.referrer or '/documents')



@app.route("/download_document/<int:did>")
def download_document(did):
    is_admin = session.get("admin_logged_in")
    emp_session = session.get("employee_id")
    if not is_admin and not emp_session:
        return redirect("/employee_login")
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, original_name, stored_name FROM employee_documents WHERE id=%s", (did,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if not row:
        flash("Document not found.", "danger")
        return redirect('/documents')
    doc_emp_id, original_name, stored_name = row
    if not is_admin and emp_session != doc_emp_id:
        flash("Access denied.", "danger")
        return redirect('/employee_portal')
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'employee_docs', doc_emp_id)
    return send_from_directory(folder, stored_name, as_attachment=True, download_name=original_name)


@app.route("/upload_my_document", methods=["POST"])
def upload_my_document():
    emp_id = session.get("employee_id")
    if not emp_id:
        return redirect("/employee_login")
    doc_type = request.form.get('doc_type', '').strip()
    f        = request.files.get('document')
    if not doc_type or not f or not f.filename:
        flash("All fields required.", "danger")
        return redirect('/employee_portal')
    if not _allowed_doc(f.filename):
        flash("Invalid file type. Allowed: pdf, jpg, jpeg, png, doc, docx", "danger")
        return redirect('/employee_portal')
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'employee_docs', emp_id)
    os.makedirs(folder, exist_ok=True)
    orig_name   = f.filename
    stored_name = str(uuid.uuid4()) + '_' + secure_filename(orig_name)
    f.save(os.path.join(folder, stored_name))
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO employee_documents (employee_id, doc_type, original_name, stored_name, uploaded_by) VALUES (%s,%s,%s,%s,'employee')",
        (emp_id, doc_type, orig_name, stored_name)
    )
    db.commit(); cursor.close(); db.close()
    flash("Document uploaded successfully.", "success")
    return redirect('/employee_portal#documents')


@app.route("/delete_my_document/<int:did>", methods=["POST"])
def delete_my_document(did):
    emp_id = session.get("employee_id")
    if not emp_id:
        return redirect("/employee_login")
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, stored_name FROM employee_documents WHERE id=%s AND employee_id=%s", (did, emp_id))
    row = cursor.fetchone()
    if row:
        fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'employee_docs', emp_id, row[1])
        try:
            os.remove(fpath)
        except Exception:
            pass
        cursor.execute("DELETE FROM employee_documents WHERE id=%s AND employee_id=%s", (did, emp_id))
        db.commit()
    cursor.close(); db.close()
    flash("Document deleted.", "success")
    return redirect('/employee_portal#documents')


# ================================================================
#  FEATURE 3: OVERTIME TRACKING
# ================================================================

@app.route("/overtime")
@admin_required
def overtime():
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
    month = int(request.args.get('month', today.month))
    year  = int(request.args.get('year',  today.year))
    active_tab = request.args.get('tab', 'ot')

    # OT records
    cursor.execute("""
        SELECT o.id, o.employee_id, e.name, o.date, o.shift_end, o.actual_logout,
               o.ot_minutes, o.ot_pay, o.status, o.notes
        FROM overtime_records o JOIN employees e ON e.employee_id=o.employee_id
        WHERE MONTH(o.date)=%s AND YEAR(o.date)=%s
        ORDER BY o.date DESC
    """, (month, year))
    records = cursor.fetchall()

    total_ot_minutes = sum(r[6] for r in records)
    total_ot_hours   = round(total_ot_minutes / 60, 1)
    total_ot_pay     = sum(float(r[7]) for r in records)
    pending_count    = sum(1 for r in records if r[8] == 'Pending')
    approved_count   = sum(1 for r in records if r[8] == 'Approved')

    # Comp-off settings
    cursor.execute("SELECT COALESCE(compoff_min_ot_minutes,120), COALESCE(compoff_minutes_per_day,480) FROM company_settings LIMIT 1")
    cfg = cursor.fetchone() or (120, 480)
    min_ot_minutes  = int(cfg[0])
    minutes_per_day = int(cfg[1])

    # Comp-off balances per employee
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(e.role,''), COALESCE(e.department,''),
               COALESCE(cb.earned_minutes,0), COALESCE(cb.used_minutes,0)
        FROM employees e
        LEFT JOIN compoff_balance cb ON cb.employee_id=e.employee_id
        ORDER BY e.name
    """)
    compoff_balances = []
    for emp_id, name, role, dept, earned, used in cursor.fetchall():
        earned_days = round(earned / minutes_per_day, 2) if minutes_per_day else 0
        used_days   = round(used   / minutes_per_day, 2) if minutes_per_day else 0
        avail_days  = max(0, round((earned - used) / minutes_per_day, 2)) if minutes_per_day else 0
        compoff_balances.append({
            "emp_id": emp_id, "name": name, "role": role, "dept": dept,
            "earned_min": earned, "used_min": used,
            "earned_days": earned_days, "used_days": used_days, "avail_days": avail_days
        })

    cursor.close(); db.close()

    return render_template("overtime.html",
        co=co,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
        records=records,
        month=month, year=year,
        month_name=datetime.date(year, month, 1).strftime("%B %Y"),
        total_ot_hours=total_ot_hours,
        total_ot_pay=total_ot_pay,
        pending_count=pending_count,
        approved_count=approved_count,
        active_tab=active_tab,
        min_ot_minutes=min_ot_minutes,
        minutes_per_day=minutes_per_day,
        compoff_balances=compoff_balances,
    )


@app.route("/overtime_action/<int:oid>", methods=["POST"])
@admin_required
def overtime_action(oid):
    action = request.form.get('action', '').strip()
    notes  = request.form.get('notes', '').strip()
    if action not in ('approve', 'reject'):
        flash("Invalid action.", "danger")
        return redirect('/overtime?tab=ot')
    status = 'Approved' if action == 'approve' else 'Rejected'
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Fetch OT record before updating
    cursor.execute("SELECT employee_id, ot_minutes, status FROM overtime_records WHERE id=%s", (oid,))
    ot_row = cursor.fetchone()

    cursor.execute(
        "UPDATE overtime_records SET status=%s, notes=%s WHERE id=%s",
        (status, notes or None, oid)
    )
    db.commit()

    # Credit comp-off balance when approving
    if status == 'Approved' and ot_row and ot_row[2] != 'Approved':
        emp_id     = ot_row[0]
        ot_minutes = ot_row[1]
        # Get compoff threshold settings
        cursor.execute("SELECT COALESCE(compoff_min_ot_minutes,120) FROM company_settings LIMIT 1")
        min_row = cursor.fetchone()
        min_ot  = int(min_row[0]) if min_row else 120
        if ot_minutes >= min_ot:
            cursor.execute("""
                INSERT INTO compoff_balance (employee_id, earned_minutes, used_minutes)
                VALUES (%s, %s, 0)
                ON DUPLICATE KEY UPDATE earned_minutes = earned_minutes + %s
            """, (emp_id, ot_minutes, ot_minutes))
            db.commit()
            flash(f"Overtime approved. {ot_minutes} OT minutes credited to comp-off balance.", "success")
        else:
            flash(f"Overtime approved. OT below threshold ({min_ot} min) — no comp-off credited.", "success")
    elif status == 'Rejected' and ot_row and ot_row[2] == 'Approved':
        # Reverse comp-off if previously approved
        emp_id     = ot_row[0]
        ot_minutes = ot_row[1]
        cursor.execute("""
            UPDATE compoff_balance SET earned_minutes = GREATEST(0, earned_minutes - %s)
            WHERE employee_id=%s
        """, (ot_minutes, emp_id))
        db.commit()
        flash("Overtime rejected and comp-off balance reversed.", "success")
    else:
        flash(f"Overtime record {status.lower()}.", "success")

    cursor.close(); db.close()
    return redirect('/overtime?tab=ot')


# ─────────────────────────── COMP-OFF MANAGEMENT ───────────────────────────

@app.route("/compoff")
@admin_required
def compoff():
    return redirect("/overtime?tab=compoff")

@app.route("/compoff_old")
@admin_required
def compoff_old():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    # Settings
    cursor.execute("SELECT COALESCE(compoff_min_ot_minutes,120), COALESCE(compoff_minutes_per_day,480), COALESCE(company_name,'') FROM company_settings LIMIT 1")
    cfg_row = cursor.fetchone() or (120, 480, '')
    min_ot_minutes      = int(cfg_row[0])
    minutes_per_day     = int(cfg_row[1])
    company_name        = cfg_row[2]

    # Employee balances
    cursor.execute("""
        SELECT e.employee_id, e.name, COALESCE(e.role,''), COALESCE(e.department,''),
               COALESCE(cb.earned_minutes,0), COALESCE(cb.used_minutes,0)
        FROM employees e
        LEFT JOIN compoff_balance cb ON cb.employee_id=e.employee_id
        WHERE e.is_active=1 ORDER BY e.name
    """)
    balances = []
    for emp_id, name, role, dept, earned, used in cursor.fetchall():
        earned_days = round(earned / minutes_per_day, 2) if minutes_per_day else 0
        used_days   = round(used   / minutes_per_day, 2) if minutes_per_day else 0
        avail_days  = max(0, round((earned - used) / minutes_per_day, 2)) if minutes_per_day else 0
        balances.append({
            "emp_id": emp_id, "name": name, "role": role, "dept": dept,
            "earned_min": earned, "used_min": used,
            "earned_days": earned_days, "used_days": used_days, "avail_days": avail_days
        })

    # Recent OT records (last 30 days)
    cursor.execute("""
        SELECT o.id, e.name, o.employee_id, o.date, o.ot_minutes, o.ot_pay, o.status
        FROM overtime_records o JOIN employees e ON e.employee_id=o.employee_id
        ORDER BY o.date DESC LIMIT 50
    """)
    ot_records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pending_leaves = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pending_resignations = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pending_tickets = cursor.fetchone()[0]
    cursor.close(); db.close()

    return render_template("compoff.html",
        balances=balances, ot_records=ot_records,
        min_ot_minutes=min_ot_minutes, minutes_per_day=minutes_per_day,
        company_name=company_name,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets
    )


@app.route("/compoff_settings", methods=["POST"])
@admin_required
def compoff_settings():
    min_ot  = int(request.form.get("min_ot_minutes", 120))
    mpd     = int(request.form.get("minutes_per_day", 480))
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        UPDATE company_settings SET compoff_min_ot_minutes=%s, compoff_minutes_per_day=%s
    """, (min_ot, mpd))
    db.commit(); cursor.close(); db.close()
    flash("Comp-off settings saved.", "success")
    return redirect("/overtime?tab=settings")


@app.route("/my_compoff")
@employee_required
def my_compoff():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("SELECT COALESCE(compoff_min_ot_minutes,120), COALESCE(compoff_minutes_per_day,480) FROM company_settings LIMIT 1")
    cfg = cursor.fetchone() or (120, 480)
    min_ot_minutes  = int(cfg[0])
    minutes_per_day = int(cfg[1])

    cursor.execute("SELECT COALESCE(earned_minutes,0), COALESCE(used_minutes,0) FROM compoff_balance WHERE employee_id=%s", (emp_id,))
    bal = cursor.fetchone() or (0, 0)
    earned_min, used_min = bal
    avail_min   = max(0, earned_min - used_min)
    earned_days = round(earned_min / minutes_per_day, 2) if minutes_per_day else 0
    used_days   = round(used_min   / minutes_per_day, 2) if minutes_per_day else 0
    avail_days  = round(avail_min  / minutes_per_day, 2) if minutes_per_day else 0

    # My OT records
    cursor.execute("""
        SELECT date, ot_minutes, ot_pay, status, notes
        FROM overtime_records WHERE employee_id=%s ORDER BY date DESC LIMIT 30
    """, (emp_id,))
    ot_records = cursor.fetchall()

    # My comp-off leave applications
    cursor.execute("""
        SELECT lr.leave_date, lr.status, lr.reason, lr.created_at
        FROM leave_requests lr JOIN leave_types lt ON lt.id=lr.leave_type_id
        WHERE lr.employee_id=%s AND lt.name='Comp-off'
        ORDER BY lr.created_at DESC LIMIT 20
    """, (emp_id,))
    compoff_leaves = cursor.fetchall()

    cursor.execute("SELECT id FROM leave_types WHERE name='Comp-off' LIMIT 1")
    lt_row = cursor.fetchone()
    compoff_lt_id = lt_row[0] if lt_row else None

    cursor.execute("SELECT name, COALESCE(role,''), COALESCE(department,''), face_image FROM employees WHERE employee_id=%s", (emp_id,))
    emp_info = cursor.fetchone()
    cursor.close(); db.close()

    return render_template("my_compoff.html",
        emp_id=emp_id, emp_info=emp_info,
        earned_days=earned_days, used_days=used_days, avail_days=avail_days,
        earned_min=earned_min, used_min=used_min, avail_min=avail_min,
        minutes_per_day=minutes_per_day, min_ot_minutes=min_ot_minutes,
        ot_records=ot_records, compoff_leaves=compoff_leaves,
        compoff_lt_id=compoff_lt_id
    )


# ---------------- API: NOTIFICATIONS (Admin) ----------------

@app.route("/api/notifications", methods=["GET"])
@api_required
def api_get_notifications():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='admin' ORDER BY created_at DESC LIMIT 50"
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "notifications": [
        {"id": r[0], "title": r[1], "message": r[2],
         "is_read": bool(r[3]), "created_at": r[4].strftime("%d %b %Y, %I:%M %p") if r[4] else ""}
        for r in rows
    ]})


@app.route("/api/notifications/mark_read", methods=["POST"])
@api_required
def api_mark_notifications_read():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read=TRUE WHERE recipient_type='admin'")
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True})


# ---------------- API: NOTIFICATIONS (Employee) ----------------

@app.route("/api/employee/notifications", methods=["GET"])
@employee_api_required
def api_employee_get_notifications():
    from flask import g as _g
    emp_id = _g.api_emp_id
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='employee' AND employee_id=%s ORDER BY created_at DESC LIMIT 50",
        (emp_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "notifications": [
        {"id": r[0], "title": r[1], "message": r[2],
         "is_read": bool(r[3]), "created_at": r[4].strftime("%d %b %Y, %I:%M %p") if r[4] else ""}
        for r in rows
    ]})


@app.route("/api/employee/notifications/mark_read", methods=["POST"])
@employee_api_required
def api_employee_mark_notifications_read():
    from flask import g as _g
    emp_id = _g.api_emp_id
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=TRUE WHERE recipient_type='employee' AND employee_id=%s",
        (emp_id,)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True})


@app.route("/web/notifications/mark_read", methods=["POST"])
@employee_required
def web_employee_mark_notifications_read():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=TRUE WHERE recipient_type='employee' AND employee_id=%s",
        (emp_id,)
    )
    db.commit(); cursor.close(); db.close()
    return jsonify({"ok": True})


@app.route("/web/notifications/list")
@employee_required
def web_employee_notifications_list():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='employee' AND employee_id=%s ORDER BY created_at DESC LIMIT 30",
        (emp_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify({"ok": True, "notifications": [
        {"id": r[0], "title": r[1], "message": r[2],
         "is_read": bool(r[3]), "created_at": r[4].strftime("%d %b %Y, %I:%M %p") if r[4] else ""}
        for r in rows
    ]})


# ── Tenant Provisioning ──────────────────────────────────────────────────────

_SUBDOMAIN_RE = re.compile(r'^[a-z0-9\-]+$')

@app.route("/create_org", methods=["GET"])
def create_org_page():
    return render_template("create_org.html")


@app.route("/create_org", methods=["POST"])
def create_org():
    company_name    = request.form.get("company_name", "").strip()
    subdomain       = request.form.get("subdomain", "").strip().lower()
    admin_username  = request.form.get("admin_username", "").strip()
    admin_password  = request.form.get("admin_password", "").strip()
    admin_email     = request.form.get("admin_email", "").strip() or None

    # Validate
    if not all([company_name, subdomain, admin_username, admin_password]):
        flash("All fields (company name, subdomain, admin username and password) are required.", "error")
        return redirect("/create_org")
    if not _SUBDOMAIN_RE.match(subdomain):
        flash("Subdomain may only contain lowercase letters, digits, and hyphens.", "error")
        return redirect("/create_org")
    if len(admin_password) < 8:
        flash("Admin password must be at least 8 characters.", "error")
        return redirect("/create_org")

    # Check subdomain not taken
    try:
        from database import get_master_db
        mconn = get_master_db()
        mcur  = mconn.cursor(buffered=True)
        mcur.execute("SELECT id FROM tenants WHERE subdomain=%s", (subdomain,))
        if mcur.fetchone():
            mcur.close(); mconn.close()
            flash(f"Subdomain '{subdomain}' is already taken. Choose another.", "error")
            return redirect("/create_org")
        mcur.close(); mconn.close()
    except Exception as exc:
        flash(f"Could not check subdomain availability: {exc}", "error")
        return redirect("/create_org")

    # Derive DB name
    db_name = "att_" + subdomain.replace("-", "_")

    try:
        from database import create_tenant_database
        create_tenant_database(db_name)
    except Exception as exc:
        flash(f"Failed to create tenant database: {exc}", "error")
        return redirect("/create_org")

    try:
        from flask import g as _g
        _g.tenant_db = db_name
        init_tenant_db(db_name)
    except Exception as exc:
        flash(f"Failed to initialize tenant schema: {exc}", "error")
        return redirect("/create_org")

    # Insert company settings and admin user into the new tenant DB
    try:
        from database import get_tenant_db
        tconn = get_tenant_db(db_name)
        tcur  = tconn.cursor()
        tcur.execute(
            "UPDATE company_settings SET company_name=%s, setup_done=1 WHERE id=1",
            (company_name,)
        )
        tcur.execute(
            "INSERT INTO admin_users (username, password, email) VALUES (%s, %s, %s)"
            " ON DUPLICATE KEY UPDATE password=VALUES(password)",
            (admin_username, generate_password_hash(admin_password), admin_email)
        )
        tconn.commit()
        tcur.close(); tconn.close()
    except Exception as exc:
        flash(f"Failed to seed tenant data: {exc}", "error")
        return redirect("/create_org")

    # Register tenant in master DB
    try:
        from database import get_master_db
        mconn = get_master_db()
        mcur  = mconn.cursor()
        mcur.execute(
            "INSERT INTO tenants (company_name, subdomain, db_name, admin_email, status) "
            "VALUES (%s, %s, %s, %s, 'active')",
            (company_name, subdomain, db_name, admin_email)
        )
        mconn.commit()
        mcur.close(); mconn.close()
    except Exception as exc:
        flash(f"Tenant registered in DB but master registry failed: {exc}", "error")
        return redirect("/create_org")

    flash(f"Organisation '{company_name}' created! Subdomain: {subdomain}. You can now log in.", "success")
    return redirect("/admin_login")


# ─────────────────────────────────────────
#  ONBOARDING WORKFLOW
# ─────────────────────────────────────────

@app.route("/onboarding")
@admin_required
def onboarding():
    db = get_db_connection()
    cursor = db.cursor()
    active_tab = request.args.get("tab", "active")

    # Active onboardings with progress
    cursor.execute("""
        SELECT eo.id, e.employee_id, e.name, e.role, e.department,
               ot.name AS template_name, eo.assigned_date, eo.due_date, eo.status,
               COUNT(eot.id) AS total_tasks,
               SUM(CASE WHEN eot.status='Done' THEN 1 ELSE 0 END) AS done_tasks
        FROM employee_onboarding eo
        JOIN employees e ON e.employee_id = eo.employee_id
        JOIN onboarding_templates ot ON ot.id = eo.template_id
        LEFT JOIN employee_onboarding_tasks eot ON eot.onboarding_id = eo.id
        GROUP BY eo.id
        ORDER BY eo.assigned_date DESC
    """)
    active_onboardings = cursor.fetchall()

    # Templates with task count
    cursor.execute("""
        SELECT ot.id, ot.name, ot.description, ot.is_active,
               COUNT(tt.id) AS task_count
        FROM onboarding_templates ot
        LEFT JOIN onboarding_template_tasks tt ON tt.template_id = ot.id
        GROUP BY ot.id
        ORDER BY ot.created_at DESC
    """)
    templates = cursor.fetchall()

    # Employees list for assign dropdown
    cursor.execute("SELECT employee_id, name, role FROM employees WHERE is_active=1 ORDER BY name")
    emp_list = cursor.fetchall()

    # Active templates for assign dropdown
    cursor.execute("SELECT id, name FROM onboarding_templates WHERE is_active=1 ORDER BY name")
    active_templates = cursor.fetchall()

    co = get_company_settings()
    cursor.close(); db.close()
    return render_template("onboarding.html",
        active_onboardings=active_onboardings,
        templates=templates,
        emp_list=emp_list,
        active_templates=active_templates,
        active_tab=active_tab,
        co=co,
        pending_leaves=0, pending_resignations=0, pending_tickets=0
    )

@app.route("/onboarding_template_save", methods=["POST"])
@admin_required
def onboarding_template_save():
    db = get_db_connection(); cursor = db.cursor()
    tid    = request.form.get("template_id")
    name   = request.form.get("name", "").strip()
    desc   = request.form.get("description", "").strip()
    if not name:
        flash("Template name is required.", "error")
        return redirect("/onboarding?tab=templates")
    if tid:
        cursor.execute("UPDATE onboarding_templates SET name=%s, description=%s WHERE id=%s", (name, desc, tid))
        flash("Template updated.", "success")
    else:
        cursor.execute("INSERT INTO onboarding_templates (name, description) VALUES (%s,%s)", (name, desc))
        flash("Template created.", "success")
    db.commit(); cursor.close(); db.close()
    return redirect("/onboarding?tab=templates")

@app.route("/onboarding_template_delete", methods=["POST"])
@admin_required
def onboarding_template_delete():
    db = get_db_connection(); cursor = db.cursor()
    tid = request.form.get("template_id")
    cursor.execute("DELETE FROM onboarding_template_tasks WHERE template_id=%s", (tid,))
    cursor.execute("DELETE FROM onboarding_templates WHERE id=%s", (tid,))
    db.commit(); cursor.close(); db.close()
    flash("Template deleted.", "success")
    return redirect("/onboarding?tab=templates")

@app.route("/onboarding_task_save", methods=["POST"])
@admin_required
def onboarding_task_save():
    db = get_db_connection(); cursor = db.cursor()
    task_id   = request.form.get("task_id")
    tid       = request.form.get("template_id")
    title     = request.form.get("task_title", "").strip()
    desc      = request.form.get("task_description", "").strip()
    req_doc   = 1 if request.form.get("requires_document") else 0
    due_days  = int(request.form.get("due_days", 7))
    sort_order= int(request.form.get("sort_order", 0))
    if not title:
        flash("Task title is required.", "error")
        return redirect(f"/onboarding_template_detail/{tid}")
    if task_id:
        cursor.execute("""UPDATE onboarding_template_tasks
                          SET task_title=%s, task_description=%s, requires_document=%s,
                              due_days=%s, sort_order=%s
                          WHERE id=%s""", (title, desc, req_doc, due_days, sort_order, task_id))
        flash("Task updated.", "success")
    else:
        cursor.execute("""INSERT INTO onboarding_template_tasks
                          (template_id, task_title, task_description, requires_document, due_days, sort_order)
                          VALUES (%s,%s,%s,%s,%s,%s)""", (tid, title, desc, req_doc, due_days, sort_order))
        flash("Task added.", "success")
    db.commit(); cursor.close(); db.close()
    return redirect(f"/onboarding_template_detail/{tid}")

@app.route("/onboarding_task_delete", methods=["POST"])
@admin_required
def onboarding_task_delete():
    db = get_db_connection(); cursor = db.cursor()
    task_id = request.form.get("task_id")
    cursor.execute("SELECT template_id FROM onboarding_template_tasks WHERE id=%s", (task_id,))
    row = cursor.fetchone()
    tid = row[0] if row else None
    cursor.execute("DELETE FROM onboarding_template_tasks WHERE id=%s", (task_id,))
    db.commit(); cursor.close(); db.close()
    flash("Task deleted.", "success")
    return redirect(f"/onboarding_template_detail/{tid}")

@app.route("/onboarding_template_detail/<int:tid>")
@admin_required
def onboarding_template_detail(tid):
    db = get_db_connection(); cursor = db.cursor()
    cursor.execute("SELECT id, name, description, is_active FROM onboarding_templates WHERE id=%s", (tid,))
    template = cursor.fetchone()
    cursor.execute("""SELECT id, task_title, task_description, requires_document, due_days, sort_order
                      FROM onboarding_template_tasks WHERE template_id=%s ORDER BY sort_order, id""", (tid,))
    tasks = cursor.fetchall()
    co = get_company_settings()
    cursor.close(); db.close()
    return render_template("onboarding_template_detail.html",
        template=template, tasks=tasks, co=co,
        pending_leaves=0, pending_resignations=0, pending_tickets=0
    )

@app.route("/onboarding_assign", methods=["POST"])
@admin_required
def onboarding_assign():
    db = get_db_connection(); cursor = db.cursor()
    emp_id   = request.form.get("employee_id")
    tid      = request.form.get("template_id")
    due_date = request.form.get("due_date") or None
    today    = date.today()

    # Check not already assigned same template
    cursor.execute("SELECT id FROM employee_onboarding WHERE employee_id=%s AND template_id=%s AND status='In Progress'",
                   (emp_id, tid))
    if cursor.fetchone():
        flash("This employee already has this onboarding in progress.", "error")
        cursor.close(); db.close()
        return redirect("/onboarding?tab=active")

    cursor.execute("INSERT INTO employee_onboarding (employee_id, template_id, assigned_date, due_date) VALUES (%s,%s,%s,%s)",
                   (emp_id, tid, today, due_date))
    ob_id = cursor.lastrowid

    # Copy tasks from template
    cursor.execute("""SELECT id, task_title, task_description, requires_document, due_days
                      FROM onboarding_template_tasks WHERE template_id=%s ORDER BY sort_order, id""", (tid,))
    for task in cursor.fetchall():
        cursor.execute("""INSERT INTO employee_onboarding_tasks
                          (onboarding_id, template_task_id, employee_id, task_title, task_description, requires_document, due_days)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                       (ob_id, task[0], emp_id, task[1], task[2], task[3], task[4]))
    db.commit()

    # Notification to employee
    try:
        cursor.execute("SELECT name FROM onboarding_templates WHERE id=%s", (tid,))
        tname = cursor.fetchone()[0]
        cursor.execute("""INSERT INTO employee_notifications (employee_id, title, message, notif_type)
                          VALUES (%s, 'Onboarding Started', %s, 'info')""",
                       (emp_id, f"Your onboarding checklist '{tname}' has been assigned. Please complete all tasks."))
        db.commit()
    except Exception:
        pass

    cursor.execute("SELECT name FROM employees WHERE employee_id=%s", (emp_id,))
    emp_name = cursor.fetchone()[0]
    cursor.close(); db.close()
    flash(f"Onboarding assigned to {emp_name}.", "success")
    return redirect("/onboarding?tab=active")

@app.route("/onboarding_detail/<int:ob_id>")
@admin_required
def onboarding_detail(ob_id):
    db = get_db_connection(); cursor = db.cursor()
    cursor.execute("""
        SELECT eo.id, e.employee_id, e.name, e.role, e.department,
               ot.name AS tname, eo.assigned_date, eo.due_date, eo.status
        FROM employee_onboarding eo
        JOIN employees e ON e.employee_id=eo.employee_id
        JOIN onboarding_templates ot ON ot.id=eo.template_id
        WHERE eo.id=%s
    """, (ob_id,))
    ob = cursor.fetchone()
    cursor.execute("""
        SELECT id, task_title, task_description, requires_document, due_days,
               status, completed_at, document_path, admin_notes
        FROM employee_onboarding_tasks WHERE onboarding_id=%s ORDER BY id
    """, (ob_id,))
    tasks = cursor.fetchall()
    co = get_company_settings()
    cursor.close(); db.close()
    return render_template("onboarding_detail.html",
        ob=ob, tasks=tasks, co=co,
        pending_leaves=0, pending_resignations=0, pending_tickets=0
    )

@app.route("/onboarding_admin_task_update", methods=["POST"])
@admin_required
def onboarding_admin_task_update():
    db = get_db_connection(); cursor = db.cursor()
    task_id    = request.form.get("task_id")
    new_status = request.form.get("status")
    notes      = request.form.get("admin_notes", "")
    ob_id      = request.form.get("ob_id")
    completed  = datetime.now() if new_status == "Done" else None
    cursor.execute("""UPDATE employee_onboarding_tasks
                      SET status=%s, completed_at=%s, admin_notes=%s WHERE id=%s""",
                   (new_status, completed, notes, task_id))
    # Auto-complete onboarding if all tasks done
    cursor.execute("SELECT COUNT(*) FROM employee_onboarding_tasks WHERE onboarding_id=%s AND status!='Done'", (ob_id,))
    remaining = cursor.fetchone()[0]
    if remaining == 0:
        cursor.execute("UPDATE employee_onboarding SET status='Completed' WHERE id=%s", (ob_id,))
    db.commit(); cursor.close(); db.close()
    flash("Task updated.", "success")
    return redirect(f"/onboarding_detail/{ob_id}")

@app.route("/onboarding_close", methods=["POST"])
@admin_required
def onboarding_close():
    db = get_db_connection(); cursor = db.cursor()
    ob_id = request.form.get("ob_id")
    cursor.execute("UPDATE employee_onboarding SET status='Completed' WHERE id=%s", (ob_id,))
    db.commit(); cursor.close(); db.close()
    flash("Onboarding marked as completed.", "success")
    return redirect("/onboarding?tab=active")

# Employee portal onboarding
@app.route("/my_onboarding")
@employee_required
def my_onboarding():
    emp_id = session.get("employee_id")
    db = get_db_connection(); cursor = db.cursor()
    cursor.execute("""
        SELECT eo.id, ot.name, eo.assigned_date, eo.due_date, eo.status,
               COUNT(eot.id) AS total, SUM(CASE WHEN eot.status='Done' THEN 1 ELSE 0 END) AS done
        FROM employee_onboarding eo
        JOIN onboarding_templates ot ON ot.id=eo.template_id
        LEFT JOIN employee_onboarding_tasks eot ON eot.onboarding_id=eo.id
        WHERE eo.employee_id=%s
        GROUP BY eo.id ORDER BY eo.assigned_date DESC
    """, (emp_id,))
    onboardings = cursor.fetchall()

    selected_ob_id = request.args.get("ob_id")
    tasks = []
    selected_ob = None
    if not selected_ob_id and onboardings:
        selected_ob_id = onboardings[0][0]
    if selected_ob_id:
        cursor.execute("""SELECT id, task_title, task_description, requires_document,
                                 due_days, status, completed_at, document_path
                          FROM employee_onboarding_tasks
                          WHERE onboarding_id=%s AND employee_id=%s ORDER BY id""",
                       (selected_ob_id, emp_id))
        tasks = cursor.fetchall()
        for ob in onboardings:
            if ob[0] == int(selected_ob_id):
                selected_ob = ob
                break

    cursor.execute("SELECT employee_id, name, role, department, face_image FROM employees WHERE employee_id=%s", (emp_id,))
    emp = cursor.fetchone()
    cursor.close(); db.close()
    return render_template("my_onboarding.html",
        emp=emp, emp_id=emp_id, onboardings=onboardings, tasks=tasks,
        selected_ob=selected_ob, selected_ob_id=int(selected_ob_id) if selected_ob_id else None
    )

@app.route("/my_onboarding_task_done", methods=["POST"])
@employee_required
def my_onboarding_task_done():
    emp_id = session.get("employee_id")
    db = get_db_connection(); cursor = db.cursor()
    task_id = request.form.get("task_id")
    ob_id   = request.form.get("ob_id")

    cursor.execute("SELECT employee_id, requires_document FROM employee_onboarding_tasks WHERE id=%s", (task_id,))
    row = cursor.fetchone()
    if not row or row[0] != emp_id:
        flash("Not authorised.", "error")
        cursor.close(); db.close()
        return redirect("/my_onboarding")

    doc_path = None
    if 'document' in request.files:
        f = request.files['document']
        if f and f.filename:
            import os as _os
            upload_dir = _os.path.join("static", "onboarding_docs")
            _os.makedirs(upload_dir, exist_ok=True)
            safe_name = f"{emp_id}_{task_id}_{f.filename.replace(' ','_')}"
            f.save(_os.path.join(upload_dir, safe_name))
            doc_path = safe_name

    update_args = [datetime.now(), task_id]
    if doc_path:
        cursor.execute("UPDATE employee_onboarding_tasks SET status='Done', completed_at=%s, document_path=%s WHERE id=%s",
                       (datetime.now(), doc_path, task_id))
    else:
        cursor.execute("UPDATE employee_onboarding_tasks SET status='Done', completed_at=%s WHERE id=%s",
                       (datetime.now(), task_id))

    # Auto-complete if all done
    cursor.execute("SELECT COUNT(*) FROM employee_onboarding_tasks WHERE onboarding_id=%s AND status!='Done'", (ob_id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("UPDATE employee_onboarding SET status='Completed' WHERE id=%s", (ob_id,))

    db.commit(); cursor.close(); db.close()
    flash("Task marked as done!", "success")
    return redirect(f"/my_onboarding?ob_id={ob_id}")


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_master_db()
    init_db()
    load_default_shift()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
