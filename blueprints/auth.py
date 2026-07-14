"""Auth blueprint — login, logout, password reset, WebAuthn."""
import os
import re
import time
import base64
import secrets
import hashlib
import datetime
from urllib.parse import urlparse

from flask import (Blueprint, session, request, redirect, render_template,
                   flash, url_for, jsonify, current_app)

from extensions import limiter, app_log, _allowed_origins
from database import get_db_connection
from utils.auth import (admin_required, employee_required,
                        generate_password_hash, check_password_hash,
                        _hash_token, _db,
                        _check_login_lockout, _record_login_failure,
                        _clear_login_failures)
from utils.helpers import (get_company_settings, invalidate_settings_cache,
                           get_auth_config, get_fingerprint_enabled)
from utils.email_utils import get_email_config, send_email_async

# WebAuthn optional dependency
try:
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
except Exception:
    webauthn = None
    _webauthn_available = False

auth_bp = Blueprint("auth", __name__)

# ── WebAuthn helpers ──────────────────────────────────────────────────────────
_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
_WA_FP_VERIFY_WINDOW_SEC = 120


def _wa_rp_id():
    host = request.host.split(":")[0]
    if host in ("127.0.0.1", "::1", "localhost"):
        return host
    if _allowed_origins != "*" and _allowed_origins:
        canonical = urlparse(_allowed_origins[0]).hostname
        if canonical:
            return canonical
    return host


def _wa_check_rp_id(rp_id):
    if rp_id in ("127.0.0.1", "::1", "localhost"):
        return None
    if _IP_RE.match(rp_id):
        return (
            f"WebAuthn does not support IP addresses as RP IDs (got '{rp_id}'). "
            "Access via 'localhost' or configure a hostname."
        )
    return None


def _wa_origins():
    host = request.host
    scheme = request.scheme
    origins = {f"{scheme}://{host}"}
    bare = host.split(":")[0]
    if bare == "127.0.0.1":
        origins.add(f"{scheme}://{host.replace('127.0.0.1', 'localhost')}")
    elif bare == "localhost":
        origins.add(f"{scheme}://{host.replace('localhost', '127.0.0.1')}")
    return list(origins)


def _wa_b64url_decode(s):
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _wa_b64url_encode(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _wa_fingerprint_recently_verified(emp_id):
    emp_id = (emp_id or "").strip().upper()
    verified_emp = session.pop("wa_fp_verified_emp_id", None)
    verified_at  = session.pop("wa_fp_verified_at", 0)
    return bool(emp_id) and verified_emp == emp_id and (time.time() - verified_at) <= _WA_FP_VERIFY_WINDOW_SEC

@auth_bp.route("/setup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
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
        elif len(admin_pass) < 8:
            error = "Password must be at least 8 characters."
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
            invalidate_settings_cache()
            return redirect("/admin_login?setup=done")

    return render_template("setup.html", error=error)



@auth_bp.route("/admin_login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
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
        # Check lockout before attempting any credential check
        locked, until = _check_login_lockout(identifier)
        if locked:
            return render_template("admin_login.html",
                error=f"Account locked until {until} due to too many failed attempts.")
        # Try admin credentials first
        with _db() as (cursor, db):
            cursor.execute("SELECT password, COALESCE(role,'admin') FROM admin_users WHERE username=%s", (identifier,))
            admin_row = cursor.fetchone()
        if admin_row and check_password_hash(admin_row[0], password):
            _clear_login_failures(identifier)
            # Upgrade legacy hash to bcrypt on first successful login
            if admin_row[0] and not admin_row[0].startswith("$2"):
                with _db() as (_uc, _ud):
                    _uc.execute("UPDATE admin_users SET password=%s WHERE username=%s",
                                (generate_password_hash(password), identifier))
                    _ud.commit()
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = identifier
            session["admin_role"] = admin_row[1]
            session["_session_created"] = time.time()
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
            if not stored_pwd or not check_password_hash(stored_pwd, password):
                _record_login_failure(identifier)
                return render_template("admin_login.html", error="Invalid credentials. Check your ID and password.")
            _clear_login_failures(identifier)
            # Upgrade legacy hash to bcrypt on first successful login
            if stored_pwd and not stored_pwd.startswith("$2"):
                with _db() as (_uc, _ud):
                    _uc.execute("UPDATE employees SET password=%s WHERE employee_id=%s",
                                (generate_password_hash(password), emp_row[0]))
                    _ud.commit()
            session.clear()
            session["employee_id"]     = emp_row[0]
            session["employee_name"]   = emp_row[1]
            session["employee_role"]   = emp_row[2] or ""
            session["_session_created"] = time.time()
            session["_fpc"]            = bool(emp_row[4])  # force_pin_change flag in session
            session.permanent = True
            if emp_row[4]:
                return redirect("/force_change_pin")
            return redirect("/employee_portal")
        _record_login_failure(identifier)
        return render_template("admin_login.html", error="Invalid credentials. Check your ID and password.")
    return render_template("admin_login.html")

# ---------------- LOGOUT ----------------

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

# ---------------- ADMIN DASHBOARD ----------------

@auth_bp.route("/change_admin_password", methods=["POST"])
@admin_required
def change_admin_password():
    current_pw   = request.form.get("current_password", "")
    new_pw       = request.form.get("new_password", "")
    confirm_pw   = request.form.get("confirm_password", "")
    # Use the logged-in admin's username, not a hardcoded 'admin' string.
    # A hardcoded value lets any admin account change the 'admin' password
    # if they know its current value — a cross-account privilege escalation.
    logged_in_as = session.get("admin_username", "admin")
    if not new_pw or new_pw != confirm_pw:
        return redirect("/admin?pwd_error=mismatch")
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT password FROM admin_users WHERE username=%s", (logged_in_as,))
    row = cursor.fetchone()
    if not row or not check_password_hash(row[0], current_pw):
        cursor.close(); db.close()
        return redirect("/admin?pwd_error=wrong")
    cursor.execute(
        "UPDATE admin_users SET password=%s WHERE username=%s",
        (generate_password_hash(new_pw), logged_in_as)
    )
    db.commit(); cursor.close(); db.close()
    return redirect("/admin?pwd_ok=1")



@auth_bp.route("/admin_set_recovery_email", methods=["POST"])
@admin_required
def admin_set_recovery_email():
    email    = request.form.get("recovery_email", "").strip()
    username = session.get("admin_username", "admin")
    if email:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("UPDATE admin_users SET email=%s WHERE username=%s", (email, username))
        db.commit(); cursor.close(); db.close()
    return redirect("/admin?email_ok=1#password-management")




@auth_bp.route("/admin_forgot_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_forgot_password():
    if request.method == "GET":
        return render_template("admin_forgot_password.html",
                               sent=False, error=None)
    admin_email = request.form.get("email", "").strip().lower()
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id FROM admin_users WHERE LOWER(email)=%s", (admin_email,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        # Return the same message whether the email exists or not (no account enumeration)
        return render_template("admin_forgot_password.html", sent=True, error=None)
    token       = secrets.token_hex(32)
    token_hash  = hashlib.sha256(token.encode()).hexdigest()
    expiry      = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    admin_id    = row[0]
    cursor.execute(
        "UPDATE admin_users SET reset_token=%s, reset_token_expiry=%s WHERE id=%s",
        (token_hash, expiry, admin_id)
    )
    db.commit(); cursor.close(); db.close()
    cfg = get_email_config()
    if not cfg:
        return render_template("admin_forgot_password.html", sent=False,
                               error="Email service not configured. Go to Admin → Email Settings first.")
    reset_url = f"{_safe_app_url()}/admin_reset_password/{token}"
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
    except Exception:
        app_log.error("Failed to send admin password reset email", exc_info=True)
        return render_template("admin_forgot_password.html", sent=False,
                               error="Failed to send email. Please check your email settings.")
    return render_template("admin_forgot_password.html", sent=True, error=None)



@auth_bp.route("/admin_reset_password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_reset_password(token):
    db     = get_db_connection()
    cursor = db.cursor(buffered=True)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    cursor.execute(
        "SELECT id FROM admin_users WHERE reset_token=%s AND reset_token_expiry > %s",
        (token_hash, datetime.datetime.utcnow())
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
    if len(new_pw) < 8:
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=True, done=False,
                               token=token, error="Password must be at least 8 characters.")
    if new_pw != confirm_pw:
        cursor.close(); db.close()
        return render_template("admin_reset_password.html", valid=True, done=False,
                               token=token, error="Passwords do not match.")
    admin_id = row[0]
    cursor.execute(
        "UPDATE admin_users SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE id=%s",
        (generate_password_hash(new_pw), admin_id)
    )
    db.commit(); cursor.close(); db.close()
    return render_template("admin_reset_password.html", valid=True, done=True, token=token, error=None)



@auth_bp.route("/employee_forgot_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def employee_forgot_password():
    if request.method == "GET":
        return render_template("employee_forgot_password.html", sent=False, error=None)
    emp_id = request.form.get("employee_id", "").strip()
    if not emp_id:
        return render_template("employee_forgot_password.html", sent=False, error="Please enter your Employee ID.")
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, email, name FROM employees WHERE employee_id=%s", (emp_id,))
    row = cursor.fetchone()
    if not row or not row[1]:
        cursor.close(); db.close()
        # Generic message to avoid account enumeration; also covers "no email on file"
        return render_template("employee_forgot_password.html", sent=True, error=None)
    db_email = row[1]
    emp_name = _html.escape(row[2] or emp_id)
    token       = secrets.token_hex(32)
    token_hash  = hashlib.sha256(token.encode()).hexdigest()
    expiry      = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    cursor.execute("UPDATE employees SET reset_token=%s, reset_token_expiry=%s WHERE employee_id=%s",
                   (token_hash, expiry, emp_id))
    db.commit(); cursor.close(); db.close()
    cfg = get_email_config()
    if not cfg:
        return render_template("employee_forgot_password.html", sent=False,
                               error="Email service not configured. Please contact HR.")
    reset_url = f"{_safe_app_url()}/employee_reset_password/{token}"
    html_body = f"""
<div style="font-family:Segoe UI,sans-serif;max-width:520px;margin:auto;background:#f8fafc;border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:#1e3a8a;padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">🔐 Password Reset</div>
    <div style="font-size:13px;opacity:0.75;margin-top:4px;">Employee Portal</div>
  </div>
  <div style="padding:28px;">
    <p style="font-size:15px;color:#1e293b;margin-bottom:20px;">Hi <strong>{emp_name}</strong>, you requested a password reset for Employee ID <strong>{emp_id}</strong>.</p>
    <a href="{reset_url}" style="display:block;text-align:center;padding:14px 28px;background:#1e3a8a;color:white;border-radius:10px;text-decoration:none;font-size:15px;font-weight:700;margin-bottom:20px;">
      Reset My Password
    </a>
    <p style="font-size:13px;color:#64748b;">This link expires in <strong>1 hour</strong>. If you did not request this, please ignore this email.</p>
    <p style="font-size:12px;color:#94a3b8;margin-top:12px;">Or copy this link: {reset_url}</p>
  </div>
</div>"""
    send_email_async(db_email, "Password Reset — Employee Portal", html_body, cfg)
    return render_template("employee_forgot_password.html", sent=True, error=None)



@auth_bp.route("/employee_reset_password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def employee_reset_password(token):
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    cursor.execute("SELECT employee_id FROM employees WHERE reset_token=%s AND reset_token_expiry > %s",
                   (token_hash, datetime.datetime.utcnow()))
    row = cursor.fetchone()
    if not row:
        cursor.close(); db.close()
        return render_template("employee_reset_password.html", valid=False, done=False, token=token)
    if request.method == "GET":
        cursor.close(); db.close()
        return render_template("employee_reset_password.html", valid=True, done=False, token=token, error=None)
    new_pw     = request.form.get("new_password", "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()
    if len(new_pw) < 8:
        cursor.close(); db.close()
        return render_template("employee_reset_password.html", valid=True, done=False,
                               token=token, error="Password must be at least 8 characters.")
    if new_pw != confirm_pw:
        cursor.close(); db.close()
        return render_template("employee_reset_password.html", valid=True, done=False,
                               token=token, error="Passwords do not match.")
    emp_id = row[0]
    cursor.execute("UPDATE employees SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE employee_id=%s",
                   (generate_password_hash(new_pw), emp_id))
    db.commit(); cursor.close(); db.close()
    _audit("employee_password_reset", "employees", emp_id, "Password reset via email link")
    return render_template("employee_reset_password.html", valid=True, done=True, token=token, error=None)



@auth_bp.route("/employee_login", methods=["GET", "POST"])
def employee_login():
    return redirect("/admin_login")



@auth_bp.route("/employee_logout", methods=["GET", "POST"])
def employee_logout():
    session.clear()
    return redirect("/employee_login")



@auth_bp.route("/change_password", methods=["POST"])
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
    if len(new_pwd) < 8:
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



@auth_bp.route("/force_change_pin", methods=["GET", "POST"])
@employee_required
def force_change_pin():
    emp_id = session["employee_id"]
    error  = None
    if request.method == "POST":
        new_pwd = request.form.get("new_password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        if len(new_pwd) < 8:
            error = "Password must be at least 8 characters."
        elif new_pwd != confirm:
            error = "Passwords do not match."
        elif new_pwd in ("1234", "12345678", "password", "admin123"):
            error = "That password is too common. Please choose a stronger one."
        else:
            db = get_db_connection()
            cursor = db.cursor(buffered=True)
            cursor.execute(
                "UPDATE employees SET password=%s, force_pin_change=0 WHERE employee_id=%s",
                (generate_password_hash(new_pwd), emp_id)
            )
            db.commit(); cursor.close(); db.close()
            session.pop("_fpc", None)  # clear forced-change flag so portal is accessible
            return redirect("/employee_portal")
    return render_template("force_change_pin.html", error=error,
                           emp_name=session.get("employee_name", ""))



@auth_bp.route("/webauthn/status", methods=["GET"])
def webauthn_status():
    """Diagnostic endpoint — shows WebAuthn config without exposing sensitive data."""
    return jsonify({
        "webauthn_available": _webauthn_available,
        "rp_id":              _wa_rp_id() if _webauthn_available else None,
        "expected_origins":   _wa_origins() if _webauthn_available else [],
        "challenge_in_session": bool(session.get("wa_reg_challenge")),
        "request_host":       request.host,
        "request_scheme":     request.scheme,
    })



@auth_bp.route("/webauthn/registration-options", methods=["GET"])
def webauthn_registration_options():
    """Server-generated WebAuthn registration options with challenge stored in session."""
    if not _webauthn_available:
        return jsonify({"ok": False, "msg": "Fingerprint enrollment is not available on this server."}), 503
    try:
        emp_id   = (request.args.get("emp_id") or session.get("employee_id") or "employee").strip().upper()
        emp_name = (request.args.get("name") or emp_id).strip()
        rp_id    = _wa_rp_id()
        rp_err   = _wa_check_rp_id(rp_id)
        if rp_err:
            return jsonify({"ok": False, "error": rp_err}), 422
        _reg_algs = [COSEAlgorithmIdentifier.ECDSA_SHA_256, COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256]
        options = webauthn.generate_registration_options(
            rp_id=rp_id,
            rp_name="Employee Attendance",
            user_id=emp_id.encode(),
            user_name=emp_id,
            user_display_name=emp_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                user_verification=UserVerificationRequirement.REQUIRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
            supported_pub_key_algs=_reg_algs,
            attestation=AttestationConveyancePreference.NONE,
        )
        session["wa_reg_challenge"]  = _wa_b64url_encode(options.challenge)
        session["wa_reg_emp_id"]     = emp_id
        session["wa_reg_alg_ids"]    = [a.value for a in _reg_algs]
        return webauthn.options_to_json(options), 200, {"Content-Type": "application/json"}
    except Exception as exc:
        app_log.error("WebAuthn registration-options failed: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500



@auth_bp.route("/webauthn/authentication-options", methods=["GET"])
def webauthn_authentication_options():
    """Server-generated WebAuthn authentication options with challenge stored in session."""
    if not _webauthn_available:
        return jsonify({"ok": False, "msg": "Fingerprint verification is not available on this server."}), 503
    try:
        emp_id = (request.args.get("emp_id") or "").strip().upper()
        rp_id  = _wa_rp_id()
        rp_err = _wa_check_rp_id(rp_id)
        if rp_err:
            return jsonify({"ok": False, "error": rp_err}), 422

        allow_creds = []
        if emp_id:
            try:
                db = get_db_connection(); cur = db.cursor(buffered=True)
                cur.execute("SELECT fingerprint_credential_id FROM employees WHERE employee_id=%s", (emp_id,))
                row = cur.fetchone(); cur.close(); db.close()
                if row and row[0]:
                    allow_creds = [PublicKeyCredentialDescriptor(
                        id=_wa_b64url_decode(row[0]), transports=[AuthenticatorTransport.INTERNAL]
                    )]
            except Exception as db_exc:
                app_log.warning("WebAuthn auth-options: DB lookup failed for emp=%s: %s", emp_id, db_exc)

        options = webauthn.generate_authentication_options(
            rp_id=rp_id, allow_credentials=allow_creds, user_verification=UserVerificationRequirement.REQUIRED,
        )
        session["wa_auth_challenge"] = _wa_b64url_encode(options.challenge)
        session["wa_auth_emp_id"]    = emp_id
        return webauthn.options_to_json(options), 200, {"Content-Type": "application/json"}
    except Exception as exc:
        app_log.error("WebAuthn authentication-options failed: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500



@auth_bp.route("/api/employee/webauthn-verify-challenge", methods=["POST"])
def webauthn_verify_challenge():
    """
    Real server-side WebAuthn assertion verification: checks the ECDSA/RSA
    signature in the assertion against the employee's stored public key (not
    just the clientDataJSON fields, which are trivially forgeable on their
    own). On success, sets a short-lived, one-time, employee-bound session
    flag that /attendance and /api/employee/qr-face-checkin consume to allow
    the actual check-in — this stops a verified fingerprint for employee A
    from being reused to check in as employee B.
    """
    if not _webauthn_available:
        return jsonify({"ok": False, "msg": "Fingerprint verification is not available on this server."}), 503
    data          = request.get_json(force=True, silent=True) or {}
    emp_id        = (data.get("emp_id") or session.get("wa_auth_emp_id") or "").strip().upper()
    credential    = data.get("credential")
    challenge_b64 = session.get("wa_auth_challenge")

    if not credential or not challenge_b64:
        return jsonify({"ok": False, "msg": "Missing credential or challenge"}), 400

    try:
        db = get_db_connection(); cur = db.cursor(buffered=True)

        if emp_id:
            # QR + Fingerprint mode: employee already identified by QR scan
            cur.execute(
                "SELECT employee_id, name, fingerprint_public_key, fingerprint_sign_count FROM employees WHERE employee_id=%s",
                (emp_id,)
            )
        else:
            # Passkey mode: employee is identified by the credential ID inside the assertion.
            # credential["id"] is the base64url credential ID the browser signed with.
            cred_id = (credential.get("id") or "") if isinstance(credential, dict) else ""
            if not cred_id:
                cur.close(); db.close()
                return jsonify({"ok": False, "msg": "Missing credential ID"}), 400
            cur.execute(
                "SELECT employee_id, name, fingerprint_public_key, fingerprint_sign_count FROM employees WHERE fingerprint_credential_id=%s",
                (cred_id,)
            )

        row = cur.fetchone()
        if not row or not row[2]:
            cur.close(); db.close()
            return jsonify({"ok": False, "msg": "No passkey enrolled. Please enrol from the employee portal."}), 401

        emp_id             = row[0]
        emp_name           = row[1] or emp_id
        stored_pubkey      = base64.b64decode(row[2])
        stored_sign_count  = int(row[3] or 0)

        verified = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=_wa_b64url_decode(challenge_b64),
            expected_rp_id=_wa_rp_id(),
            expected_origin=_wa_origins(),
            credential_public_key=stored_pubkey,
            # Per W3C WebAuthn §7.2 step 21: pass the stored count so py_webauthn
            # can reject a cloned credential (new ≤ stored when stored > 0).
            # Authenticators that never increment (Windows Hello, Touch ID) always
            # return 0, so stored stays 0 and the check is skipped automatically.
            credential_current_sign_count=stored_sign_count,
        )
    except Exception as e:
        try: cur.close(); db.close()
        except Exception: pass
        app_log.warning("WebAuthn authentication verification failed for emp_id=%s: %s", emp_id or "(passkey mode)", e, exc_info=True)
        return jsonify({"ok": False, "msg": f"Verification failed: {e}"}), 401

    session.pop("wa_auth_challenge", None)
    session.pop("wa_auth_emp_id", None)

    # Persisting the new sign count is best-effort bookkeeping (anti-clone
    # detection) — a failure here doesn't invalidate a verification that
    # already succeeded above, so it's swallowed rather than failing the
    # whole request. Reuses the connection from the SELECT above instead of
    # opening a second one.
    try:
        cur.execute(
            "UPDATE employees SET fingerprint_sign_count=%s WHERE employee_id=%s",
            (verified.new_sign_count, emp_id)
        )
        db.commit()
    except Exception:
        pass
    finally:
        cur.close(); db.close()

    session["wa_fp_verified_emp_id"] = emp_id
    session["wa_fp_verified_at"]     = time.time()
    return jsonify({"ok": True, "emp_id": emp_id, "name": emp_name})



@auth_bp.route("/api/employee/webauthn-register", methods=["POST"])
@limiter.limit("10 per minute")
def webauthn_register():
    """Save a WebAuthn credential after successful enrollment. Requires active employee session."""
    # Use session employee_id; fall back to wa_reg_emp_id stored when options were generated.
    # Both values live in the same signed session cookie, so this is equivalent security.
    emp_id = session.get("employee_id") or session.get("wa_reg_emp_id")
    if not emp_id:
        return jsonify({"ok": False, "msg": "Session expired — please log in again"}), 401
    data       = request.get_json(force=True, silent=True) or {}
    credential = data.get("credential")
    challenge_b64 = session.get("wa_reg_challenge")
    if not challenge_b64:
        return jsonify({"ok": False, "msg": "Enrollment session expired — please start again"}), 401
    try:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        ok, err = _wa_verify_and_store_registration(emp_id, credential, challenge_b64, cursor, db)
        cursor.close(); db.close()
    except Exception:
        app_log.error("WebAuthn registration endpoint failed", exc_info=True)
        return jsonify({"ok": False, "msg": "WebAuthn registration failed. Please try again."}), 500
    session.pop("wa_reg_challenge", None)
    session.pop("wa_reg_emp_id", None)
    session.pop("wa_reg_alg_ids", None)
    if not ok:
        return jsonify({"ok": False, "msg": err}), 401
    return jsonify({"ok": True})



@auth_bp.route("/api/employee/webauthn-register-kiosk", methods=["POST"])
@limiter.limit("5 per minute")
def webauthn_register_kiosk():
    """Enrol a passkey from the attendance kiosk. No employee session required."""
    if not _webauthn_available:
        return jsonify({"ok": False, "msg": "Fingerprint enrollment is not available on this server."}), 503
    data          = request.get_json(force=True, silent=True) or {}
    emp_id        = (data.get("emp_id") or "").strip().upper()
    credential    = data.get("credential")
    challenge_b64 = session.get("wa_reg_challenge")
    if not emp_id:
        return jsonify({"ok": False, "msg": "Employee ID required"}), 400
    if not challenge_b64:
        app_log.warning("WebAuthn kiosk enrolment: no challenge in session for emp=%s", emp_id)
        return jsonify({"ok": False, "msg": "Session expired — please refresh the page and try again"}), 400
    if session.get("wa_reg_emp_id", "").upper() != emp_id:
        app_log.warning("WebAuthn kiosk: emp_id mismatch — session=%s post=%s",
                        session.get("wa_reg_emp_id"), emp_id)
        return jsonify({"ok": False, "msg": "Employee ID mismatch. Please restart enrollment."}), 403
    try:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id=%s", (emp_id,))
        if not cursor.fetchone():
            cursor.close(); db.close()
            return jsonify({"ok": False, "msg": "Employee ID not found"}), 404
        ok, err = _wa_verify_and_store_registration(emp_id, credential, challenge_b64, cursor, db)
        cursor.close(); db.close()
    except Exception as exc:
        app_log.error("WebAuthn kiosk registration unexpected error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "msg": f"Registration error: {exc}"}), 500
    session.pop("wa_reg_challenge", None)
    session.pop("wa_reg_alg_ids", None)
    if not ok:
        return jsonify({"ok": False, "msg": err}), 400
    app_log.info("WebAuthn kiosk enrolment: emp_id=%s", emp_id)
    return jsonify({"ok": True})



@auth_bp.route("/api/employee/webauthn-unenroll", methods=["POST"])
@limiter.limit("10 per minute")
def webauthn_unenroll():
    """Remove the stored WebAuthn credential for the logged-in employee."""
    emp_id = session.get("employee_id")
    if not emp_id:
        return jsonify({"ok": False, "msg": "Not logged in"}), 401
    try:
        db     = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "UPDATE employees SET fingerprint_credential_id=NULL, fingerprint_public_key=NULL, "
            "fingerprint_sign_count=0 WHERE employee_id=%s",
            (emp_id,)
        )
        db.commit()
        cursor.close(); db.close()
        return jsonify({"ok": True})
    except Exception:
        app_log.error("WebAuthn unenroll failed", exc_info=True)
        return jsonify({"ok": False, "msg": "Failed to remove credential. Please try again."}), 500



@auth_bp.route("/api/employee/<emp_id>/webauthn-credential", methods=["GET"])
@limiter.limit("30 per minute")
def get_employee_webauthn_credential(emp_id):
    """Return the stored WebAuthn credential_id — requires an active admin or employee session."""
    is_admin   = session.get("admin_logged_in")
    session_emp = session.get("employee_id")
    if not (is_admin or session_emp):
        # Also accept a valid Bearer token (kiosk uses admin token)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token_hash = _hash_token(auth[7:])
            with _db() as (cursor, _):
                cursor.execute(
                    "SELECT 1 FROM api_tokens WHERE token=%s AND expires_at > NOW()", (token_hash,)
                )
                if not cursor.fetchone():
                    return jsonify({"ok": False, "msg": "Unauthorized"}), 401
        else:
            return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    emp_id = emp_id.strip().upper()
    # Employees may only retrieve their own credential; admins and Bearer tokens can retrieve any
    if session_emp and not is_admin and session_emp.upper() != emp_id:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT fingerprint_credential_id FROM employees WHERE employee_id=%s LIMIT 1",
            (emp_id,)
        )
        row = cursor.fetchone(); cursor.close(); db.close()
        return jsonify({"ok": True, "credential_id": row[0] if row else None})
    except Exception:
        return jsonify({"ok": True, "credential_id": None})



