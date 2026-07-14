"""Authentication decorators, login lockout, and password hashing."""
import datetime
import hashlib
import bcrypt as _bcrypt
from functools import wraps
from contextlib import contextmanager
from flask import session, request, jsonify, redirect, url_for, g as _flask_g
from werkzeug.security import check_password_hash as _wz_check_pw
from database import get_db_connection
from extensions import app_log, log_security_event
from utils.session_risk import is_session_compromised, evaluate_session_risk
from utils.async_writer import enqueue_write

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
# 5 matches what app.py's now-removed duplicate decorators actually enforced
# in production — adopted as canonical here rather than the 10 this module
# used before consolidation, to avoid silently loosening lockout as a side
# effect of removing the duplicate.
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
    """Called from the request-handling thread on every failed login — must
    stay fast unconditionally, including under a brute-force flood, which is
    exactly when this gets called the most. The actual DB write (measured:
    3s median / 5.8s max latency under 60 concurrent attempts against one
    identifier, from row-lock + connection-pool contention) is handed off to
    the single background writer thread instead of run here. See
    utils/async_writer.py for why this is an in-process queue, not Celery.

    Trade-off, stated plainly: lockout becomes eventually consistent rather
    than exact-on-the-5th-request — the counter increment and lockout check
    happen slightly after the response for attempt N has already been sent.
    Bounded by queue throughput (a single writer processing sequentially,
    typically sub-millisecond per write once decoupled from contention), not
    unbounded. Acceptable for a defense-in-depth control; would not be
    acceptable for the password check itself, which stays fully synchronous.
    """
    log_security_event(
        "auth.failure", "Failed login attempt", level="WARNING",
        identifier=identifier, attempt_type=attempt_type,
    )
    enqueue_write(_record_login_failure_db, identifier, attempt_type)


def _record_login_failure_db(identifier: str, attempt_type: str = "admin"):
    """The actual DB write — runs only on the background writer thread,
    never on a request thread. Do not call this directly from a route."""
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
                log_security_event(
                    "auth.lockout", "Account locked after repeated failed logins", level="ERROR",
                    identifier=identifier, attempt_type=attempt_type,
                    failed_count=row[0], locked_until=lockout_until.isoformat(),
                )
    except Exception:
        pass

def _clear_login_failures(identifier: str, attempt_type: str = "admin"):
    """Enqueued onto the SAME writer queue as _record_login_failure_db, not
    written synchronously — critical for correctness, not just speed. If
    this ran immediately while a burst of recent failures was still queued
    (e.g. a user's 5th failed attempt followed instantly by a correct 6th),
    a synchronous clear could run BEFORE those queued failure-writes land,
    and the failures would then land AFTER the clear — undoing it, leaving
    a phantom failed_count despite the successful login. Routing both
    through one FIFO queue with a single consumer thread guarantees this
    clear always executes after every failure recorded before it, with no
    ordering race possible.
    """
    enqueue_write(_clear_login_failures_db, identifier, attempt_type)


def _clear_login_failures_db(identifier: str, attempt_type: str = "admin"):
    try:
        with _db() as (cur, conn):
            cur.execute(
                "DELETE FROM login_attempts WHERE identifier=%s AND attempt_type=%s",
                (identifier, attempt_type)
            )
            conn.commit()
    except Exception:
        pass


# ── Session kill-switch enforcement ───────────────────────────────────────────
def _reject_if_compromised(login_endpoint: str):
    """The actual kill switch. Checked on every authenticated request, not
    just at login — a session flagged 'compromised' mid-lifetime (see
    utils/session_risk.py) is dead on its very next request regardless of
    whether the browser tab that owns it ever sees the SSE push telling it
    to log itself out. Returns a redirect Response if the session should be
    killed, or None if it's fine to proceed."""
    sid = session.get("_sid")
    if sid and is_session_compromised(sid):
        log_security_event("session.rejected", "Rejected a request from a compromised session",
                            level="WARNING", identifier=session.get("admin_username")
                            or session.get("employee_id"))
        session.clear()
        return redirect(url_for(login_endpoint, locked="1"))
    return None


# ── Web session guards ────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("admin_logged_in") and session.get("employee_id"):
            session.pop("employee_id", None)
            session.pop("employee_name", None)
            session.pop("employee_role", None)
        if not session.get("admin_logged_in"):
            # employee_id present but no admin session = an authenticated
            # employee reaching for an admin-only route, not just an
            # anonymous visitor — that's the signal worth a WARNING; a
            # plain anonymous hit is routine enough to log at INFO only.
            _level = "WARNING" if session.get("employee_id") else "INFO"
            log_security_event("access.denied", "Unauthenticated request to admin-only route",
                                level=_level, required="admin")
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
        _killed = _reject_if_compromised("auth.admin_login")
        if _killed:
            return _killed
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
            log_security_event("access.denied", "Unauthenticated request to employee-only route",
                                level="INFO", required="employee")
            return redirect("/employee_login")
        _killed = _reject_if_compromised("auth.employee_login")
        if _killed:
            return _killed
        # Prevent bypassing forced password change by navigating directly to portal
        from flask import request as _req
        if session.get("_fpc") and _req.endpoint != "auth.force_change_pin":
            return redirect("/force_change_pin")
        return f(*args, **kwargs)
    return wrapper

def manager_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            log_security_event("access.denied", "Unauthenticated request to manager/admin route",
                                level="INFO", required="manager_or_admin")
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
            # A real, logged-in account reaching for a resource its own role
            # doesn't grant — a BOLA/privilege-escalation signal, not
            # routine traffic, so this is ERROR (alert-worthy) rather than
            # the WARNING used for a bare unauthenticated hit above.
            log_security_event("access.denied", "Insufficient role for manager/admin route",
                                level="ERROR", required="manager_or_admin",
                                actual_role=session.get("admin_role", "admin"),
                                identifier=session.get("admin_username"))
            # Feeds the session kill switch: weight 25, not the full
            # threshold, in one shot — a single blocked attempt could be a
            # stale UI/bookmark on an honestly lower-privileged account.
            # Repeated attempts against the same session is the real signal,
            # and that's what accumulates toward the kill threshold.
            sid = session.get("_sid")
            if sid:
                evaluate_session_risk(
                    sid, session.get("admin_username") or "unknown", "admin",
                    weight=25, event_type="access.denied",
                    reason="Repeated insufficient-role access attempts",
                )
            return jsonify({"ok": False, "msg": "Insufficient permissions."}), 403
        return f(*args, **kwargs)
    return wrapper


# ── API Bearer token guards ───────────────────────────────────────────────────
def api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            log_security_event("access.denied", "API request missing Bearer token",
                                level="INFO", required="admin_api")
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        # Never log the token or its hash — it's the literal credential /
        # DB lookup key, and logging it would hand anyone with log access
        # something they could use to fingerprint or replay-correlate it.
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
            log_security_event("access.denied", "API request with invalid or expired admin token",
                                level="WARNING", required="admin_api")
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        _flask_g.api_user = row[0]
        return f(*args, **kwargs)
    return wrapper

def employee_api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            log_security_event("access.denied", "API request missing Bearer token",
                                level="INFO", required="employee_api")
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
            log_security_event("access.denied", "API request with invalid or expired employee token",
                                level="WARNING", required="employee_api")
            return jsonify({"ok": False, "msg": "Invalid or expired token"}), 401
        _flask_g.api_emp_id = row[0]
        return f(*args, **kwargs)
    return wrapper
