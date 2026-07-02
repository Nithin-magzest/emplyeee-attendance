"""Email sending — SMTP + DB-backed queue with retry worker."""
import os
import ssl
import base64
import smtplib
import threading
import time as _time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from database import get_db_connection
from extensions import app_log


def get_email_config():
    """Return SMTP config dict from DB, falling back to .env values."""
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT host, port, username, password, from_name, from_email FROM email_config LIMIT 1"
        )
        row = cursor.fetchone(); cursor.close(); db.close()
        if row and row[0]:
            return {
                "host": row[0], "port": row[1], "user": row[2], "password": row[3],
                "from_name": row[4], "from_email": row[5] or row[2],
            }
    except Exception:
        pass
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
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute("SELECT email FROM admin_users WHERE email IS NOT NULL AND email != ''")
    emails = [row[0] for row in cursor.fetchall()]
    cursor.close(); db.close()
    return emails


def send_email_smtp(to_email, subject, html_body, config,
                    attachment_bytes=None, attachment_filename=None):
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
        with smtplib.SMTP_SSL(config["host"], port, context=context, timeout=20) as server:
            server.login(config["user"], config["password"])
            server.sendmail(from_addr, to_email, msg.as_string())
    else:
        with smtplib.SMTP(config["host"], port, timeout=20) as server:
            server.ehlo(); server.starttls(context=context); server.ehlo()
            server.login(config["user"], config["password"])
            server.sendmail(from_addr, to_email, msg.as_string())


def send_email_async(to_email, subject, html_body, config,
                     attachment_bytes=None, attachment_filename=None, **_):
    """Enqueue email for reliable delivery via the DB-backed worker."""
    att_b64 = base64.b64encode(attachment_bytes).decode() if attachment_bytes else None
    try:
        db  = get_db_connection(); cur = db.cursor()
        cur.execute(
            "INSERT INTO email_queue (to_email, subject, html_body, attachment_b64, attachment_filename) "
            "VALUES (%s,%s,%s,%s,%s)",
            (to_email, subject, html_body, att_b64, attachment_filename)
        )
        db.commit(); cur.close(); db.close()
    except Exception as e:
        app_log.error("Failed to enqueue email to %s: %s", to_email, e)
        threading.Thread(
            target=lambda: send_email_smtp(to_email, subject, html_body, config,
                                           attachment_bytes=attachment_bytes,
                                           attachment_filename=attachment_filename),
            daemon=True
        ).start()


def _email_queue_worker():
    """Background thread: dequeues and sends emails; retries up to 3 times."""
    while True:
        try:
            cfg = get_email_config()
            if not cfg:
                _time.sleep(30)
                continue
            db  = get_db_connection(); cur = db.cursor(buffered=True)
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
                                    attachment_bytes=att_bytes, attachment_filename=att_name)
                    cur.execute(
                        "UPDATE email_queue SET status='done', sent_at=NOW() WHERE id=%s", (eid,)
                    )
                except Exception as exc:
                    app_log.error("Email queue send failed to %s: %s", to_email, exc)
                    cur.execute(
                        "UPDATE email_queue SET status='pending', last_error=%s WHERE id=%s",
                        (str(exc)[:500], eid)
                    )
                db.commit()
            cur.execute(
                "UPDATE email_queue SET status='failed' WHERE status='pending' AND attempts >= 3"
            )
            db.commit(); cur.close(); db.close()
        except Exception as _we:
            app_log.error("Email queue worker error: %s", _we)
        _time.sleep(15)


def build_attendance_email(employee_name, emp_id, action, status, time_str, today_str):
    color        = "#16a34a" if action == "login" else "#2563eb"
    action_label = "Checked In" if action == "login" else "Checked Out"
    return f"""
<div style="font-family:Segoe UI,sans-serif;max-width:520px;margin:auto;background:#f8fafc;
            border-radius:16px;overflow:hidden;border:1px solid #dbeafe;">
  <div style="background:#1e3a8a;padding:24px 28px;color:white;">
    <div style="font-size:20px;font-weight:700;">&#127970; Employee Attendance System</div>
  </div>
  <div style="padding:28px;">
    <p style="color:#334155;">Hello <strong>{employee_name}</strong>,</p>
    <div style="background:{color};color:#fff;border-radius:12px;padding:18px 22px;margin:20px 0;">
      <div style="font-size:18px;font-weight:700;">&#10003; {action_label}</div>
      <div style="margin-top:6px;opacity:0.9;">Status: {status}</div>
      <div style="margin-top:4px;opacity:0.9;">Time: {time_str} on {today_str}</div>
    </div>
    <p style="color:#64748b;font-size:13px;">Employee ID: {emp_id}</p>
  </div>
</div>"""
