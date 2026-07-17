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


def totp_qr_data_uri(admin_username: str, secret: str) -> str:
    """Base64 PNG data: URI of the provisioning QR code, for the admin to
    scan with Google Authenticator/Authy/etc during enrollment."""
    uri = pyotp.TOTP(secret).provisioning_uri(name=admin_username, issuer_name=_ISSUER)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
