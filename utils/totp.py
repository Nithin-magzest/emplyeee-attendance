"""TOTP (RFC 6238) two-factor auth for the admin Email Settings step-up gate.

The secret is stored encrypted at rest via the same Fernet-based encrypt_pii/
decrypt_pii used for PII fields (utils/helpers.py) — reusing the codebase's
one established encryption idiom rather than introducing a second scheme.
"""
import base64
import io
import pyotp
import qrcode
from database import get_db_connection
from utils.helpers import encrypt_pii, decrypt_pii

_ISSUER = "Attendance System"


def get_or_create_admin_totp_secret(admin_username: str):
    """Return (secret, already_enabled). Generates+stores a new secret the
    first time this admin goes through enrollment; reuses it after."""
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT totp_secret, totp_enabled FROM admin_users WHERE username=%s", (admin_username,))
    row = cursor.fetchone()
    if row and row[0]:
        cursor.close()
        db.close()
        return decrypt_pii(row[0]), bool(row[1])
    secret = pyotp.random_base32()
    cursor.execute(
        "UPDATE admin_users SET totp_secret=%s WHERE username=%s",
        (encrypt_pii(secret), admin_username),
    )
    db.commit()
    cursor.close()
    db.close()
    return secret, False


def mark_totp_enabled(admin_username: str):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE admin_users SET totp_enabled=1 WHERE username=%s", (admin_username,))
    db.commit()
    cursor.close()
    db.close()


def reset_admin_totp_secret(admin_username: str):
    """Wipes the stored secret and disables 2FA so the next call to
    get_or_create_admin_totp_secret issues a brand-new secret/QR — for an
    admin who deleted the entry from their authenticator app and can no
    longer produce a code for the old secret."""
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE admin_users SET totp_secret=NULL, totp_enabled=0 WHERE username=%s",
        (admin_username,),
    )
    db.commit()
    cursor.close()
    db.close()


def verify_totp_code(admin_username: str, code: str, require_enabled: bool = True) -> bool:
    """require_enabled=False is only for the one-time enrollment-confirmation
    step, where totp_enabled is still 0 by definition. Every other caller
    (the actual step-up gate) must use the default True."""
    code = (code or "").strip()
    if not code or len(code) != 6 or not code.isdigit():
        return False
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT totp_secret, totp_enabled FROM admin_users WHERE username=%s", (admin_username,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    if not row or not row[0]:
        return False
    if require_enabled and not row[1]:
        return False
    secret = decrypt_pii(row[0])
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def get_or_create_employee_totp_secret(employee_id: str):
    """Return (secret, already_enabled) for employee TOTP."""
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT totp_secret, COALESCE(totp_enabled, 0) FROM employees WHERE employee_id=%s", (employee_id,))
    row = cursor.fetchone()
    if row and row[0]:
        cursor.close()
        db.close()
        return decrypt_pii(row[0]), bool(row[1])
    secret = pyotp.random_base32()
    cursor.execute(
        "UPDATE employees SET totp_secret=%s WHERE employee_id=%s",
        (encrypt_pii(secret), employee_id),
    )
    db.commit()
    cursor.close()
    db.close()
    return secret, False


def mark_employee_totp_enabled(employee_id: str):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET totp_enabled=1 WHERE employee_id=%s", (employee_id,))
    db.commit()
    cursor.close()
    db.close()


def verify_employee_totp_code(employee_id: str, code: str, require_enabled: bool = False) -> bool:
    code = (code or "").strip()
    if not code or len(code) != 6 or not code.isdigit():
        return False
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT totp_secret, COALESCE(totp_enabled, 0) FROM employees WHERE employee_id=%s", (employee_id,))
    row = cursor.fetchone()
    cursor.close()
    db.close()
    if not row or not row[0]:
        return False
    if require_enabled and not row[1]:
        return False
    secret = decrypt_pii(row[0])
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def totp_qr_data_uri(admin_username: str, secret: str) -> str:
    """Base64 PNG data: URI of the provisioning QR code, for the admin/employee to
    scan with Google Authenticator/Authy/etc during enrollment."""
    uri = pyotp.TOTP(secret).provisioning_uri(name=admin_username, issuer_name=_ISSUER)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def send_mfa_login_email(to_email: str, username_or_id: str, role_title: str, secret: str, otp_code: str):
    """Mails the TOTP Authenticator QR code and 6-digit login verification code to user's company email."""
    if not to_email:
        return
    try:
        from utils.email_utils import get_email_config, send_email_async
        cfg = get_email_config()
        qr_uri = totp_qr_data_uri(username_or_id, secret)
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; background: #ffffff;">
          <h2 style="color: #4F46E5; margin-top: 0;">MagHR Premier — Login MFA Verification</h2>
          <p>Hello <strong>{username_or_id}</strong>,</p>
          <p>A login attempt was initiated for your <strong>{role_title}</strong> account.</p>
          <div style="background: #f8fafc; border: 1.5px dashed #4F46E5; border-radius: 10px; padding: 16px; text-align: center; margin: 20px 0;">
            <p style="margin: 0; font-size: 12px; color: #64748b; font-weight: bold; text-transform: uppercase;">Your 6-Digit One-Time Login Code</p>
            <p style="font-size: 32px; font-weight: 800; color: #4F46E5; letter-spacing: 6px; margin: 8px 0;">{otp_code}</p>
          </div>
          <p style="font-size: 13px; color: #475569;">Or scan the Authenticator QR code below to register TOTP with Google Authenticator or Authy:</p>
          <div style="text-align: center; margin: 16px 0;">
            <img src="{qr_uri}" alt="Authenticator QR Code" style="width: 180px; height: 180px; border: 1px solid #cbd5e1; border-radius: 8px;" />
          </div>
          <p style="font-size: 11px; color: #94a3b8; margin-top: 20px;">If you did not request this login, please contact your Security Administrator immediately.</p>
        </div>
        """
        send_email_async(to_email, f"MagHR Login MFA Verification Code: {otp_code}", html_body, cfg)
    except Exception as e:
        from extensions import app_log
        app_log.warning("Could not dispatch MFA login email: %s", e)

