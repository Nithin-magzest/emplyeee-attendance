"""Auth blueprint — login, logout, password reset, WebAuthn."""
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Migrated from app.py — each function is registered on auth_bp instead of app.
#
# Source routes (move from app.py, replacing @app.route with @auth_bp.route):
#
#   /setup                       → setup_wizard
#   /admin_login                 → admin_login          (keep @limiter.limit)
#   /logout                      → logout
#   /employee_login              → employee_login
#   /employee_logout             → employee_logout
#   /change_password             → change_password
#   /force_change_pin            → force_change_pin
#   /change_admin_password       → change_admin_password
#   /admin_set_recovery_email    → admin_set_recovery_email
#   /admin_forgot_password       → admin_forgot_password (keep @limiter.limit)
#   /admin_reset_password/<tok>  → admin_reset_password (keep @limiter.limit)
#   /employee_forgot_password    → employee_forgot_password (keep @limiter.limit)
#   /employee_reset_password/<t> → employee_reset_password (keep @limiter.limit)
#   /webauthn/registration-options       → webauthn_registration_options
#   /webauthn/authentication-options     → webauthn_authentication_options
#   /api/employee/webauthn-verify-challenge  → api_employee_webauthn_verify_challenge
#   /api/employee/webauthn-register      → webauthn_register  (keep @limiter.limit)
#   /api/employee/webauthn-unenroll      → webauthn_unenroll  (keep @limiter.limit)
#   /api/employee/<>/webauthn-credential → get_employee_webauthn_credential
#   /api/employee/mobile-biometric-nonce → api_employee_mobile_biometric_nonce
#   /api/employee/mobile-biometric-attest→ api_employee_mobile_biometric_attest
#
# Import pattern for each moved route:
#
#   from extensions import app, limiter
#   from utils.auth import (admin_required, employee_required,
#                           employee_api_required, generate_password_hash,
#                           check_password_hash, _hash_token, _db,
#                           _check_login_lockout, _record_login_failure,
#                           _clear_login_failures)
#   from utils.helpers import get_company_settings
#   from utils.email_utils import get_email_config, send_email_smtp, send_email_async
#   from database import get_db_connection
#
# url_for changes required (6 total in app.py):
#   url_for("admin_login")    → url_for("auth.admin_login")
#   url_for("employee_login") → url_for("auth.employee_login")
# ─────────────────────────────────────────────────────────────────────────────
