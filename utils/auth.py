"""Authentication decorators, login lockout, and password hashing."""
import datetime
import hashlib
import bcrypt as _bcrypt
from functools import wraps
from contextlib import contextmanager
from flask import session, request, jsonify, redirect, url_for, g as _flask_g
from werkzeug.security import check_password_hash as _wz_check_pw
from database import get_db_connection
from extensions import app_log

# ── Password hashing (bcrypt with legacy pbkdf2 fallback) ────────────────────
def generate_password_hash(pw: str, **_) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt(rounds=12)).decode()

def check_password_hash(pw_hash: str, pw: str) -> bool:
    if not pw_hash:
        return False
    if pw_hash.startswith("$2b$") or pw_hash.startswith("$2a$"):
        try:
            return _bcrypt.checkpw(pw.encode(), pw_hash.encode())
        except Exception:
            return False
    return _wz_check_pw(pw_hash, pw)


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


# ── Account lockout ───────────────────────────────────────────────────────────
_LOGIN_MAX_ATTEMPTS    = 5
_LOGIN_LOCKOUT_MINUTES = 15

def _check_login_lockout(identifier: str, attempt_type: str = "admin"):
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
    try:
        with _db() as (cur, conn):
            cur.execute(
                "DELETE FROM login_attempts WHERE identifier=%s AND attempt_type=%s",
                (identifier, attempt_type)
            )
            conn.commit()
    except Exception:
        pass


# ── Web session guards ────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
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
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.",
                                "redirect": url_for("auth.admin_login")}), 401
            return redirect(url_for("auth.admin_login"))
        return f(*args, **kwargs)
    return wrapper

def employee_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.pop("employee_id", None)
            session.pop("employee_name", None)
            session.pop("employee_role", None)
            return redirect("/admin")
        if not session.get("employee_id"):
            return redirect("/employee_login")
        # Prevent bypassing forced password change by navigating directly to portal
        from flask import request as _req
        if session.get("_fpc") and _req.endpoint not in ("auth.force_change_pin", "force_change_pin"):
            return redirect("/force_change_pin")
        return f(*args, **kwargs)
    return wrapper

def manager_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            is_ajax = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Accept", "").startswith("application/json")
                or request.is_json
            )
            if is_ajax:
                return jsonify({"ok": False, "msg": "Session expired. Please log in again.",
                                "redirect": url_for("auth.admin_login")}), 401
            return redirect(url_for("auth.admin_login"))
        if session.get("admin_role", "admin") not in ("admin", "manager"):
            return jsonify({"ok": False, "msg": "Insufficient permissions."}), 403
        return f(*args, **kwargs)
    return wrapper


# ── API Bearer token guards ───────────────────────────────────────────────────
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
        _flask_g.api_user = row[0]
        return f(*args, **kwargs)
    return wrapper

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
        _flask_g.api_emp_id = row[0]
        return f(*args, **kwargs)
    return wrapper
