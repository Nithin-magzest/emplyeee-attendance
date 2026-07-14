"""Shared utility helpers used across multiple blueprints."""
import os
import re
import datetime
import threading
import hashlib
import base64
from contextlib import contextmanager

_SAFE_IDENT_RE = re.compile(r'^[a-z][a-z0-9_]*$')
from flask import session, request, jsonify, render_template


def _safe_redirect(dest: str, fallback: str = "/admin") -> str:
    """Validate that a redirect target is a relative path (prevents open redirect)."""
    if dest and dest.startswith("/") and not dest.startswith("//"):
        return dest
    return fallback


def _safe_referrer_redirect(referrer: str, fallback: str) -> str:
    """Accept absolute Referer header only when it points back at this same app."""
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
from database import get_db_connection
from extensions import app_log

# ── PII encryption (Fernet) ───────────────────────────────────────────────────
from cryptography.fernet import Fernet, InvalidToken as _FernetInvalid
_ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
try:
    _fernet = Fernet(_ENCRYPTION_KEY.encode()) if _ENCRYPTION_KEY else None
except Exception:
    _fernet = None

def encrypt_pii(value: str) -> str:
    if not value or not _fernet:
        return value
    return _fernet.encrypt(value.encode()).decode()

def decrypt_pii(value: str) -> str:
    if not value or not _fernet:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except (_FernetInvalid, Exception):
        return value


# ── Token hashing ─────────────────────────────────────────────────────────────
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── DB context manager ────────────────────────────────────────────────────────
@contextmanager
def _db():
    conn   = get_db_connection()
    cursor = conn.cursor(buffered=True)
    try:
        yield cursor, conn
    finally:
        try:  cursor.close()
        except Exception as _e: app_log.debug("cursor.close() failed: %s", _e)
        try:  conn.close()
        except Exception as _e: app_log.debug("conn.close() failed: %s", _e)


# ── Audit logging ──────────────────────────────────────────────────────────────
def _audit(action, table=None, record_id=None, detail=None):
    try:
        actor      = session.get("admin_username") or session.get("employee_id") or "system"
        actor_type = "admin" if session.get("admin_logged_in") else "employee"
        ip         = request.remote_addr or ""
        db = get_db_connection(); cursor = db.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (actor, actor_type, action, target_table, target_id, detail, ip_address) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (actor, actor_type, action, table, str(record_id) if record_id is not None else None, detail, ip)
        )
        db.commit(); cursor.close(); db.close()
    except Exception:
        pass


# ── Notification helper ───────────────────────────────────────────────────────
def _create_notification(recipient_type, title, message, employee_id=None):
    try:
        db = get_db_connection(); cursor = db.cursor()
        cursor.execute(
            "INSERT INTO notifications (recipient_type, employee_id, title, message) VALUES (%s,%s,%s,%s)",
            (recipient_type, employee_id, title, message)
        )
        db.commit(); cursor.close(); db.close()
    except Exception:
        pass


# ── Malware scanning (ClamAV) ─────────────────────────────────────────────────
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


# ── File upload validation ─────────────────────────────────────────────────────
_ALLOWED_MIME_MAP = {
    "pdf":  {"application/pdf"},
    "jpg":  {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png":  {"image/png"},
    "doc":  {"application/msword"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "xls":  {"application/vnd.ms-excel"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}
_MAX_DOC_SIZE_MB = 10

def _validate_upload(file_storage, allowed_exts=None):
    if not file_storage or not file_storage.filename:
        return False, "No file selected."
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if allowed_exts and ext not in allowed_exts:
        return False, f"File type .{ext} not allowed. Allowed: {', '.join(sorted(allowed_exts))}"
    ct = (file_storage.content_type or "").split(";")[0].strip().lower()
    if ct and ext in _ALLOWED_MIME_MAP and ct not in _ALLOWED_MIME_MAP[ext]:
        return False, "File content does not match its extension."
    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if ext == "pdf" and not header.startswith(b"%PDF"):
        return False, "Invalid PDF file."
    if ext == "png" and not header.startswith(b"\x89PNG"):
        return False, "Invalid PNG file."
    if ext in ("jpg", "jpeg") and not header.startswith(b"\xff\xd8"):
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


_ALLOWED_IMG_EXT  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
_ALLOWED_IMG_MIME = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/gif"}
_MAX_PHOTO_SIZE_MB = 5
_IMG_MAGIC = {
    ".jpg":  (b"\xff\xd8",),
    ".jpeg": (b"\xff\xd8",),
    ".png":  (b"\x89PNG",),
    ".webp": (b"RIFF",),
    ".bmp":  (b"BM",),
}

def _validate_image_file(file):
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
            return False, "File content does not match its extension."
    file.stream.seek(0, 2)
    size_mb = file.stream.tell() / (1024 * 1024)
    file.stream.seek(0)
    if size_mb > _MAX_PHOTO_SIZE_MB:
        return False, f"Photo too large ({size_mb:.1f} MB). Maximum: {_MAX_PHOTO_SIZE_MB} MB."
    clean, scan_err = _scan_for_malware(file)
    if not clean:
        return False, scan_err
    return True, ""


# ── Company settings cache (60-second TTL) ────────────────────────────────────
_co_cache      = {"data": None, "expires": None}
_auth_cache    = {"data": None, "expires": None}
_settings_lock = threading.Lock()
_CO_CACHE_TTL  = 60

def _co_expired(cache):
    return cache["data"] is None or datetime.datetime.now() >= cache["expires"]

def invalidate_settings_cache():
    with _settings_lock:
        _co_cache["data"]   = None
        _auth_cache["data"] = None

def get_company_settings():
    with _settings_lock:
        if not _co_expired(_co_cache):
            return dict(_co_cache["data"])
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT company_name, company_tagline, company_logo, currency_symbol, timezone, "
            "setup_done, COALESCE(company_code,'') FROM company_settings LIMIT 1"
        )
        row = cursor.fetchone(); cursor.close(); db.close()
        if row:
            result = {
                "company_name": row[0], "company_tagline": row[1],
                "company_logo": row[2], "currency_symbol": row[3],
                "company_code": row[6], "timezone": row[4], "setup_done": bool(row[5]),
            }
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
    "fingerprint_enabled": False, "qr_enabled": True, "face_enabled": True,
    "location_enabled": True, "employee_password_auth": True,
}

def get_auth_config():
    with _settings_lock:
        if not _co_expired(_auth_cache):
            return dict(_auth_cache["data"])
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute("""
            SELECT COALESCE(fingerprint_enabled,0), COALESCE(qr_enabled,1),
                   COALESCE(face_enabled,1), COALESCE(location_enabled,1),
                   COALESCE(employee_password_auth,1)
            FROM company_settings LIMIT 1
        """)
        row = cursor.fetchone(); cursor.close(); db.close()
        if row:
            result = {
                "fingerprint_enabled": bool(row[0]), "qr_enabled": bool(row[1]),
                "face_enabled": bool(row[2]), "location_enabled": bool(row[3]),
                "employee_password_auth": bool(row[4]),
            }
            with _settings_lock:
                _auth_cache["data"]    = result
                _auth_cache["expires"] = datetime.datetime.now() + datetime.timedelta(seconds=_CO_CACHE_TTL)
            return dict(result)
    except Exception:
        pass
    return dict(_AUTH_CONFIG_DEFAULTS)

def get_fingerprint_enabled():
    return get_auth_config()["fingerprint_enabled"]

def _read_global_features():
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
                "session_timeout": r[11], "late_deduction_pct": float(r[12]),
                "half_day_deduction_pct": float(r[13]), "grace_minutes": int(r[14]),
                "holiday_pay": r[15], "leave_pay": r[16],
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
                "session_timeout": r[11], "late_deduction_pct": float(r[12]),
                "half_day_deduction_pct": float(r[13]), "grace_minutes": int(r[14]),
                "holiday_pay": r[15], "leave_pay": r[16],
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
})

def _upsert_co_feature(company_id, field, value):
    if not company_id:
        return
    # Double-gate: frozenset membership + regex ensures only safe identifier chars
    if field not in _VALID_CFS_COLS or not _SAFE_IDENT_RE.match(field):
        app_log.error("_upsert_co_feature: rejected column %r", field)
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
    if not company_id or not fields_dict:
        return
    # Validate every key against frozenset AND regex before any interpolation
    bad = [k for k in fields_dict if k not in _VALID_CFS_COLS or not _SAFE_IDENT_RE.match(k)]
    if bad:
        app_log.error("_upsert_co_features: rejected columns %s", bad)
        return
    try:
        safe_fields  = {k: v for k, v in fields_dict.items() if k in _VALID_CFS_COLS}
        cols         = ", ".join(safe_fields.keys())
        vals         = list(safe_fields.values())
        placeholders = ", ".join(["%s"] * len(vals))
        updates      = ", ".join(f"{k}=EXCLUDED.{k}" for k in safe_fields.keys())
        db = get_db_connection(); cur = db.cursor(buffered=True)
        cur.execute(f"""
            INSERT INTO company_feature_settings (company_id, {cols})
            VALUES (%s, {placeholders})
            ON CONFLICT (company_id) DO UPDATE SET {updates}
        """, [company_id] + vals)
        db.commit(); cur.close(); db.close()
    except Exception:
        pass


# ── Error page renderer ───────────────────────────────────────────────────────
def _error_page(code, icon, title, subtitle, hint):
    return render_template(
        "error.html", code=code, icon=icon, title=title, subtitle=subtitle, hint=hint
    ), code
