import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash, send_from_directory, current_app
import uuid
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
import datetime
import html as _html
try:
    import face_recognition
    _face_recognition_available = True
except Exception as _fr_err:
    face_recognition = None
    _face_recognition_available = False
    print(f"⚠  face_recognition unavailable ({_fr_err}). Face features disabled.")

# Cache known face encodings by (employee_id, file_mtime) to avoid recomputing on every punch
_face_enc_cache: dict = {}

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
try:
    # typing.Literal was added in Python 3.8; backport it for 3.7 so webauthn imports cleanly
    import typing as _typing
    if not hasattr(_typing, "Literal"):
        from typing_extensions import Literal as _Literal
        _typing.Literal = _Literal
    import webauthn
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria, AuthenticatorAttachment, UserVerificationRequirement,
        ResidentKeyRequirement, PublicKeyCredentialDescriptor, AuthenticatorTransport,
        COSEAlgorithmIdentifier, AttestationConveyancePreference,
    )
    _webauthn_available = True
except Exception as _wa_err:
    webauthn = None
    _webauthn_available = False
    print(f"⚠  webauthn unavailable ({_wa_err}). Fingerprint features disabled. (Needs Python 3.8+; "
          f"runs fine in the production Podman image, which uses Python 3.11.)")
from database import get_db_connection
from qr_generator import generate_qr
import bcrypt as _bcrypt
from werkzeug.security import check_password_hash as _wz_check_pw

def generate_password_hash(pw: str, **_) -> str:
    """Hash a password with bcrypt (work factor 12)."""
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt(rounds=12)).decode()

def check_password_hash(pw_hash: str, pw: str) -> bool:
    """Verify a password against bcrypt or legacy werkzeug hash."""
    if not pw_hash:
        return False
    if pw_hash.startswith("$2b$") or pw_hash.startswith("$2a$"):
        try:
            return _bcrypt.checkpw(pw.encode(), pw_hash.encode())
        except Exception:
            return False
    # Legacy pbkdf2/scrypt hash from werkzeug — still valid on upgrade
    return _wz_check_pw(pw_hash, pw)
from functools import wraps
from contextlib import contextmanager
import os
import math
import re
import calendar
import psycopg2
import smtplib
import ssl
import secrets
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
import threading
import io as _io
import hashlib
import time
import base64
from werkzeug.exceptions import HTTPException
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv

load_dotenv()

import logging

# ── Startup: warn if critical env vars are missing ──
_missing_env = [k for k in ("DB_HOST", "DB_USER", "DB_PASS", "DB_NAME") if not os.environ.get(k)]
if _missing_env:
    import warnings
    warnings.warn(
        f"Missing required environment variables: {', '.join(_missing_env)}. "
        "Copy .env.example to .env and fill in the values.",
        stacklevel=2
    )

from extensions import app, limiter, app_log, _allowed_origins

# ── Trusted base URL for email links (avoids Host-header injection) ───────────
# Set APP_URL=https://yourdomain.com in .env for production.
# Falls back to request.host_url only when the env var is absent (local dev).
_APP_URL = os.environ.get("APP_URL", "").rstrip("/")

def _safe_app_url() -> str:
    """Return a trusted base URL, never derived from the Host header."""
    return _APP_URL if _APP_URL else request.host_url.rstrip("/")

def _safe_redirect(dest: str, fallback: str = "/admin") -> str:
    """Validate that a redirect target is a relative path (prevents open redirect)."""
    if dest and dest.startswith("/") and not dest.startswith("//"):
        return dest
    return fallback

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

@app.context_processor
def inject_common_vars():
    return dict(
        shift_start=SHIFT_START.strftime("%I:%M %p"),
        shift_end=SHIFT_END.strftime("%I:%M %p"),
    )

@app.template_filter('qr_url')
def _qr_url_filter(p):
    """Normalize QR code paths — old code stored absolute OS paths; extract just static/qrcodes/<file>."""
    import re
    if not p:
        return ''
    m = re.search(r'static[/\\]qrcodes[/\\]([^/\\]+\.png)', str(p))
    return f'static/qrcodes/{m.group(1)}' if m else str(p)

# /favicon.ico and /healthz are served by blueprints/health.py


# Jinja2 filter: handles both datetime.time and datetime.timedelta.
# psycopg2 returns TIME columns as datetime.time (hits the strftime branch
# below); the timedelta branch is a defensive fallback kept from when this
# ran against mysql-connector, which returned TIME columns as timedelta.
@app.template_filter("fmt_time")
def fmt_time_filter(value):
    if value is None:
        return "--"
    if isinstance(value, str):
        return value
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M:%S")
    # timedelta fallback — see comment above
    total = int(value.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)

# Templates that need arithmetic on a TIME value (elapsed-time math, HH/MM/SS
# breakdowns) used to rely on mysql-connector's timedelta.seconds. psycopg2
# returns datetime.time instead, which has no .seconds — this filter gives
# templates a type-agnostic "total seconds" so that math still works.
@app.template_filter("time_seconds")
def time_seconds_filter(value):
    if value is None:
        return 0
    if hasattr(value, "hour"):
        return value.hour * 3600 + value.minute * 60 + value.second
    return int(value.total_seconds())

# ---------------- CONFIG ----------------
# secret_key, session cookie flags, and PERMANENT_SESSION_LIFETIME are
# authoritative in extensions.py. Do not duplicate them here.

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
app.jinja_env.globals["timedelta"]  = datetime.timedelta

@app.context_processor
def inject_companies_context():
    """Inject active company and companies list into every admin template."""
    if not session.get("admin_logged_in"):
        return {}
    try:
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute("""
            SELECT id, name, COALESCE(code,''), COALESCE(pin,'')
            FROM companies ORDER BY name
        """)
        rows = cur.fetchall()
        cur.close(); db.close()
        active_cid = session.get("active_company_id")
        active_company = None
        for r in rows:
            if r[0] == active_cid:
                active_company = {"id": r[0], "name": r[1], "code": r[2]}
                break
        return {
            "all_companies": [{"id": r[0], "name": r[1], "code": r[2], "has_pin": bool(r[3])} for r in rows],
            "active_company": active_company,
        }
    except Exception:
        return {"all_companies": [], "active_company": None}

@app.context_processor
def inject_overdue_onboardings():
    if not session.get("admin_logged_in"):
        return {}
    try:
        db = get_db_connection(); cur = db.cursor()
        today = datetime.date.today()
        cur.execute("""
            SELECT COUNT(*) FROM employee_onboarding
            WHERE status != 'Completed' AND due_date < %s
        """, (today,))
        count = cur.fetchone()[0]
        cur.close(); db.close()
        return {"overdue_onboardings": count}
    except Exception:
        return {"overdue_onboardings": 0}

_SESSION_MAX_AGE = 8 * 3600  # 8 hours absolute — stolen cookie cannot be used indefinitely

@app.before_request
def _enforce_session_lifetime():
    """Expire sessions that are older than the absolute max age, regardless of activity."""
    if request.path.startswith("/static/") or request.path == "/healthz":
        return
    created = session.get("_session_created")
    if created and (time.time() - created) > _SESSION_MAX_AGE:
        session.clear()
        if request.path.startswith("/api/"):
            from flask import jsonify as _jfy
            return _jfy({"ok": False, "msg": "Session expired. Please log in again."}), 401
        flash("Your session expired. Please log in again.", "warning")
        return redirect(url_for("auth.admin_login"))


@app.before_request
def _enforce_csrf():
    if request.method != "POST":
        return
    if current_app.testing:
        return  # CSRF disabled in test mode; Bearer-token tests handle auth separately
    if request.path.startswith("/api/"):
        return  # API routes use Bearer-token auth — no session/CSRF needed
    # NOTE: We intentionally do NOT skip JSON requests here. The auto-inject
    # script (_inject_csrf_meta) adds X-CSRF-Token to every fetch() call, so
    # legitimate JSON POSTs from the web UI already carry the token.
    # Skipping CSRF for is_json would allow XSS payloads to forge state-changing
    # JSON requests without a token.
    token = session.get("_csrf")
    submitted = (request.form.get("_csrf_token")
                 or request.headers.get("X-CSRF-Token")
                 or request.headers.get("X-CSRFToken"))
    if not token or not submitted or not secrets.compare_digest(str(token), str(submitted)):
        # Browser form submissions: redirect to login so the user gets a fresh session+token
        if request.accept_mimetypes.accept_html and not request.headers.get("X-Requested-With"):
            flash("Your session expired. Please log in again.", "warning")
            login_url = url_for("auth.employee_login") if request.path.startswith("/employee") or "employee" in request.path else url_for("auth.admin_login")
            return redirect(login_url)
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


_CSRF_HEAD_RE    = re.compile(rb'</head>', re.IGNORECASE)
_CSRF_BODY_RE    = re.compile(rb'</body>', re.IGNORECASE)
# Matches <script>/<style> tags without a nonce — used to inject CSP nonces
_SCRIPT_TAG_RE   = re.compile(rb'<script(?!\s[^>]*\bnonce\b)(?=[\s>])', re.IGNORECASE)
_STYLE_TAG_RE    = re.compile(rb'<style(?!\s[^>]*\bnonce\b)(?=[\s>])',  re.IGNORECASE)
# Capture inline event-handler values for dynamic CSP sha256 hash generation.
# Two patterns: double-quoted and single-quoted attribute values.
_CSP_EV_DQ = re.compile(
    rb'\bon(?:animationend|blur|change|click|contextmenu|copy|cut|dblclick|drag|dragend'
    rb'|dragenter|dragleave|dragover|dragstart|drop|error|focus|input|invalid|keydown|keypress'
    rb'|keyup|load|mousedown|mousemove|mouseout|mouseover|mouseup|paste|pointerdown'
    rb'|pointermove|pointerup|reset|scroll|select|submit|touchend|touchmove|touchstart'
    rb'|transitionend|wheel)\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)
_CSP_EV_SQ = re.compile(
    rb"\bon(?:animationend|blur|change|click|contextmenu|copy|cut|dblclick|drag|dragend"
    rb"|dragenter|dragleave|dragover|dragstart|drop|error|focus|input|invalid|keydown|keypress"
    rb"|keyup|load|mousedown|mousemove|mouseout|mouseover|mouseup|paste|pointerdown"
    rb"|pointermove|pointerup|reset|scroll|select|submit|touchend|touchmove|touchstart"
    rb"|transitionend|wheel)\s*=\s*'([^']*)'",
    re.IGNORECASE,
)
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

@app.before_request
def _set_csp_nonce():
    from flask import g
    g.csp_nonce = secrets.token_urlsafe(16)

_SETTINGS_PATHS = {"/settings", "/setup", "/admin_set_recovery_email",
                   "/save_security_settings", "/toggle_auth_feature",
                   "/toggle_fingerprint", "/save_company_code", "/save_geo_settings",
                   "/save_company_info", "/toggle_feature"}

@app.after_request
def _security_headers(response):
    from flask import g
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=(self)"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Server"] = "AttendanceApp"
    if request.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    ct = response.content_type or ""
    if "text/html" in ct:
        nonce = getattr(g, "csp_nonce", "")
        # _inject_csrf_meta runs before this hook (Flask reverses registration order),
        # so response.get_data() is the final HTML with nonces already injected.
        # Scan for inline event-handler values and compute sha256 hashes so they
        # pass CSP without needing 'unsafe-inline'.
        try:
            data = response.get_data()
            _ev_hashes: set = set()
            for _pat in (_CSP_EV_DQ, _CSP_EV_SQ):
                for _m in _pat.finditer(data):
                    _body = _html.unescape(_m.group(1).decode("utf-8", errors="replace"))
                    _ev_hashes.add(
                        "'sha256-" + base64.b64encode(
                            hashlib.sha256(_body.encode("utf-8")).digest()
                        ).decode() + "'"
                    )
        except Exception:
            _ev_hashes = set()
        _unsafe_hashes = " 'unsafe-hashes'" if _ev_hashes else ""
        _hash_src = (" " + " ".join(sorted(_ev_hashes))) if _ev_hashes else ""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'{_unsafe_hashes}{_hash_src}; "
            f"style-src-elem 'self' 'nonce-{nonce}'; "
            "style-src-attr 'unsafe-inline'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "report-uri /csp-report;"
        )
    return response


@app.after_request
def _bust_settings_cache(response):
    if request.method == "POST" and request.path in _SETTINGS_PATHS:
        invalidate_settings_cache()
    return response

@app.after_request
def _inject_csrf_meta(response):
    """Inject CSRF meta tag and auto-inject script into every HTML page."""
    if response.status_code >= 300 or not response.content_type.startswith("text/html"):
        return response
    try:
        from flask import g
        token = _csrf_token()
        meta  = f'<meta name="csrf-token" content="{token}" />'.encode()
        data  = response.get_data()
        data  = _CSRF_HEAD_RE.sub(meta + b'</head>', data, count=1)
        data  = _CSRF_BODY_RE.sub(_CSRF_SCRIPT + b'</body>', data, count=1)
        nonce = getattr(g, "csp_nonce", None)
        if nonce:
            nb = nonce.encode()
            data = _SCRIPT_TAG_RE.sub(b'<script nonce="' + nb + b'"', data)
            data = _STYLE_TAG_RE.sub(b'<style nonce="' + nb + b'"', data)
        response.set_data(data)
    except Exception:
        pass
    return response

# ---------------- AUDIT LOGGING ----------------
def _audit(action, table=None, record_id=None, detail=None):
    """Write one row to audit_logs. Never raises — audit must never break main flow."""
    try:
        actor      = session.get("admin_username") or session.get("employee_id") or "system"
        actor_type = "admin" if session.get("admin_logged_in") else "employee"
        ip         = request.remote_addr or ""
        db = get_db_connection(); cursor = db.cursor()
        cursor.execute("""INSERT INTO audit_logs (actor, actor_type, action, target_table, target_id, detail, ip_address)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                       (actor, actor_type, action, table, str(record_id) if record_id is not None else None, detail, ip))
        db.commit(); cursor.close(); db.close()
    except Exception:
        pass

# ---------------- MALWARE SCANNING (ClamAV) ----------------
try:
    import clamd as _clamd_lib
    _clamav_available = True
except ImportError:
    _clamd_lib = None
    _clamav_available = False

_CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "clamav")
_CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
_MALWARE_SCAN_ENABLED = os.environ.get("MALWARE_SCAN_ENABLED", "true").strip().lower() not in ("false", "0", "no")

def _scan_for_malware(file_storage):
    """Scan an uploaded file with ClamAV before it's saved. Returns (is_clean, error_msg).
    Fails closed (rejects the upload) in production if the scanner is unavailable
    or unreachable; fails open with a logged warning in development, so a missing
    local ClamAV instance doesn't block day-to-day dev work.

    Set MALWARE_SCAN_ENABLED=false to turn this off deliberately (e.g. a
    memory-constrained deployment that can't run ClamAV) — that's a clean
    skip, not a failure, so it doesn't trigger the fail-closed behavior
    below and permanently block uploads."""
    if not _MALWARE_SCAN_ENABLED:
        return True, None
    _dev = os.environ.get("APP_ENV", "production") == "development"
    if not _clamav_available:
        app_log.error("clamd package not installed — malware scanning skipped")
        return (True, None) if _dev else (False, "Malware scanning is unavailable — upload rejected.")
    try:
        cd = _clamd_lib.ClamdNetworkSocket(host=_CLAMAV_HOST, port=_CLAMAV_PORT, timeout=15)
        pos = file_storage.stream.tell()
        file_storage.stream.seek(0)
        result = cd.instream(file_storage.stream)
        file_storage.stream.seek(pos)
        status, signature = result.get("stream", (None, None))
        if status == "FOUND":
            app_log.warning("Malware detected in upload %r: %s", file_storage.filename, signature)
            return False, "This file was flagged by malware scanning and cannot be uploaded."
        return True, None
    except Exception as _e:
        app_log.error("ClamAV scan failed (%s): %s", type(_e).__name__, _e)
        return (True, None) if _dev else (False, "File could not be scanned for malware — please try again shortly.")


# ---------------- FILE UPLOAD VALIDATION ----------------
_ALLOWED_MIME_MAP = {
    'pdf':  {'application/pdf'},
    'jpg':  {'image/jpeg'},
    'jpeg': {'image/jpeg'},
    'png':  {'image/png'},
    'doc':  {'application/msword'},
    'docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    'xls':  {'application/vnd.ms-excel'},
    'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
}
_MAX_DOC_SIZE_MB = 10

def _validate_upload(file_storage, allowed_exts=None):
    """Returns (ok, error_message). Checks extension + MIME type + size."""
    if not file_storage or not file_storage.filename:
        return False, "No file selected."
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if allowed_exts and ext not in allowed_exts:
        return False, f"File type .{ext} not allowed. Allowed: {', '.join(sorted(allowed_exts))}"
    ct = (file_storage.content_type or '').split(';')[0].strip().lower()
    if ct and ext in _ALLOWED_MIME_MAP and ct not in _ALLOWED_MIME_MAP[ext]:
        return False, f"File content does not match its extension."
    # Check magic bytes for PDF and images
    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if ext == 'pdf' and not header.startswith(b'%PDF'):
        return False, "Invalid PDF file."
    if ext == 'png' and not header.startswith(b'\x89PNG'):
        return False, "Invalid PNG file."
    if ext in ('jpg', 'jpeg') and not header.startswith(b'\xff\xd8'):
        return False, "Invalid JPEG file."
    file_storage.stream.seek(0, 2)
    size_mb = file_storage.stream.tell() / (1024 * 1024)
    file_storage.stream.seek(0)
    if size_mb > _MAX_DOC_SIZE_MB:
        return False, f"File too large ({size_mb:.1f} MB). Maximum: {_MAX_DOC_SIZE_MB} MB."
    clean, scan_err = _scan_for_malware(file_storage)
    if not clean:
        return False, scan_err
    return True, None

# ---------------- COMPANY SETTINGS (with 60-second TTL cache) ----------------
_co_cache      = {"data": None, "expires": None}
_auth_cache    = {"data": None, "expires": None}
_settings_lock = threading.Lock()
_CO_CACHE_TTL  = 60  # seconds

def _co_expired(cache):
    return cache["data"] is None or datetime.datetime.now() >= cache["expires"]

def invalidate_settings_cache():
    with _settings_lock:
        _co_cache["data"]    = None
        _auth_cache["data"]  = None

def get_company_settings():
    with _settings_lock:
        if not _co_expired(_co_cache):
            return dict(_co_cache["data"])
    try:
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT company_name, company_tagline, company_logo, currency_symbol, timezone, setup_done, COALESCE(company_code,'') FROM company_settings LIMIT 1")
        row = cursor.fetchone()
        cursor.close(); db.close()
        if row:
            result = {"company_name": row[0], "company_tagline": row[1],
                      "company_logo": row[2], "currency_symbol": row[3],
                      "company_code": row[6],
                      "timezone": row[4], "setup_done": bool(row[5])}
            with _settings_lock:
                _co_cache["data"]    = result
                _co_cache["expires"] = datetime.datetime.now() + datetime.timedelta(seconds=_CO_CACHE_TTL)
            return dict(result)
    except Exception:
        pass
    return {"company_name": "My Company", "company_tagline": "Employee Attendance System",
            "company_logo": None, "currency_symbol": "₹", "timezone": "Asia/Kolkata",
            "setup_done": False, "company_code": ""}

_AUTH_CONFIG_DEFAULTS = {
    "fingerprint_enabled": False,
    "qr_enabled": True,
    "face_enabled": True,
    "location_enabled": True,
    "employee_password_auth": True,
}

def get_auth_config():
    with _settings_lock:
        if not _co_expired(_auth_cache):
            return dict(_auth_cache["data"])
    try:
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("""
            SELECT COALESCE(fingerprint_enabled, 0),
                   COALESCE(qr_enabled, 1),
                   COALESCE(face_enabled, 1),
                   COALESCE(location_enabled, 1),
                   COALESCE(employee_password_auth, 1)
            FROM company_settings LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close(); db.close()
        if row:
            result = {
                "fingerprint_enabled": bool(row[0]),
                "qr_enabled":          bool(row[1]),
                "face_enabled":        bool(row[2]),
                "location_enabled":    bool(row[3]),
                "employee_password_auth": bool(row[4]),
            }
            with _settings_lock:
                _auth_cache["data"]    = result
                _auth_cache["expires"] = datetime.datetime.now() + datetime.timedelta(seconds=_CO_CACHE_TTL)
            return dict(result)
        return dict(_AUTH_CONFIG_DEFAULTS)
    except Exception:
        return dict(_AUTH_CONFIG_DEFAULTS)

def get_fingerprint_enabled():
    return get_auth_config()["fingerprint_enabled"]

# ── Per-company feature settings ──────────────────────────────────────────────
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

_VALID_CFS_COLS = frozenset({
    "face_auth_enabled", "geo_enabled", "geo_radius", "qr_enabled", "pin_enabled",
    "fingerprint_enabled", "biometric_enabled", "notify_leave", "notify_payslip",
    "notify_resignation", "notify_doc_expiry", "session_timeout",
    "late_deduction_pct", "half_day_deduction_pct", "grace_minutes",
    "shift_start", "shift_half", "shift_end", "holiday_pay", "leave_pay",
})

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

# Deduction rates and salary rules (loaded from DB on startup)
LATE_DEDUCTION_RATE = 0.10
HALF_DAY_RATE       = 0.50
GRACE_MINUTES       = 15       # grace period after shift start for full-day login
HOLIDAY_PAY         = 'paid'   # 'paid' = full day pay | 'unpaid' = no pay
LEAVE_PAY           = 'exclude' # 'exclude' = not a working day | 'absent' = count as absent

def load_salary_rules():
    global LATE_DEDUCTION_RATE, HALF_DAY_RATE, GRACE_MINUTES, HOLIDAY_PAY, LEAVE_PAY
    try:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT COALESCE(late_deduction_pct,10), COALESCE(half_day_deduction_pct,50), "
            "       COALESCE(grace_minutes,15), COALESCE(holiday_pay,'paid'), COALESCE(leave_pay,'exclude') "
            "FROM company_settings LIMIT 1"
        )
        row = cursor.fetchone()
        cursor.close(); db.close()
        if row:
            LATE_DEDUCTION_RATE = float(row[0]) / 100.0
            HALF_DAY_RATE       = float(row[1]) / 100.0
            GRACE_MINUTES       = int(row[2])
            HOLIDAY_PAY         = str(row[3])
            LEAVE_PAY           = str(row[4])
    except Exception:
        pass

def load_deduction_rates():
    load_salary_rules()

with app.app_context():
    try:
        load_default_shift()
        load_salary_rules()
    except Exception:
        pass

# ---------------- IMAGE UPLOAD VALIDATION ----------------
_ALLOWED_IMG_EXT  = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
_ALLOWED_IMG_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif'}

_MAX_PHOTO_SIZE_MB = 5
_IMG_MAGIC = {
    '.jpg':  (b'\xff\xd8',),
    '.jpeg': (b'\xff\xd8',),
    '.png':  (b'\x89PNG',),
    '.webp': (b'RIFF',),
    '.bmp':  (b'BM',),
}

def _validate_image_file(file):
    """Return (ok, error_msg). Checks extension, MIME type, magic bytes, and size."""
    if not file or not file.filename:
        return False, "No file selected."
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_IMG_EXT:
        return False, f"Invalid file type '{ext}'. Only JPG, PNG, WEBP or BMP allowed."
    ct = (file.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in _ALLOWED_IMG_MIME:
        return False, f"Invalid content type '{ct}'. Only image files accepted."
    header = file.stream.read(8)
    file.stream.seek(0)
    for magic in _IMG_MAGIC.get(ext, ()):
        if not header.startswith(magic):
            return False, "File content does not match its extension. Upload a real image."
    file.stream.seek(0, 2)
    size_mb = file.stream.tell() / (1024 * 1024)
    file.stream.seek(0)
    if size_mb > _MAX_PHOTO_SIZE_MB:
        return False, f"Photo too large ({size_mb:.1f} MB). Maximum: {_MAX_PHOTO_SIZE_MB} MB."
    clean, scan_err = _scan_for_malware(file)
    if not clean:
        return False, scan_err
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
        app_log.critical(
            "ENCRYPTION_KEY is set but invalid — PII fields will be stored in plaintext. "
            "Regenerate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
else:
    if os.environ.get("APP_ENV", "production") != "development":
        raise RuntimeError(
            "ENCRYPTION_KEY is not set — refusing to start. "
            "Aadhaar, PAN, and bank account numbers require encryption in production. "
            "Generate a key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    else:
        app_log.critical(
            "ENCRYPTION_KEY is not set — PII fields will be stored in plaintext. "
            "Generate a key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

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
def _hash_token(token: str) -> str:
    """SHA-256 hash a Bearer token before storing/comparing in DB."""
    return hashlib.sha256(token.encode()).hexdigest()

_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_MINUTES = 15

def _check_login_lockout(identifier: str, attempt_type: str = "admin"):
    """Return (is_locked, locked_until_str). Raises nothing."""
    try:
        with _db() as (cur, _):
            cur.execute(
                "SELECT locked_until FROM login_attempts WHERE identifier=%s AND attempt_type=%s",
                (identifier, attempt_type)
            )
            row = cur.fetchone()
        if row and row[0] and row[0] > datetime.datetime.now():
            return True, row[0].strftime("%H:%M")
    except Exception:
        pass
    return False, None

def _record_login_failure(identifier: str, attempt_type: str = "admin"):
    """Increment failure counter; lock account after _LOGIN_MAX_ATTEMPTS."""
    try:
        with _db() as (cur, conn):
            cur.execute(
                "INSERT INTO login_attempts (identifier, attempt_type, failed_count, last_attempt) "
                "VALUES (%s, %s, 1, NOW()) "
                "ON CONFLICT (identifier, attempt_type) DO UPDATE SET "
                "failed_count=login_attempts.failed_count+1, last_attempt=NOW()",
                (identifier, attempt_type)
            )
            conn.commit()
            cur.execute(
                "SELECT failed_count FROM login_attempts WHERE identifier=%s AND attempt_type=%s",
                (identifier, attempt_type)
            )
            row = cur.fetchone()
            if row and row[0] >= _LOGIN_MAX_ATTEMPTS:
                lockout_until = datetime.datetime.now() + datetime.timedelta(minutes=_LOGIN_LOCKOUT_MINUTES)
                cur.execute(
                    "UPDATE login_attempts SET locked_until=%s WHERE identifier=%s AND attempt_type=%s",
                    (lockout_until, identifier, attempt_type)
                )
                conn.commit()
    except Exception:
        pass

def _clear_login_failures(identifier: str, attempt_type: str = "admin"):
    """Reset failure counter on successful login."""
    try:
        with _db() as (cur, conn):
            cur.execute(
                "DELETE FROM login_attempts WHERE identifier=%s AND attempt_type=%s",
                (identifier, attempt_type)
            )
            conn.commit()
    except Exception:
        pass

@contextmanager
def _db():
    """Open a DB connection + buffered cursor; always close both on exit."""
    conn   = get_db_connection()
    cursor = conn.cursor(buffered=True)
    try:
        yield cursor, conn
    finally:
        try:  cursor.close()
        except Exception as _e: app_log.debug("cursor.close() failed: %s", _e)
        try:  conn.close()
        except Exception as _e: app_log.debug("conn.close() failed: %s", _e)

# ---------------- DB MIGRATION ----------------
# Trigger function backing every `... ON UPDATE CURRENT_TIMESTAMP`-style
# column from the old MySQL schema — Postgres has no column-level
# equivalent, so each such table gets a BEFORE UPDATE trigger calling this.
_UPDATED_AT_TRIGGER_FN = """
    CREATE OR REPLACE FUNCTION _set_updated_at() RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
"""

def _attach_updated_at_trigger(cursor, table):
    cursor.execute(f'DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}')
    cursor.execute(f"""
        CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION _set_updated_at()
    """)

def init_db():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute(_UPDATED_AT_TRIGGER_FN)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) DEFAULT NULL,
            face_image VARCHAR(255),
            qr_code VARCHAR(255)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            login_time TIME DEFAULT NULL,
            logout_time TIME DEFAULT NULL,
            status VARCHAR(50) DEFAULT NULL,
            logout_status VARCHAR(50) DEFAULT NULL,
            attendance_type VARCHAR(50) DEFAULT NULL,
            UNIQUE (employee_id, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            id SERIAL PRIMARY KEY,
            date DATE UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salary_config (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            salary_per_day DECIMAL(10,2) DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll_config (
            id SERIAL PRIMARY KEY,
            pf_employee_pct DECIMAL(5,2) DEFAULT 12.00,
            pf_employer_pct DECIMAL(5,2) DEFAULT 12.00,
            professional_tax DECIMAL(8,2) DEFAULT 200.00,
            tds_annual_pct DECIMAL(5,2) DEFAULT 0.00,
            pf_basic_cap DECIMAL(10,2) DEFAULT 15000.00
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(150) DEFAULT NULL,
            reset_token VARCHAR(64) DEFAULT NULL,
            reset_token_expiry TIMESTAMP DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id SERIAL PRIMARY KEY,
            smtp_host VARCHAR(150) NOT NULL,
            smtp_port INT NOT NULL DEFAULT 587,
            smtp_user VARCHAR(150) NOT NULL,
            smtp_pass VARCHAR(255) NOT NULL,
            from_name VARCHAR(100) DEFAULT 'HR Department',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _attach_updated_at_trigger(cursor, "email_config")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            leave_date DATE NOT NULL,
            reason VARCHAR(500) NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            recipient_type VARCHAR(20) NOT NULL CHECK (recipient_type IN ('admin', 'employee')),
            employee_id VARCHAR(50) NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resignation_requests (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            last_working_day DATE NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            category VARCHAR(100) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            priority VARCHAR(20) DEFAULT 'Medium',
            status VARCHAR(30) DEFAULT 'Open',
            admin_response TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _attach_updated_at_trigger(cursor, "tickets")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            start_time TIME NOT NULL,
            half_time  TIME NOT NULL,
            end_time   TIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            priority VARCHAR(20) DEFAULT 'Normal' CHECK (priority IN ('Normal','Important','Urgent')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS break_config (
            id SERIAL PRIMARY KEY,
            break_name VARCHAR(100) NOT NULL,
            break_time TIME NOT NULL,
            duration_minutes INT NOT NULL DEFAULT 10,
            is_active SMALLINT DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_goals (
            id SERIAL PRIMARY KEY,
            title VARCHAR(150) NOT NULL,
            description TEXT,
            incentive_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            is_active SMALLINT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_incentives (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            company VARCHAR(150) NOT NULL,
            designation VARCHAR(100) NOT NULL,
            from_year VARCHAR(10) NOT NULL,
            to_year VARCHAR(10) DEFAULT NULL,
            is_current SMALLINT DEFAULT 0,
            description TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_education (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            annual_quota INT NOT NULL DEFAULT 12,
            is_paid SMALLINT DEFAULT 1,
            is_active SMALLINT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_balances (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            leave_type_id INT NOT NULL,
            year INT NOT NULL,
            total_days INT NOT NULL DEFAULT 0,
            used_days DECIMAL(4,1) NOT NULL DEFAULT 0,
            UNIQUE (employee_id, leave_type_id, year)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_documents (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            quarter SMALLINT NOT NULL,
            year INT NOT NULL,
            overall_rating DECIMAL(3,1) DEFAULT 0,
            reviewer_feedback TEXT,
            employee_comment TEXT,
            status VARCHAR(20) DEFAULT 'Draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (employee_id, quarter, year)
        )
    """)
    _attach_updated_at_trigger(cursor, "performance_reviews")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_kpis (
            id SERIAL PRIMARY KEY,
            review_id INT NOT NULL,
            kpi_title VARCHAR(200) NOT NULL,
            description TEXT,
            target VARCHAR(200),
            achievement VARCHAR(200),
            weight INT DEFAULT 20,
            rating SMALLINT DEFAULT 0,
            comments TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hike_config (
            id SERIAL PRIMARY KEY,
            label VARCHAR(80) NOT NULL,
            min_rating DECIMAL(3,1) NOT NULL,
            max_rating DECIMAL(3,1) NOT NULL,
            hike_pct DECIMAL(5,2) DEFAULT 0,
            incentive_pct DECIMAL(5,2) DEFAULT 0,
            color VARCHAR(20) DEFAULT '#1e3a8a'
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM hike_config")
    if cursor.fetchone()[0] == 0:
        for _lbl, _mn, _mx, _hp, _ip, _clr in [
            ("Exceptional",          4.5, 5.0, 20.00, 15.00, "#15803d"),
            ("Exceeds Expectations", 4.0, 4.4, 15.00, 10.00, "#2563eb"),
            ("Meets Expectations",   3.0, 3.9, 10.00,  5.00, "#7c3aed"),
            ("Needs Improvement",    2.0, 2.9,  5.00,  0.00, "#d97706"),
            ("Below Expectations",   0.0, 1.9,  0.00,  0.00, "#dc2626"),
        ]:
            cursor.execute(
                "INSERT INTO hike_config (label, min_rating, max_rating, hike_pct, incentive_pct, color) VALUES (%s,%s,%s,%s,%s,%s)",
                (_lbl, _mn, _mx, _hp, _ip, _clr)
            )
        db.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overtime_records (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            shift_end TIME NOT NULL,
            actual_logout TIME NOT NULL,
            ot_minutes INT NOT NULL DEFAULT 0,
            ot_pay DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'Pending',
            notes TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (employee_id, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_templates (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            is_active SMALLINT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_template_tasks (
            id SERIAL PRIMARY KEY,
            template_id INT NOT NULL,
            task_title VARCHAR(300) NOT NULL,
            task_description TEXT,
            requires_document SMALLINT DEFAULT 0,
            due_days INT DEFAULT 7,
            sort_order INT DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_onboarding (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            onboarding_id INT NOT NULL,
            template_task_id INT NOT NULL,
            employee_id VARCHAR(50) NOT NULL,
            task_title VARCHAR(300) NOT NULL,
            task_description TEXT,
            requires_document SMALLINT DEFAULT 0,
            due_days INT DEFAULT 7,
            status VARCHAR(20) DEFAULT 'Pending',
            completed_at TIMESTAMP NULL,
            document_path VARCHAR(500),
            admin_notes TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offer_letters (
            id SERIAL PRIMARY KEY,
            onboarding_id INT NOT NULL,
            employee_id VARCHAR(50) NOT NULL,
            designation VARCHAR(150),
            department VARCHAR(150),
            work_location VARCHAR(200),
            monthly_ctc DECIMAL(12,2) DEFAULT 0,
            joining_date DATE,
            offer_valid_until DATE,
            probation_months INT DEFAULT 6,
            reporting_to VARCHAR(150),
            additional_notes TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP DEFAULT NULL,
            status VARCHAR(20) DEFAULT 'draft',
            notice_period_days INT DEFAULT 30,
            candidate_address TEXT
        )
    """)
    for _col, _sql in [
        ("notice_period_days", "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS notice_period_days INT DEFAULT 30"),
        ("candidate_address",  "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS candidate_address TEXT"),
        ("response_token",         "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS response_token VARCHAR(64) DEFAULT NULL"),
        ("candidate_response",     "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS candidate_response VARCHAR(20) DEFAULT NULL"),
        ("responded_at",           "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS responded_at TIMESTAMP DEFAULT NULL"),
        ("response_token_expiry",  "ALTER TABLE offer_letters ADD COLUMN IF NOT EXISTS response_token_expiry TIMESTAMP DEFAULT NULL"),
    ]:
        try:
            cursor.execute(_sql); db.commit()
        except psycopg2.Error:
            db.rollback()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            actor VARCHAR(100) NOT NULL,
            actor_type VARCHAR(20) DEFAULT 'admin',
            action VARCHAR(150) NOT NULL,
            target_table VARCHAR(100),
            target_id VARCHAR(100),
            detail TEXT,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actor ON audit_logs (actor)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_action ON audit_logs (action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON audit_logs (created_at)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id SERIAL PRIMARY KEY,
            identifier VARCHAR(150) NOT NULL,
            attempt_type VARCHAR(20) DEFAULT 'admin',
            failed_count INT DEFAULT 0,
            last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            locked_until TIMESTAMP DEFAULT NULL,
            UNIQUE (identifier, attempt_type)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_queue (
            id           SERIAL PRIMARY KEY,
            to_email     VARCHAR(255) NOT NULL,
            subject      VARCHAR(500) NOT NULL,
            html_body    TEXT   NOT NULL,
            attachment_b64 TEXT   DEFAULT NULL,
            attachment_filename VARCHAR(255) DEFAULT NULL,
            status       VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','sending','done','failed')),
            attempts     SMALLINT DEFAULT 0,
            last_error   TEXT DEFAULT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at      TIMESTAMP DEFAULT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_status ON email_queue (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_created ON email_queue (created_at)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll_runs (
            id SERIAL PRIMARY KEY,
            year INT NOT NULL,
            month INT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_by VARCHAR(100),
            email_count INT DEFAULT 0,
            UNIQUE (year, month)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compoff_balance (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL UNIQUE,
            earned_minutes INT DEFAULT 0,
            used_minutes INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _attach_updated_at_trigger(cursor, "compoff_balance")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_tokens (
            token VARCHAR(64) PRIMARY KEY,
            token_type VARCHAR(20) NOT NULL DEFAULT 'admin',
            identity VARCHAR(100) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_biometric_proofs (
            employee_id VARCHAR(50) PRIMARY KEY,
            nonce VARCHAR(64) DEFAULT NULL,
            nonce_expires_at TIMESTAMP DEFAULT NULL,
            verified_at TIMESTAMP DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regularization_requests (
            id SERIAL PRIMARY KEY,
            employee_id VARCHAR(50) NOT NULL,
            request_date DATE NOT NULL,
            login_time TIME DEFAULT NULL,
            logout_time TIME DEFAULT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            admin_note TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP DEFAULT NULL,
            UNIQUE (employee_id, request_date)
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            code VARCHAR(20) DEFAULT NULL,
            working_days VARCHAR(30) DEFAULT 'Mon,Tue,Wed,Thu,Fri',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_feature_settings (
            company_id INT PRIMARY KEY,
            face_auth_enabled  SMALLINT DEFAULT 1,
            qr_enabled         SMALLINT DEFAULT 1,
            fingerprint_enabled SMALLINT DEFAULT 0,
            geo_enabled        SMALLINT DEFAULT 0,
            geo_radius         INT DEFAULT 300,
            pin_enabled        SMALLINT DEFAULT 1,
            biometric_enabled  SMALLINT DEFAULT 0,
            notify_leave       SMALLINT DEFAULT 1,
            notify_payslip     SMALLINT DEFAULT 1,
            notify_resignation SMALLINT DEFAULT 1,
            notify_doc_expiry  SMALLINT DEFAULT 1,
            session_timeout    INT DEFAULT 30,
            late_deduction_pct DECIMAL(5,2) DEFAULT 10.00,
            half_day_deduction_pct DECIMAL(5,2) DEFAULT 50.00,
            grace_minutes      INT DEFAULT 15,
            holiday_pay        VARCHAR(20) DEFAULT 'paid' CHECK (holiday_pay IN ('paid','unpaid')),
            leave_pay          VARCHAR(20) DEFAULT 'exclude' CHECK (leave_pay IN ('exclude','absent')),
            shift_start        TIME DEFAULT '09:00:00',
            shift_half         TIME DEFAULT '13:00:00',
            shift_end          TIME DEFAULT '18:00:00',
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    db.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shift_swap_requests (
            id SERIAL PRIMARY KEY,
            requester_id VARCHAR(50) NOT NULL,
            target_id VARCHAR(50) NOT NULL,
            requester_shift_id INT NOT NULL,
            target_shift_id INT NOT NULL,
            reason TEXT,
            status VARCHAR(20) DEFAULT 'Pending_Target' CHECK (status IN ('Pending_Target','Pending_Admin','Approved','Rejected','Rejected_Admin')),
            target_response TEXT,
            admin_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _attach_updated_at_trigger(cursor, "shift_swap_requests")
    db.commit()

    # Create company_settings table (must precede the migration loop below,
    # which ALTERs this table — on a fresh install with nothing to migrate
    # from, an ALTER before the table exists silently no-ops instead of
    # erroring, so column order here isn't just cosmetic).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_settings (
            id SERIAL PRIMARY KEY,
            company_name VARCHAR(200) DEFAULT 'My Company',
            company_tagline VARCHAR(300) DEFAULT 'Employee Attendance System',
            company_logo VARCHAR(255) DEFAULT NULL,
            currency_symbol VARCHAR(10) DEFAULT '₹',
            timezone VARCHAR(60) DEFAULT 'Asia/Kolkata',
            setup_done SMALLINT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _attach_updated_at_trigger(cursor, "company_settings")
    db.commit()
    # Add default shift columns if not present
    for col, default in [("shift_start","09:00:00"), ("shift_half","13:00:00"), ("shift_end","18:00:00")]:
        try:
            cursor.execute(f"ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS {col} TIME DEFAULT '{default}'")
            db.commit()
        except Exception:
            pass

    # Migrations for existing installs
    for sql in [
        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS logout_status VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS attendance_type VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS role VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS password VARCHAR(255) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS shift_id INT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS date_of_joining DATE DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS phone VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS gender VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS dob DATE DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS blood_group VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS address TEXT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS city VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS state VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS pincode VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS emergency_contact_relation VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS aadhar_number VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS pan_number VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS bank_account VARCHAR(30) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS bank_ifsc VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS uan_number VARCHAR(30) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_mode VARCHAR(20) DEFAULT 'office'",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_lat DECIMAL(10,8) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_lon DECIMAL(11,8) DEFAULT NULL",
        "ALTER TABLE salary_config ADD COLUMN IF NOT EXISTS last_revised DATE DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(64) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP DEFAULT NULL",
        "ALTER TABLE email_config ADD COLUMN IF NOT EXISTS from_email VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS about_me TEXT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS manager_name VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS manager_id VARCHAR(20) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS department VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS designation VARCHAR(150) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_active SMALLINT DEFAULT 1",
        "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS leave_type_id INT DEFAULT NULL",
        "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS is_half_day SMALLINT DEFAULT 0",
        "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS half_day_session VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS company_code VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'admin'",
        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS worked_minutes INT DEFAULT 0",
        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS last_relogin TIME DEFAULT NULL",
        "ALTER TABLE salary_config ADD COLUMN IF NOT EXISTS monthly_ctc DECIMAL(12,2) DEFAULT 0",
        "ALTER TABLE salary_config ADD COLUMN IF NOT EXISTS basic_pct INT DEFAULT 50",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS compoff_min_ot_minutes INT DEFAULT 120",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS compoff_minutes_per_day INT DEFAULT 480",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS late_deduction_pct DECIMAL(5,2) DEFAULT 10.00",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS half_day_deduction_pct DECIMAL(5,2) DEFAULT 50.00",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS grace_minutes INT DEFAULT 15",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS holiday_pay VARCHAR(20) DEFAULT 'paid' CHECK (holiday_pay IN ('paid','unpaid'))",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS leave_pay VARCHAR(20) DEFAULT 'exclude' CHECK (leave_pay IN ('exclude','absent'))",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS joining_date DATE DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS company_id INT DEFAULT NULL",
        "ALTER TABLE employee_documents ADD COLUMN IF NOT EXISTS expiry_date DATE DEFAULT NULL",
        "ALTER TABLE overtime_records ADD COLUMN IF NOT EXISTS requested_by_employee SMALLINT DEFAULT 0",
        "ALTER TABLE overtime_records ADD COLUMN IF NOT EXISTS employee_reason VARCHAR(500) DEFAULT NULL",
        "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP DEFAULT NULL",
        "ALTER TABLE salary_config ADD COLUMN IF NOT EXISTS last_hike_quarter SMALLINT DEFAULT NULL",
        "ALTER TABLE salary_config ADD COLUMN IF NOT EXISTS last_hike_year INT DEFAULT NULL",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS default_onboarding_template_id INT DEFAULT NULL",
        "ALTER TABLE employee_onboarding_tasks ADD COLUMN IF NOT EXISTS employee_note VARCHAR(500) DEFAULT NULL",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS fingerprint_enabled SMALLINT DEFAULT 0",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS qr_enabled SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS face_enabled SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS location_enabled SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS employee_password_auth SMALLINT DEFAULT 1",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS fingerprint_credential_id VARCHAR(512) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS fingerprint_public_key TEXT DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS fingerprint_sign_count INT DEFAULT 0",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS face_auth_enabled SMALLINT DEFAULT 0",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS geo_enabled SMALLINT DEFAULT 0",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS geo_radius INT DEFAULT 100",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS pin_enabled SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS biometric_enabled SMALLINT DEFAULT 0",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS notify_leave SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS notify_payslip SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS notify_resignation SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS notify_doc_expiry SMALLINT DEFAULT 1",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS session_timeout INT DEFAULT 30",
        "ALTER TABLE company_settings ADD COLUMN IF NOT EXISTS working_days VARCHAR(30) DEFAULT 'Mon,Tue,Wed,Thu,Fri'",
        "ALTER TABLE break_config ADD COLUMN IF NOT EXISTS break_type VARCHAR(20) DEFAULT 'coffee' CHECK (break_type IN ('coffee','lunch','custom'))",
        "ALTER TABLE break_config ADD COLUMN IF NOT EXISTS shift_id INT DEFAULT NULL",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS working_days VARCHAR(30) DEFAULT 'Mon,Tue,Wed,Thu,Fri'",
        "ALTER TABLE onboarding_templates ADD COLUMN IF NOT EXISTS role VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE shifts ADD COLUMN IF NOT EXISTS company_id INT DEFAULT NULL",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS pin VARCHAR(10) DEFAULT NULL",
        "ALTER TABLE break_config ADD COLUMN IF NOT EXISTS company_id INT DEFAULT NULL",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public','private'))",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS target_employee_id VARCHAR(50) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS reset_token VARCHAR(80) DEFAULT NULL",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP DEFAULT NULL",
    ]:
        try:
            cursor.execute(sql)
            db.commit()
        except psycopg2.Error:
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
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS force_pin_change SMALLINT DEFAULT 0")
        db.commit()
    except psycopg2.Error:
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

    # Performance indexes migration
    try:
        cursor.execute("SELECT 1 FROM _applied_migrations WHERE name='perf_indexes_v1'")
        if not cursor.fetchone():
            _idx_stmts = [
                "CREATE INDEX IF NOT EXISTS idx_leave_emp ON leave_requests(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_leave_status ON leave_requests(status)",
                "CREATE INDEX IF NOT EXISTS idx_tickets_emp ON tickets(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
                "CREATE INDEX IF NOT EXISTS idx_resign_emp ON resignation_requests(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_notif_emp ON notifications(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_notif_read ON notifications(is_read)",
                "CREATE INDEX IF NOT EXISTS idx_onboard_emp ON employee_onboarding(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_onboard_status ON employee_onboarding(status)",
                "CREATE INDEX IF NOT EXISTS idx_payroll_emp ON payroll_runs(employee_id)",
            ]
            for stmt in _idx_stmts:
                try:
                    cursor.execute(stmt)
                    db.commit()
                except Exception:
                    db.rollback()
            cursor.execute("INSERT INTO _applied_migrations (name) VALUES ('perf_indexes_v1')")
            db.commit()
    except Exception:
        pass

    # Performance indexes v2 — high-traffic columns missing from v1
    try:
        cursor.execute("SELECT 1 FROM _applied_migrations WHERE name='perf_indexes_v2'")
        if not cursor.fetchone():
            _idx_stmts_v2 = [
                "CREATE INDEX IF NOT EXISTS idx_att_date ON attendance(date)",
                "CREATE INDEX IF NOT EXISTS idx_emp_active ON employees(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_emp_company ON employees(company_id)",
                "CREATE INDEX IF NOT EXISTS idx_leave_date ON leave_requests(leave_date)",
            ]
            for stmt in _idx_stmts_v2:
                try:
                    cursor.execute(stmt)
                    db.commit()
                except Exception:
                    db.rollback()
            cursor.execute("INSERT INTO _applied_migrations (name) VALUES ('perf_indexes_v2')")
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
        app_log.info("Admin created: username=%s", _admin_user)
        admin_count = 1
    elif admin_count == 0 and not _admin_pass:
        app_log.warning("ADMIN_PASSWORD not set in .env — complete setup via /setup")

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
            ON CONFLICT (employee_id, leave_type_id, year) DO UPDATE SET
                total_days = CASE WHEN leave_balances.used_days = 0
                                  THEN EXCLUDED.total_days ELSE leave_balances.total_days END
        """, (employee_id, lt_id, year, quota))


def init_master_db():
    """Create the att_master tenant-registry schema and its tenants table if
    they don't exist. Postgres has no mid-connection database switch, so this
    is a schema within the shared database now, not a separate physical
    database the way MySQL's att_master was."""
    try:
        # Schema must exist before get_master_db() can SET search_path to it,
        # so this first connection stays on the default (public) schema —
        # get_db_connection() now always resets search_path explicitly on
        # every borrow, so it's safe to use here without leaking att_master
        # onto whichever connection the pool hands out next.
        db = get_db_connection()
        cur = db.cursor()
        cur.execute('CREATE SCHEMA IF NOT EXISTS att_master')
        db.commit()
        cur.close(); db.close()

        from database import get_master_db
        db = get_master_db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(200) NOT NULL,
                subdomain VARCHAR(100) UNIQUE NOT NULL,
                db_name VARCHAR(100) UNIQUE NOT NULL,
                admin_email VARCHAR(200) DEFAULT NULL,
                plan VARCHAR(50) DEFAULT 'starter',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        cur.close()
        db.close()
    except Exception as _e:
        app_log.warning("init_master_db failed (non-fatal for single-tenant mode): %s", _e)


def init_tenant_db(schema_name: str):
    """Initialize schema in a freshly created tenant schema."""
    from flask import g as _g
    _g.tenant_db = schema_name
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
        # If both admin and employee keys exist, drop the employee key and continue as admin
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.pop("employee_id", None)
            session.pop("employee_name", None)
            session.pop("employee_role", None)
        if not session.get("admin_logged_in"):
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Accept", "").startswith("application/json")
                or request.headers.get("Content-Type", "").startswith("application/json")
                or request.is_json
            )
            if is_ajax:
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.", "redirect": url_for("auth.admin_login")}), 401
            return redirect(url_for("auth.admin_login"))
        return f(*args, **kwargs)
    return wrapper

def employee_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # If admin is also logged in, redirect to admin panel instead of clearing session
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.pop("employee_id", None)
            session.pop("employee_name", None)
            session.pop("employee_role", None)
            return redirect("/admin")
        if not session.get("employee_id"):
            return redirect("/employee_login")
        if session.get("_fpc") and request.endpoint != "force_change_pin":
            return redirect("/force_change_pin")
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
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.", "redirect": url_for("auth.admin_login")}), 401
            return redirect(url_for("auth.admin_login"))
        admin_role = session.get("admin_role", "admin")
        if admin_role not in ("admin", "manager"):
            return jsonify({"ok": False, "msg": "Insufficient permissions."}), 403
        return f(*args, **kwargs)
    return wrapper

# ---------------- ATTENDANCE HELPERS ----------------
def _td_to_time(val):
    """Convert a timedelta or datetime.time to datetime.time. psycopg2
    already returns TIME columns as datetime.time (returned as-is below);
    the timedelta path handles values computed via time arithmetic elsewhere
    in the app, and is what mysql-connector used to return directly."""
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
    if attendance_type == "Full Day":
        return 0.0
    if attendance_type == "Approved Leave":
        # If leave is configured as 'absent', deduct full day; else no deduction
        return spd if LEAVE_PAY == 'absent' else 0.0
    if attendance_type == "Holiday":
        # If holiday is unpaid, deduct full day
        return spd if HOLIDAY_PAY == 'unpaid' else 0.0
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
            ON CONFLICT (employee_id, date) DO UPDATE SET
                actual_logout=EXCLUDED.actual_logout, ot_minutes=EXCLUDED.ot_minutes, ot_pay=EXCLUDED.ot_pay
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
            "host": row[0], "port": row[1], "user": row[2], "password": decrypt_pii(row[3]),
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

def get_admin_emails():
    """Return a list of all admin email addresses that have been set."""
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT email FROM admin_users WHERE email IS NOT NULL AND email != ''")
    emails = [row[0] for row in cursor.fetchall()]
    cursor.close(); db.close()
    return emails

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
    port = int(config.get("port", 587))
    if port == 465:
        # Implicit SSL (port 465)
        with smtplib.SMTP_SSL(config["host"], port, context=context, timeout=20) as server:
            server.login(config["user"], config["password"])
            server.sendmail(from_addr, to_email, msg.as_string())
    else:
        # STARTTLS (port 587 / 25)
        with smtplib.SMTP(config["host"], port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(config["user"], config["password"])
            server.sendmail(from_addr, to_email, msg.as_string())

def send_email_async(to_email, subject, html_body, config,
                     attachment_bytes=None, attachment_filename=None, **_):
    """Enqueue an email for reliable delivery via the DB-backed email worker."""
    att_b64 = None
    if attachment_bytes:
        att_b64 = base64.b64encode(attachment_bytes).decode()
    try:
        db  = get_db_connection()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO email_queue (to_email, subject, html_body, attachment_b64, attachment_filename) "
            "VALUES (%s,%s,%s,%s,%s)",
            (to_email, subject, html_body, att_b64, attachment_filename)
        )
        db.commit()
        cur.close(); db.close()
    except Exception as e:
        app_log.error("Failed to enqueue email to %s: %s", to_email, e)
        # Fall back to in-process send so the email is not silently dropped
        threading.Thread(
            target=lambda: send_email_smtp(to_email, subject, html_body, config,
                                           attachment_bytes=attachment_bytes,
                                           attachment_filename=attachment_filename),
            daemon=True
        ).start()


def _email_queue_worker():
    """Background thread: dequeues and sends emails, retries up to 3 times."""
    import time as _time
    while True:
        try:
            cfg = get_email_config()
            if not cfg:
                _time.sleep(30)
                continue
            db  = get_db_connection()
            cur = db.cursor(buffered=True)
            cur.execute(
                "SELECT id, to_email, subject, html_body, attachment_b64, attachment_filename "
                "FROM email_queue WHERE status='pending' AND attempts < 3 "
                "ORDER BY created_at LIMIT 10"
            )
            rows = cur.fetchall()
            for row in rows:
                eid, to_email, subject, html_body, att_b64, att_name = row
                cur.execute(
                    "UPDATE email_queue SET status='sending', attempts=attempts+1 WHERE id=%s", (eid,)
                )
                db.commit()
                try:
                    att_bytes = base64.b64decode(att_b64) if att_b64 else None
                    send_email_smtp(to_email, subject, html_body, cfg,
                                    attachment_bytes=att_bytes,
                                    attachment_filename=att_name)
                    cur.execute(
                        "UPDATE email_queue SET status='done', sent_at=NOW() WHERE id=%s", (eid,)
                    )
                except Exception as exc:
                    app_log.error("Email queue: send failed to %s: %s", to_email, exc)
                    cur.execute(
                        "UPDATE email_queue SET status='pending', last_error=%s WHERE id=%s",
                        (str(exc)[:500], eid)
                    )
                db.commit()
            cur.execute(
                "UPDATE email_queue SET status='failed' "
                "WHERE status='pending' AND attempts >= 3"
            )
            db.commit()
            cur.close(); db.close()
        except Exception as _we:
            app_log.error("Email queue worker error: %s", _we)
        _time.sleep(15)


# Start the email queue worker once (gunicorn spawns multiple workers; each gets its own thread)
threading.Thread(target=_email_queue_worker, daemon=True, name="email-queue-worker").start()

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

# ---------------- ERROR ALERTING (malfunction detection) ----------------
# The catch-all exception handler below tells users "the team has been
# notified" — this is what actually makes that true. Emails admins on
# unhandled errors, deduped by error signature so one hot failing endpoint
# can't flood inboxes or the email_queue table.
_error_alert_cache = {}
_error_alert_lock  = threading.Lock()
_ERROR_ALERT_COOLDOWN = 900  # 15 min — same error signature won't re-alert sooner

def _alert_on_error(tb_text, context=""):
    """Best-effort: any failure here is swallowed so alerting can never
    mask or crash on top of the original error being reported."""
    try:
        # Dedup key = exception type + the line that actually raised it, not
        # the full traceback (which varies request-to-request — different
        # IDs, line numbers in called code, etc. would defeat deduping).
        last_line = tb_text.strip().splitlines()[-1] if tb_text.strip() else "unknown"
        sig = hashlib.sha256(last_line.encode()).hexdigest()[:16]
        now = time.time()
        with _error_alert_lock:
            last_sent = _error_alert_cache.get(sig)
            if last_sent and now - last_sent < _ERROR_ALERT_COOLDOWN:
                return
            _error_alert_cache[sig] = now
            if len(_error_alert_cache) > 500:  # cap unbounded growth
                _error_alert_cache.clear()

        cfg = get_email_config()
        if not cfg:
            return
        admins = get_admin_emails()
        if not admins:
            return

        body = (
            "<pre style='white-space:pre-wrap;font-family:monospace;font-size:13px'>"
            f"Time: {datetime.datetime.now().isoformat()}\n"
            f"Route: {_html.escape(context or 'unknown')}\n"
            f"Method: {_html.escape(request.method if request else 'n/a')}\n"
            f"Remote IP: {_html.escape(request.remote_addr or '') if request else 'n/a'}\n\n"
            f"{_html.escape(tb_text)}</pre>"
        )
        subject = f"⚠️ Application error — {context or 'unknown route'}"
        for admin_email in admins:
            send_email_async(admin_email, subject, body, cfg)
    except Exception as _alert_err:
        app_log.error("Failed to send error alert email: %s", _alert_err)


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
    app_log.error("500 error: %s", tb.replace('\n', '\\n'))
    _alert_on_error(tb, context=request.path if request else "")
    return _error_page(500, "⚙️", "Internal Server Error",
        "Something went wrong on our end. The error has been logged.",
        "Please try again in a moment or contact your administrator.")

@app.errorhandler(Exception)
def unhandled_exception(e):
    if isinstance(e, HTTPException):
        return _error_page(e.code, "⚠️", e.name,
            "The page you requested could not be processed.",
            "Use the buttons below to navigate back.")
    tb = _traceback.format_exc()
    app_log.error("Unhandled exception: %s", tb.replace('\n', '\\n'))
    _alert_on_error(tb, context=request.path if request else "")
    return _error_page(500, "⚙️", "Internal Server Error",
        "An unexpected error occurred. The team has been notified.",
        "Please try again or contact your administrator.")

# ---------------- HOME ----------------

# ---------------- ADMIN LOGIN ----------------

# ---------------- LIVE DASHBOARD API ----------------

# ---------------- CHART DATA API ----------------


# ---------------- TODAY FILTERED VIEWS ----------------
def _today_pending_counts(cursor):
    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
    pl = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM resignation_requests WHERE status='Pending'")
    pr = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')")
    pt = cursor.fetchone()[0]
    return pl, pr, pt


# ---------------- ADMIN ACTIONS ----------------

# ---------------- SETTINGS (unified) ----------------

# ---------------- SAVE DEFAULT ONBOARDING TEMPLATE ----------------

# ---------------- SAVE SALARY RULES ----------------

# ---------------- TOGGLE AUTH METHOD ----------------
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


# ---------------- SAVE COMPANY CODE ----------------

# ---------------- SAVE COMPANY INFO ----------------

# ---------------- TOGGLE FEATURE (AJAX) ----------------

# ---------------- SAVE GEO RADIUS ----------------

# ---------------- SAVE SECURITY SETTINGS ----------------


# ---------------- COMPANIES ----------------


# ---------------- ANNOUNCEMENTS ----------------

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

# ---------------- VIEW HOLIDAYS (legacy helper — no route; /view_holidays redirects to /leave_holidays) ----------------
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
                           year=year, today=today,
        active_nav="leaves",
    )


# ---------------- EMPLOYEE DETAIL PAGE ----------------
# ---------------- ADD EMPLOYEE (from employees page) ----------------
# ---------------- UPDATE EMPLOYEE PHOTO ----------------
# ---------------- REGENERATE QR ----------------
# ---------------- LEAVE TYPES ADMIN ----------------


# ---------------- SHIFTS (redirect to settings) ----------------


# ──────────────────────── SHIFT SWAP REQUESTS ────────────────────────


# ---------------- AUTO GENERATE EMPLOYEE ID ----------------
# ---------------- BREAK CONFIG ----------------


# ---------------- VIEW SALARY CONFIG ----------------


# ---------------- MONTHLY ATTENDANCE REPORT ----------------

# ---------------- EMPLOYEE ATTENDANCE DETAIL ----------------

# ---------------- MANUAL ATTENDANCE CORRECTION ----------------


# ---------------- BULK MARK ATTENDANCE ----------------


# ---------------- MONTHLY REPORT EXCEL EXPORT ----------------

# ---------------- ABSENTEE REPORT EMAIL ----------------

# ---------------- SALARY REPORT ----------------


# ---------------- EMAIL CONFIG ----------------

# ---------------- SEND SALARY EMAIL (single) ----------------

# ---------------- SEND ALL SALARY EMAILS ----------------

# ---------------- PAYROLL LOCK / UNLOCK ----------------


# ---------------- TEST EMAIL ----------------

# ---------------- LOCATION ----------------

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

# ================================================================
#  EMPLOYEE PORTAL
# ================================================================


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


# ─────────────────────────── PERFORMANCE MANAGEMENT ───────────────────────────

RATING_LABELS = {0: "Not Rated", 1: "Unsatisfactory", 2: "Needs Improvement",
                 3: "Meets Expectations", 4: "Exceeds Expectations", 5: "Outstanding"}


# ================================================================
#  TICKETS  (web)
# ================================================================


# ================================================================
#  REST API  (used by the Flutter mobile app)
# ================================================================

def api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        token_hash = _hash_token(auth[7:])
        with _db() as (cursor, _conn):
            cursor.execute("DELETE FROM api_tokens WHERE expires_at < NOW()")
            _conn.commit()
            cursor.execute(
                "SELECT identity FROM api_tokens WHERE token=%s AND token_type='admin' AND expires_at > NOW()",
                (token_hash,)
            )
            row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        from flask import g as _g
        _g.api_user = row[0]
        return f(*args, **kwargs)
    return wrapper


# ---------------- API: LEAVE REQUESTS ----------------


# ---------------- API: RESIGNATION REQUESTS ----------------


def employee_api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        token_hash = _hash_token(auth[7:])
        with _db() as (cursor, _conn):
            cursor.execute("DELETE FROM api_tokens WHERE expires_at < NOW()")
            _conn.commit()
            cursor.execute(
                "SELECT identity FROM api_tokens WHERE token=%s AND token_type='employee' AND expires_at > NOW()",
                (token_hash,)
            )
            row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        from flask import g as _g
        _g.api_emp_id = row[0]
        return f(*args, **kwargs)
    return wrapper


def _fmt_t(t):
    if t is None: return None
    if hasattr(t, 'strftime'): return t.strftime("%H:%M:%S")
    total = int(t.total_seconds())
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, (total % 3600) // 60, total % 60)


_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')

def _wa_rp_id():
    """WebAuthn Relying Party ID.
    Loopback: return the exact host so the browser's origin matches.
    Everything else: prefer ALLOWED_ORIGINS[0] (avoids Host-header injection and
    ensures a proper domain name is used even when accessed via LAN IP).
    Falls back to the raw host only when ALLOWED_ORIGINS is unconfigured or '*'."""
    host = request.host.split(":")[0]
    # Loopback: must match the browser origin exactly; return immediately
    if host in ("127.0.0.1", "::1", "localhost"):
        return host
    # Named hosts and LAN IPs: use the pinned production domain when available
    if _allowed_origins != "*" and _allowed_origins:
        canonical = urlparse(_allowed_origins[0]).hostname
        if canonical:
            return canonical
    # NOTE: returning a non-loopback IP here will be rejected by browsers as an RP ID
    return host

def _wa_check_rp_id(rp_id):
    """Return an error string if rp_id is a non-loopback IP (browsers reject these as RP IDs),
    or None if it looks usable."""
    if rp_id in ("127.0.0.1", "::1", "localhost"):
        return None
    if _IP_RE.match(rp_id):
        return (
            f"WebAuthn does not support IP addresses as RP IDs (got '{rp_id}'). "
            "Access the server via 'localhost' on the server machine, or configure a "
            "hostname (e.g. add an entry in your hosts file and set ALLOWED_ORIGINS)."
        )
    return None

def _wa_origins():
    """Return the set of acceptable WebAuthn origins for this host.
    Always accepts both 127.0.0.1 and localhost as equivalent loopback origins.
    For LAN IPs the only valid origin is the exact IP+port the browser used."""
    host   = request.host  # includes port if non-standard
    scheme = request.scheme
    origins = {f"{scheme}://{host}"}
    bare   = host.split(":")[0]
    if bare == "127.0.0.1":
        origins.add(f"{scheme}://{host.replace('127.0.0.1', 'localhost')}")
    elif bare == "localhost":
        origins.add(f"{scheme}://{host.replace('localhost', '127.0.0.1')}")
    # LAN IPs: the single origin already added above is correct
    return list(origins)

def _wa_b64url_decode(s):
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def _wa_b64url_encode(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

# How long a real, just-completed WebAuthn assertion stays usable to authorize
# a single subsequent check-in call, scoped to the specific employee_id that
# completed it. Prevents both replay across employees and indefinite reuse.
_WA_FP_VERIFY_WINDOW_SEC = 120

def _wa_fingerprint_recently_verified(emp_id):
    """One-time, employee-bound check: did this employee just complete a real
    WebAuthn signature verification in this session? Consumes the proof."""
    emp_id = (emp_id or "").strip().upper()
    verified_emp = session.pop("wa_fp_verified_emp_id", None)
    verified_at  = session.pop("wa_fp_verified_at", 0)
    return bool(emp_id) and verified_emp == emp_id and (time.time() - verified_at) <= _WA_FP_VERIFY_WINDOW_SEC


# ---- Mobile-app biometric attestation -------------------------------------
# The mobile app has no browser, so it can't do real WebAuthn (no native
# platform-authenticator API in React Native) and has no Flask session
# cookie to piggyback the proof above on. Instead it gets a weaker but still
# meaningfully-bound proof: a server-issued, single-use nonce minted only to
# the holder of a valid employee Bearer token, consumed by a second
# Bearer-authenticated call right after the device's local biometric/PIN
# check succeeds. This is NOT a cryptographic signature — it cannot detect a
# cloned/replayed device biometric — but unlike the old flow it cannot be
# satisfied without first proving possession of that exact employee's token.
_MOBILE_BIO_NONCE_TTL_SEC    = 60
_MOBILE_BIO_VERIFY_WINDOW_SEC = 120

def _mobile_biometric_issue_nonce(emp_id):
    """Mint a fresh single-use nonce for emp_id, replacing any prior one."""
    nonce = secrets.token_hex(16)
    with _db() as (cursor, conn):
        cursor.execute(
            "INSERT INTO mobile_biometric_proofs (employee_id, nonce, nonce_expires_at, verified_at) "
            "VALUES (%s, %s, NOW() + %s * INTERVAL '1 second', NULL) "
            "ON CONFLICT (employee_id) DO UPDATE SET "
            "nonce=EXCLUDED.nonce, nonce_expires_at=EXCLUDED.nonce_expires_at, verified_at=NULL",
            (emp_id, nonce, _MOBILE_BIO_NONCE_TTL_SEC)
        )
        conn.commit()
    return nonce

def _mobile_biometric_attest(emp_id, nonce):
    """Consume a nonce after the mobile app confirms a local biometric/device
    check for this exact authenticated employee. Returns (ok, err_msg)."""
    if not nonce:
        return False, "Missing nonce"
    with _db() as (cursor, conn):
        cursor.execute(
            "SELECT nonce, nonce_expires_at FROM mobile_biometric_proofs WHERE employee_id=%s",
            (emp_id,)
        )
        row = cursor.fetchone()
        if not row or row[0] != nonce or not row[1] or row[1] < datetime.datetime.now():
            return False, "Invalid or expired nonce"
        cursor.execute(
            "UPDATE mobile_biometric_proofs SET nonce=NULL, nonce_expires_at=NULL, verified_at=NOW() "
            "WHERE employee_id=%s",
            (emp_id,)
        )
        conn.commit()
    return True, None

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


def _wa_verify_and_store_registration(emp_id, credential, challenge_b64, cursor, db):
    """Verify a WebAuthn registration response (real signature/attestation
    check) and persist the credential id + public key + sign count.
    `credential` may be a dict or a JSON string. Returns (ok, err_msg)."""
    if not _webauthn_available:
        return False, "Fingerprint enrollment is not available on this server."
    if not credential or not challenge_b64:
        return False, "Missing credential or challenge — please try enrolling again"
    # Rebuild the supported-alg list from session if available; fall back to the
    # same two algorithms we offer in generate_registration_options.
    _alg_ids = session.get("wa_reg_alg_ids") or [-7, -257]
    _supported_algs = [COSEAlgorithmIdentifier(v) for v in _alg_ids]
    _rp_id   = _wa_rp_id()
    _origins = _wa_origins()
    app_log.info("WebAuthn verify: emp=%s rp_id=%s origins=%s", emp_id, _rp_id, _origins)
    try:
        if isinstance(credential, str):
            credential = json.loads(credential)
        verified = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=_wa_b64url_decode(challenge_b64),
            expected_rp_id=_rp_id,
            expected_origin=_origins,
            supported_pub_key_algs=_supported_algs,
        )
    except Exception as exc:
        app_log.warning("WebAuthn registration failed: emp=%s rp_id=%s origins=%s err=%s",
                        emp_id, _rp_id, _origins, exc, exc_info=True)
        return False, f"Enrollment failed: {exc}"
    cred_id_b64 = _wa_b64url_encode(verified.credential_id)
    pubkey_b64  = base64.b64encode(verified.credential_public_key).decode()
    cursor.execute(
        "UPDATE employees SET fingerprint_credential_id=%s, fingerprint_public_key=%s, "
        "fingerprint_sign_count=%s WHERE employee_id=%s",
        (cred_id_b64, pubkey_b64, verified.sign_count, emp_id)
    )
    db.commit()
    return True, None


def _enroll_fingerprint_from_form(emp_id, cursor, db):
    """Shared by admin_action()/add_employee_page(): read the WebAuthn
    attestation posted by the registration form (if any), verify and store
    it, flashing a warning on failure. No-op if the field is empty."""
    fp_attestation = request.form.get("fingerprint_attestation", "").strip()
    if not fp_attestation:
        return
    _ok, _err = _wa_verify_and_store_registration(
        emp_id, fp_attestation, session.get("wa_reg_challenge"), cursor, db
    )
    session.pop("wa_reg_challenge", None)
    session.pop("wa_reg_alg_ids", None)
    if not _ok:
        flash(f"⚠️ Fingerprint enrollment failed verification: {_err}", "error")


# ---------------- API: TICKETS (employee) ----------------


# ---------------- API: EMPLOYEE — ATTENDANCE HISTORY ----------------


# ---------------- API: EMPLOYEE — LEAVE HISTORY + BALANCE ----------------


# ---------------- API: EMPLOYEE — CANCEL LEAVE ----------------


# ---------------- WEB: EMPLOYEE — CANCEL LEAVE ----------------


# ---------------- API: EMPLOYEE — REQUEST OVERTIME ----------------


# ---------------- API: ADMIN — DOCUMENT EXPIRY ALERTS ----------------


# ---------------- API: EMPLOYEE — HOLIDAYS ----------------


# ---------------- API: EMPLOYEE — PROFILE ----------------


# ---------------- API: TICKETS (admin) ----------------


# ---------------- PAY SLIPS ----------------


# ---------------- API: SHIFTS (JSON) ----------------


# ================================================================
#  FEATURE 1: ANALYTICS
# ================================================================


# ================================================================
#  FEATURE 2: DOCUMENT MANAGEMENT
# ================================================================

_DOC_ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'}

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


# ================================================================
#  FEATURE 3: OVERTIME TRACKING
# ================================================================


# ─────────────────────────── COMP-OFF MANAGEMENT ───────────────────────────


# Notification routes migrated to blueprints/notifications.py


# ── Tenant Provisioning ──────────────────────────────────────────────────────

_SUBDOMAIN_RE  = re.compile(r'^[a-z0-9\-]+$')
# Set SIGNUP_SECRET in .env to restrict who can create new organisations.
# Anyone who knows this token can provision a new tenant; keep it private.
_SIGNUP_SECRET = os.environ.get("SIGNUP_SECRET", "").strip()


# ─────────────────────────────────────────
#  ONBOARDING WORKFLOW
# ─────────────────────────────────────────


# ── OFFER LETTER ──────────────────────────────────────────────────────────────


def _generate_offer_letter_pdf(letter, co):
    """Build offer letter PDF with ReportLab and return bytes."""
    from io import BytesIO
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table,
                                    TableStyle, Spacer, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    BLUE  = rl_colors.HexColor("#1d4ed8")
    DARK  = rl_colors.HexColor("#111827")
    GRAY  = rl_colors.HexColor("#6b7280")
    LIGHT = rl_colors.HexColor("#f3f4f6")

    emp_name      = letter[17]
    designation   = letter[3] or "the offered position"
    department    = letter[4] or ""
    work_location = letter[5] or ""
    monthly_ctc   = float(letter[6]) if letter[6] else 0
    joining_date  = letter[7].strftime("%d %B %Y") if letter[7] else "—"
    valid_until   = letter[8].strftime("%d %B %Y") if letter[8] else "7 days from date of issue"
    probation     = letter[9] or 6
    reporting_to  = letter[10] or "the Department Head"
    notes         = letter[11] or ""
    gen_date      = letter[12].strftime("%d %B %Y") if letter[12] else ""
    notice_days   = letter[15] or 30
    ref_num       = f"OL/{letter[2].upper()}/{letter[12].strftime('%Y') if letter[12] else ''}/{letter[0]:04d}"
    company       = co.get("company_name", "Company")
    co_address    = co.get("address", "")
    co_email_val  = co.get("email", "")

    def ps(name, **kw):
        base = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=DARK)
        base.update(kw)
        return ParagraphStyle(name, **base)

    sNormal  = ps("normal")
    sBold    = ps("bold",   fontName="Helvetica-Bold")
    sSmall   = ps("small",  fontSize=8,  textColor=GRAY)
    sLabel   = ps("label",  fontSize=8,  fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=4)
    sCenter  = ps("center", alignment=TA_CENTER)
    sRight   = ps("right",  alignment=TA_RIGHT)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=14*mm, bottomMargin=16*mm)
    story = []

    # ── Blue top rule ──────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=4, color=BLUE, spaceAfter=8))

    # ── Letterhead row ─────────────────────────────────────────────────────
    addr_line = co_address
    if co_email_val:
        addr_line += f"  ·  {co_email_val}" if addr_line else co_email_val
    lh_data = [[
        [Paragraph(f"<b>{company}</b>", ps("co", fontSize=14, fontName="Helvetica-Bold")),
         Paragraph(addr_line, sSmall)],
        [Paragraph(f"<b>Date:</b> {gen_date}", sRight),
         Paragraph(f"<b>Ref:</b> {ref_num}", sRight)],
    ]]
    lh_tbl = Table(lh_data, colWidths=["55%", "45%"])
    lh_tbl.setStyle(TableStyle([
        ("VALIGN",  (0,0), (-1,-1), "TOP"),
        ("ALIGN",   (1,0), (1,-1),  "RIGHT"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(lh_tbl)
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor("#e5e7eb"), spaceAfter=10))

    # ── To block ───────────────────────────────────────────────────────────
    story.append(Paragraph("<b>To,</b>", sNormal))
    story.append(Paragraph(emp_name, sNormal))
    story.append(Paragraph(f"Employee ID: {letter[2]}", sNormal))
    story.append(Spacer(1, 8))

    # ── Subject ────────────────────────────────────────────────────────────
    story.append(Paragraph(f"<u><b>Sub: Offer of Employment — {designation}</b></u>", sNormal))
    story.append(Spacer(1, 10))

    # ── Salutation ─────────────────────────────────────────────────────────
    story.append(Paragraph(f"Dear <b>{emp_name}</b>,", sNormal))
    story.append(Spacer(1, 8))

    # ── Opening paragraphs ─────────────────────────────────────────────────
    dept_txt  = f" in the <b>{department}</b> department" if department else ""
    loc_txt   = f", located at <b>{work_location}</b>" if work_location else ""
    story.append(Paragraph(
        f"We are pleased to offer you the position of <b>{designation}</b>{dept_txt} "
        f"at <b>{company}</b>{loc_txt}. You will be reporting to <b>{reporting_to}</b>.",
        sNormal))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Your date of joining will be <b>{joining_date}</b>. Please report to the HR Department "
        f"on the joining date with your original documents for verification.",
        sNormal))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"At <b>{company}</b>, we believe in fostering a collaborative, growth-oriented environment "
        f"where every team member is empowered to make an impact. As a <b>{designation}</b>, "
        f"you will play a key role in driving our mission forward. We look forward to the "
        f"valuable perspective and expertise you will bring to the team.",
        sNormal))
    story.append(Spacer(1, 12))

    # ── Compensation ───────────────────────────────────────────────────────
    if monthly_ctc > 0:
        story.append(Paragraph("COMPENSATION DETAILS", sLabel))
        basic = round(monthly_ctc * 0.40, 2)
        hra   = round(monthly_ctc * 0.20, 2)
        sa    = round(monthly_ctc * 0.33, 2)
        pf    = round(monthly_ctc * 0.04, 2)
        gr    = round(monthly_ctc * 0.03, 2)
        def fmt(n): return f"₹{n:,.2f}"
        ctc_data = [
            ["Salary Component", "Monthly", "Annual"],
            ["Basic Salary",            fmt(basic),       fmt(basic*12)],
            ["House Rent Allowance",     fmt(hra),         fmt(hra*12)],
            ["Special Allowance",        fmt(sa),          fmt(sa*12)],
            ["PF — Employer (12%)",      fmt(pf),          fmt(pf*12)],
            ["Gratuity (4.81%)",         fmt(gr),          fmt(gr*12)],
            ["GROSS CTC",                fmt(monthly_ctc), fmt(monthly_ctc*12)],
        ]
        ctc_tbl = Table(ctc_data, colWidths=["50%", "25%", "25%"])
        ctc_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  LIGHT),
            ("BACKGROUND",   (0, -1), (-1, -1), DARK),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  GRAY),
            ("TEXTCOLOR",    (0, -1), (-1, -1), rl_colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("ALIGN",        (1, 0), (-1, -1),  "RIGHT"),
            ("ROWBACKGROUNDS",(0,1), (-1,-2),  [rl_colors.white, rl_colors.HexColor("#f9fafb")]),
            ("GRID",         (0, 0), (-1, -2),  0.3, rl_colors.HexColor("#e5e7eb")),
            ("TOPPADDING",   (0, 0), (-1, -1),  6),
            ("BOTTOMPADDING",(0, 0), (-1, -1),  6),
            ("LEFTPADDING",  (0, 0), (-1, -1),  8),
            ("RIGHTPADDING", (0, 0), (-1, -1),  8),
        ]))
        story.append(ctc_tbl)
        story.append(Spacer(1, 10))

    # ── Notes ──────────────────────────────────────────────────────────────
    if notes:
        note_tbl = Table([[Paragraph(f"<b>Note:</b> {notes}", ps("note", fontSize=9, textColor=rl_colors.HexColor("#1e40af")))]],
                         colWidths=["100%"])
        note_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,-1), rl_colors.HexColor("#eff6ff")),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING",  (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ]))
        story.append(note_tbl)
        story.append(Spacer(1, 10))

    # ── Terms & Conditions ─────────────────────────────────────────────────
    story.append(Paragraph("TERMS &amp; CONDITIONS", sLabel))
    tc_items = [
        "This offer is subject to satisfactory verification of your educational qualifications, credentials, and prior employment history.",
        f"You will serve a probationary period of <b>{probation} months</b> from the date of joining. Confirmation is subject to satisfactory performance.",
        f"Post-confirmation, either party may terminate employment by providing <b>{notice_days} days'</b> written notice or salary in lieu thereof. During probation, 7 days' notice applies.",
        "All compensation is subject to applicable statutory deductions (TDS, PF, ESI, Professional Tax) as per prevailing Indian law.",
        f"This offer is valid until <b>{valid_until}</b>. Non-acceptance by this date shall render this offer null and void.",
        "You shall maintain strict confidentiality of all proprietary and sensitive information of the Company during and after your employment.",
        "You will abide by the Company's HR policies, Code of Conduct, and all applicable rules as amended from time to time.",
        "A formal Appointment Letter will be issued upon joining. This offer letter does not constitute a contract of employment.",
    ]
    tc_data = [
        [Paragraph(f"{i+1}.&nbsp;&nbsp;{item}", ps(f"tc{i}", fontSize=9, leading=13, textColor=rl_colors.HexColor("#4b5563")))]
        for i, item in enumerate(tc_items)
    ]
    tc_tbl = Table(tc_data, colWidths=["100%"])
    tc_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tc_tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"We look forward to welcoming you to <b>{company}</b>. "
        "Please sign and return one copy of this letter to confirm your acceptance.",
        sNormal))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Warm regards,", sNormal))
    story.append(Spacer(1, 24))

    # ── Signature row ──────────────────────────────────────────────────────
    sig_data = [[
        [HRFlowable(width="80%", thickness=1, color=DARK),
         Paragraph("<b>Authorised Signatory</b>", ps("sig", fontSize=9)),
         Paragraph(company, ps("sigt", fontSize=8, textColor=GRAY)),
         Paragraph("Human Resources", ps("sigt2", fontSize=8, textColor=GRAY))],
        [Paragraph("I hereby accept this offer and agree to all terms stated above.", ps("accnote", fontSize=8, textColor=GRAY)),
         HRFlowable(width="80%", thickness=1, color=DARK),
         Paragraph(f"<b>{emp_name}</b>", ps("csig", fontSize=9)),
         Paragraph("Candidate Signature", ps("csigt", fontSize=8, textColor=GRAY)),
         Paragraph("Date: _______________", ps("cdate", fontSize=8, textColor=GRAY))],
    ]]
    sig_tbl = Table(sig_data, colWidths=["48%", "52%"])
    sig_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("TOPPADDING", (0,0), (-1,-1), 0)]))
    story.append(sig_tbl)

    # ── Footer rule ────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor("#e5e7eb")))
    foot_txt = company
    if co_address:
        foot_txt += f"  ·  {co_address}"
    story.append(Paragraph(f'<font size="8" color="#9ca3af">{foot_txt}&nbsp;&nbsp;&nbsp;Confidential — For addressee only</font>', sCenter))
    story.append(HRFlowable(width="100%", thickness=4, color=DARK, spaceBefore=6))

    doc.build(story)
    return buf.getvalue()


# Employee portal onboarding


# ---------------- ADMIN TOOLS (Org Chart + Audit Logs combined) ----------------


# old standalone routes kept for API


# ── /api/v1/ aliases ──────────────────────────────────────────────────────────
# Register every /api/<path> route also under /api/v1/<path>.  Existing mobile
# clients keep using /api/ with no changes; new integrations can start on v1.
# The view functions (and their decorators: @limiter, @api_required, etc.) are
# shared, so rate-limits and auth are identical on both prefixes.
def _register_api_v1_aliases():
    _seen = set()
    for _rule in list(app.url_map.iter_rules()):
        if not _rule.rule.startswith("/api/") or _rule.rule.startswith("/api/v"):
            continue
        _v1_rule = "/api/v1" + _rule.rule[4:]
        _vf      = app.view_functions.get(_rule.endpoint)
        if _vf is None:
            continue
        _ep_v1 = "v1_" + _rule.endpoint
        if _ep_v1 in _seen:
            continue
        _seen.add(_ep_v1)
        app.add_url_rule(
            _v1_rule,
            endpoint=_ep_v1,
            view_func=_vf,
            methods=_rule.methods,
        )

_register_api_v1_aliases()

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_master_db()
    init_db()
    load_default_shift()
    load_salary_rules()
    import os as _os
    _cert = _os.environ.get("SSL_CERT_PATH") or _os.path.join(_os.path.dirname(__file__), "cert.pem")
    _key  = _os.environ.get("SSL_KEY_PATH") or _os.path.join(_os.path.dirname(__file__), "key.pem")
    if _os.path.exists(_cert) and _os.path.exists(_key):
        print("🔒  SSL cert found — starting on https://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False,
                ssl_context=(_cert, _key))
    else:
        print("⚠   No cert.pem / key.pem — starting on http://0.0.0.0:5000")
        print("    Fingerprint / WebAuthn requires HTTPS. Run: python generate_cert.py")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
