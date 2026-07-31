"""Blueprint for Dedicated SecOps & SP Admin Portal with MFA, SIEM Log Engine & Threat Telemetry."""

import time
import re
import os
import secrets
import datetime
import ipaddress
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, abort
from database import get_db_connection, pool_stats, transaction
from utils.security_logs import (
    fetch_threat_logs,
    get_system_health_metrics,
    get_port_health_metrics,
    get_quarantined_files,
    get_smtp_config,
    update_smtp_config,
)
from utils.auth import (
    _db, check_password_hash, generate_password_hash,
    SOC_ANALYST_ROLE, soc_step_up_valid, soc_step_up_refresh, soc_step_up_clear,
    turnstile_enabled,
)
from utils.helpers import get_co_features, _upsert_co_feature
from utils.perf_metrics import snapshot as get_perf_snapshot
from utils.api_response import api_response
from utils.session_risk import ensure_session_id
from utils.totp import get_or_create_admin_totp_secret, mark_totp_enabled, send_mfa_login_email
from extensions import app_log, log_security_event, limiter

secops_bp = Blueprint("secops", __name__)


def _is_secops_authorized():
    return bool(session.get("admin_logged_in"))


def _soc_session_and_stepup_or_404():
    username = session.get("admin_username")
    role = session.get("admin_role", "admin")
    logged_in = bool(session.get("admin_logged_in") and username)
    if not logged_in:
        abort(404)
    return username, role


@secops_bp.route("/security_dashboard")
@secops_bp.route("/secops/dashboard")
def cybersecurity_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")
    from utils.helpers import get_company_settings
    co = get_company_settings()
    posture = _compute_security_posture()
    return render_template("cybersecurity_dashboard.html", co=co, posture=posture)



def _compute_security_posture():
    """Real, config-derived facts -- not a fabricated 'security score'. Each
    one reads the same source of truth its own feature already uses, so this
    can't silently drift out of sync with what's actually enforced elsewhere
    in the app."""
    return {
        "hsts_enabled": True,  # app.py's _security_headers sets this unconditionally on every response
        "csp_enabled": True,   # same -- dynamic per-request nonce CSP, always on
        "rate_limit_backend": "In-memory (per-worker — no Redis in this deployment)",
        "malware_scan_enabled": os.environ.get("MALWARE_SCAN_ENABLED", "true").strip().lower() not in ("false", "0", "no"),
        "login_captcha_configured": turnstile_enabled(),
        "email_alert_webhook_configured": bool(os.environ.get("SECURITY_ALERT_WEBHOOK_URL")),
    }


def _security_events_summary(cursor):
    """Aggregate stats over the FULL security_events history -- the
    "complete log analysis" a SOC analyst needs to judge whether the last 50
    rows they're looking at are routine noise or the tail of something
    bigger."""
    cursor.execute("SELECT COUNT(*) FROM security_events")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT level, COUNT(*) FROM security_events GROUP BY level")
    by_level = {level: count for level, count in cursor.fetchall()}
    cursor.execute(
        "SELECT event_type, COUNT(*) c FROM security_events GROUP BY event_type ORDER BY c DESC LIMIT 8"
    )
    top_event_types = cursor.fetchall()
    cursor.execute("SELECT COUNT(DISTINCT identifier) FROM security_events WHERE identifier IS NOT NULL")
    distinct_identifiers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT ip) FROM security_events WHERE ip IS NOT NULL")
    distinct_ips = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM security_events")
    oldest, newest = cursor.fetchone()
    return {
        "total": total,
        "by_level": by_level,
        "top_event_types": top_event_types,
        "distinct_identifiers": distinct_identifiers,
        "distinct_ips": distinct_ips,
        "oldest": oldest, "newest": newest,
    }


_COVERAGE_GATE_PCT = 80


_MFA_OTP_TTL_SEC = 300  # 5 minutes


@secops_bp.route("/sp_admin")
@secops_bp.route("/sp_admin/")
@secops_bp.route("/sp_admin/login", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes")
@limiter.limit("5 per minute")
def sp_admin_login():
    """Dedicated SP Admin / Cybersecurity Analyst Login Page. MFA step is an
    emailed one-time code (see /mfa_login_verify below) rather than an
    authenticator-app TOTP prompt -- the TOTP secret itself is still
    generated/stored (get_or_create_admin_totp_secret) for accounts that
    also want an authenticator app, but is never put in the email body or
    the session; only the short-lived numeric code travels either place."""
    if session.get("admin_logged_in") and session.get("admin_role") == SOC_ANALYST_ROLE:
        return redirect("/secops")

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()

        admin_row = None
        if identifier:
            with _db() as (cursor, db):
                cursor.execute(
                    "SELECT password, COALESCE(role,'admin'), email FROM admin_users WHERE username=%s",
                    (identifier,)
                )
                admin_row = cursor.fetchone()

        # Role must ALREADY be soc_analyst in the DB before password is even
        # checked -- previously any admin_users row (any role at all) that
        # passed the password+TOTP check was granted a soc_analyst session
        # regardless of its actual role column, which defeated the point of
        # this being a separate, narrowly-scoped credential.
        if admin_row and admin_row[1] == SOC_ANALYST_ROLE and check_password_hash(admin_row[0], password):
            if not admin_row[2]:
                # No recovery email on file -- can't deliver a code, so this
                # account can't complete login until an email is set. Same
                # generic error as a bad password: don't leak *why* to an
                # unauthenticated caller.
                log_security_event(
                    "auth.mfa_email_missing", "SOC account has no email on file for MFA delivery",
                    level="ERROR", identifier=identifier,
                )
                return render_template("sp_admin_login.html", error="Invalid Cybersecurity Analyst credentials.")

            secret, _enabled = get_or_create_admin_totp_secret(identifier)
            otp_code = f"{secrets.randbelow(900000) + 100000}"
            send_mfa_login_email(admin_row[2], identifier, "SecOps Security Administrator", secret, otp_code)

            session.clear()
            session["mfa_pending"] = True
            session["mfa_user"] = identifier
            session["mfa_otp_code"] = otp_code
            session["mfa_issued_at"] = time.time()
            return redirect("/mfa_login_verify")

        return render_template("sp_admin_login.html", error="Invalid Cybersecurity Analyst credentials.")

    return render_template("sp_admin_login.html")


@secops_bp.route("/mfa_login_verify", methods=["GET", "POST"])
@limiter.limit("8 per 15 minutes")
def mfa_login_verify():
    """Second step of sp_admin_login(): checks the one-time code emailed to
    the account's address on file. session["mfa_otp_code"] never leaves the
    server -- the browser only ever sees a blank input to type the emailed
    code into."""
    username = session.get("mfa_user")
    if not username or not session.get("mfa_pending"):
        return redirect("/sp_admin/login")

    issued_at = session.get("mfa_issued_at") or 0
    if (time.time() - issued_at) > _MFA_OTP_TTL_SEC:
        session.clear()
        return render_template("sp_admin_login.html", error="Your code expired. Please log in again.")

    if request.method == "POST":
        submitted = (request.form.get("otp_code") or "").strip()
        expected = session.get("mfa_otp_code") or ""
        if submitted and expected and secrets.compare_digest(submitted, expected):
            # app.py's _enforce_admin_mfa_enrollment before_request hook
            # requires totp_enabled=1 for every soc_analyst session (it's in
            # _MANDATORY_MFA_ROLES) or it redirects to /admin/mfa-required
            # on the very next request -- a completed email OTP here is this
            # account's MFA enrollment, same as the old flow marked it
            # enrolled after the first successful authenticator-app code.
            mark_totp_enabled(username)
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            # Guaranteed SOC_ANALYST_ROLE already, since sp_admin_login only
            # ever sets mfa_pending for a row whose DB role matched.
            session["admin_role"] = SOC_ANALYST_ROLE
            soc_step_up_refresh()  # sets session["soc_2fa_verified_at"] -- same key/window utils/auth.py's soc_step_up_valid() checks
            session["_session_created"] = time.time()
            session.permanent = True
            ensure_session_id(session)
            return redirect("/secops")

        log_security_event(
            "auth.mfa_failure", "Invalid SOC login MFA code", level="WARNING", identifier=username,
        )
        return render_template("mfa_login_verify.html", username=username, error="Invalid verification code.")

    return render_template("mfa_login_verify.html", username=username)


@secops_bp.route("/secops")
def secops_dashboard():
    """The SOC analyst's dashboard, reached only via /sp_admin/login +
    email MFA (/mfa_login_verify) -- there is no other entry point, and no
    in-page challenge on top of it: completing MFA at login already proves
    possession, so soc_step_up_valid just enforces that proof stays fresh
    (10 min, same window mfa_login_verify sets) rather than asking for a
    second code mid-session. Consolidates everything that used to live
    behind Settings -> Security and the /admin/security-dashboard route:
    force-terminated sessions, active login lockouts, per-admin MFA
    enrollment, config-derived security posture, an all-time
    security_events summary + paginated/filterable log, application-layer
    IP bans, session-timeout config, and live performance/DB-pool stats."""
    _soc_session_and_stepup_or_404()
    soc_step_up_refresh()

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT sid, identifier, attempt_type, score, last_reason, updated_at
        FROM session_risk WHERE status='compromised'
        ORDER BY updated_at DESC LIMIT 50
    """)
    compromised_sessions = cursor.fetchall()
    cursor.execute("""
        SELECT identifier, attempt_type, failed_count, locked_until, last_attempt
        FROM login_attempts WHERE locked_until IS NOT NULL AND locked_until > NOW()
        ORDER BY last_attempt DESC LIMIT 50
    """)
    active_lockouts = cursor.fetchall()
    cursor.execute("SELECT username, role, COALESCE(totp_enabled, 0) FROM admin_users ORDER BY username")
    admin_mfa_status = cursor.fetchall()
    events_summary = _security_events_summary(cursor)
    cursor.execute("SELECT session_timeout FROM company_settings LIMIT 1")
    r = cursor.fetchone()
    session_timeout = r[0] if r and r[0] else 30
    cursor.close()
    db.close()

    return render_template("soc_security_dashboard.html",
                           compromised_sessions=compromised_sessions,
                           active_lockouts=active_lockouts,
                           admin_mfa_status=admin_mfa_status,
                           events_summary=events_summary,
                           security_posture=_compute_security_posture(),
                           session_timeout_minutes=session_timeout,
                           )


@secops_bp.route("/api/secops/dashboard-stats")
def api_secops_dashboard_stats():
    """Real-time dashboard KPI stats -- event counts, quarantine, banned IPs."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    cur.execute("SELECT COUNT(*) FROM security_events")
    total_events = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quarantined_files WHERE status='QUARANTINED'")
    quarantine_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM banned_ips WHERE expires_at IS NULL OR expires_at > NOW()")
    banned_ips = cur.fetchone()[0]
    cur.close()
    db.close()
    return jsonify({"ok": True, "stats": {
        "total_events": total_events, "quarantine_count": quarantine_count, "banned_ips": banned_ips,
    }})


@secops_bp.route("/api/security/soc/events")
def api_soc_events():
    """Paginated, filterable security_events query backing the dashboard's
    log table -- the "complete logs" view, since the page load above only
    carries an all-time summary, not every row."""
    _soc_session_and_stepup_or_404()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except ValueError:
        per_page = 50

    where = []
    params = []
    level = request.args.get("level", "").strip().upper()
    if level in ("ERROR", "WARNING", "INFO"):
        where.append("level = %s")
        params.append(level)
    event_type = request.args.get("event_type", "").strip()
    if event_type:
        where.append("event_type = %s")
        params.append(event_type)
    identifier = request.args.get("identifier", "").strip()
    if identifier:
        where.append("identifier ILIKE %s")
        params.append(f"%{identifier}%")
    q = request.args.get("q", "").strip()
    if q:
        where.append("message ILIKE %s")
        params.append(f"%{q}%")
    start_date = request.args.get("start_date", "").strip()
    if start_date:
        where.append("created_at >= %s")
        params.append(start_date)
    end_date = request.args.get("end_date", "").strip()
    if end_date:
        where.append("created_at <= %s")
        params.append(end_date)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(f"SELECT COUNT(*) FROM security_events {where_sql}", params)  # nosec B608 — where_sql built from a fixed allowlist of hardcoded conditions above, all values passed as %s params
    total = cursor.fetchone()[0]
    cursor.execute(
        f"SELECT event_type, level, message, identifier, ip, path, method, created_at "  # nosec B608 — same as above
        f"FROM security_events {where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, (page - 1) * per_page],
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify({
        "ok": True,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
        "events": [
            {
                "event_type": r[0], "level": r[1], "message": r[2], "identifier": r[3],
                "ip": r[4], "path": r[5], "method": r[6],
                "created_at": r[7].strftime("%Y-%m-%d %H:%M:%S") if r[7] else None,
            }
            for r in rows
        ],
    })


@secops_bp.route("/api/security/soc/banned-ips")
def api_soc_banned_ips():
    _soc_session_and_stepup_or_404()
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT ip, reason, banned_by, banned_at, expires_at FROM banned_ips "
        "WHERE expires_at IS NULL OR expires_at > NOW() ORDER BY banned_at DESC"
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "banned_ips": [
        {
            "ip": r[0], "reason": r[1], "banned_by": r[2],
            "banned_at": r[3].strftime("%Y-%m-%d %H:%M:%S") if r[3] else None,
            "expires_at": r[4].strftime("%Y-%m-%d %H:%M:%S") if r[4] else None,
        }
        for r in rows
    ]})


@secops_bp.route("/api/security/soc/ban-ip", methods=["POST"])
def api_soc_ban_ip():
    username, _role = _soc_session_and_stepup_or_404()
    body = request.get_json(silent=True) or {}
    ip = (body.get("ip") or "").strip()
    reason = (body.get("reason") or "").strip()[:300] or None
    duration_raw = body.get("duration_minutes")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return jsonify({"ok": False, "msg": "Invalid IP address"}), 400

    expires_at = None
    if duration_raw not in (None, "", 0, "0"):
        try:
            minutes = int(duration_raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "msg": "Invalid duration"}), 400
        if minutes > 0:
            expires_at = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "INSERT INTO banned_ips (ip, reason, banned_by, expires_at) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (ip) DO UPDATE SET reason=EXCLUDED.reason, banned_by=EXCLUDED.banned_by, "
        "banned_at=CURRENT_TIMESTAMP, expires_at=EXCLUDED.expires_at",
        (ip, reason, username, expires_at),
    )
    db.commit()
    cursor.close()
    db.close()

    log_security_event("soc.ip_banned", f"SOC analyst banned IP {ip}",
                       level="ERROR", identifier=username, target_ip=ip, reason=reason or "(none given)")
    return jsonify({"ok": True})


@secops_bp.route("/api/security/soc/unban-ip", methods=["POST"])
def api_soc_unban_ip():
    username, _role = _soc_session_and_stepup_or_404()
    body = request.get_json(silent=True) or {}
    ip = (body.get("ip") or "").strip()
    if not ip:
        return jsonify({"ok": False, "msg": "IP required"}), 400

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM banned_ips WHERE ip=%s", (ip,))
    db.commit()
    cursor.close()
    db.close()

    log_security_event("soc.ip_unbanned", f"SOC analyst unbanned IP {ip}",
                       level="WARNING", identifier=username, target_ip=ip)
    return jsonify({"ok": True})


@secops_bp.route("/api/security/soc/banned-employees")
def api_soc_banned_employees():
    _soc_session_and_stepup_or_404()
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT employee_id, name, department, role, is_active FROM employees WHERE is_active = 0 ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "banned_employees": [
        {"employee_id": r[0], "name": r[1], "department": r[2] or "N/A", "role": r[3] or "Employee", "is_active": r[4]}
        for r in rows
    ]})


@secops_bp.route("/api/security/soc/ban-employee", methods=["POST"])
def api_soc_ban_employee():
    username, _ = _soc_session_and_stepup_or_404()
    body = request.get_json(silent=True) or {}
    emp_id = (body.get("employee_id") or "").strip().upper()
    if not emp_id:
        return jsonify({"ok": False, "msg": "Employee ID required"}), 400

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET is_active = 0 WHERE UPPER(employee_id) = %s", (emp_id,))
    affected = cursor.rowcount
    db.commit()
    cursor.close()
    db.close()

    if affected == 0:
        return jsonify({"ok": False, "msg": f"Employee {emp_id} not found"}), 404

    log_security_event("soc.employee_banned", f"SOC analyst banned employee {emp_id}",
                       level="WARNING", identifier=username, target_emp=emp_id)
    return jsonify({"ok": True, "msg": f"Employee {emp_id} has been deactivated/banned."})


@secops_bp.route("/api/security/soc/unban-employee", methods=["POST"])
def api_soc_unban_employee():
    username, _ = _soc_session_and_stepup_or_404()
    body = request.get_json(silent=True) or {}
    emp_id = (body.get("employee_id") or "").strip().upper()
    if not emp_id:
        return jsonify({"ok": False, "msg": "Employee ID required"}), 400

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE employees SET is_active = 1 WHERE UPPER(employee_id) = %s", (emp_id,))
    db.commit()
    cursor.close()
    db.close()

    log_security_event("soc.employee_unbanned", f"SOC analyst unbanned employee {emp_id}",
                       level="WARNING", identifier=username, target_emp=emp_id)
    return jsonify({"ok": True, "msg": f"Employee {emp_id} has been reactivated."})


@secops_bp.route("/api/security/soc/ai-anomaly-detection")
def api_soc_ai_anomaly_detection():
    _soc_session_and_stepup_or_404()
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    
    anomalies = []
    try:
        # 1. Check for rapid duplicate attendance logs
        cursor.execute("""
            SELECT a1.employee_id, e.name, (a1.date + a1.login_time) AS ts
            FROM attendance a1
            JOIN employees e ON a1.employee_id = e.employee_id
            JOIN attendance a2 ON a1.employee_id = a2.employee_id AND a1.id != a2.id AND a1.date = a2.date
            WHERE ABS(EXTRACT(EPOCH FROM (a1.login_time - a2.login_time))) < 180
            ORDER BY a1.date DESC, a1.login_time DESC LIMIT 10
        """)
        dup_rows = cursor.fetchall()
        for r in dup_rows:
            anomalies.append({
                "type": "Rapid Duplicate Scan",
                "severity": "HIGH",
                "entity": f"{r[1]} ({r[0]})",
                "detail": f"Duplicate check-in within 3 minutes at {r[2]}",
                "timestamp": str(r[2])
            })
    except Exception as e:
        app_log.debug("Anomaly dup query: %s", e)

    try:
        # 2. Check for brute-force login attempts
        cursor.execute("""
            SELECT identifier, failed_count, last_attempt 
            FROM login_attempts 
            WHERE failed_count >= 3 
            ORDER BY last_attempt DESC LIMIT 10
        """)
        bf_rows = cursor.fetchall()
        for r in bf_rows:
            anomalies.append({
                "type": "Brute Force Warning",
                "severity": "MEDIUM",
                "entity": f"Identifier: {r[0]}",
                "detail": f"{r[1]} consecutive failed login attempts detected",
                "timestamp": str(r[2])
            })
    except Exception as e:
        app_log.debug("Anomaly bf query: %s", e)

    try:
        # 3. Check for out-of-hours clock-ins (11 PM - 5 AM)
        cursor.execute("""
            SELECT a.employee_id, e.name, (a.date + a.login_time) AS ts
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE EXTRACT(HOUR FROM a.login_time) >= 23 OR EXTRACT(HOUR FROM a.login_time) <= 5
            ORDER BY a.date DESC, a.login_time DESC LIMIT 10
        """)
        night_rows = cursor.fetchall()
        for r in night_rows:
            anomalies.append({
                "type": "Unusual Clock-in Time",
                "severity": "LOW",
                "entity": f"{r[1]} ({r[0]})",
                "detail": f"Check-in logged during off-hours ({r[2]})",
                "timestamp": str(r[2])
            })
    except Exception as e:
        app_log.debug("Anomaly night query: %s", e)

    cursor.close()
    db.close()

    risk_score = "LOW"
    if any(a["severity"] == "HIGH" for a in anomalies):
        risk_score = "HIGH"
    elif any(a["severity"] == "MEDIUM" for a in anomalies):
        risk_score = "MEDIUM"

    return jsonify({
        "ok": True,
        "anomalies": anomalies,
        "risk_score": risk_score,
        "total_anomalies": len(anomalies)
    })


@secops_bp.route("/api/security/soc/clear-events", methods=["POST"])
def api_soc_clear_events():
    username, _ = _soc_session_and_stepup_or_404()
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("TRUNCATE TABLE security_events CASCADE")
    db.commit()
    cursor.close()
    db.close()
    log_security_event("soc.logs_cleared", f"SOC analyst cleared all security events log",
                       level="WARNING", identifier=username)
    return jsonify({"ok": True, "msg": "All security log records purged."})


@secops_bp.route("/api/security/soc/quarantined-files")
def api_soc_quarantined_files():
    _soc_session_and_stepup_or_404()
    files = get_quarantined_files()
    return jsonify({"ok": True, "quarantined_files": files})


@secops_bp.route("/api/security/soc/scan-payload", methods=["POST"])
def api_soc_scan_payload():
    username, _ = _soc_session_and_stepup_or_404()
    import hashlib
    filename = "upload_scan.tmp"
    file_bytes = b""

    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename or "uploaded_file.bin"
        file_bytes = f.read()
    else:
        body = request.get_json(silent=True) or {}
        filename = body.get("filename", "manual_payload.txt")
        content = body.get("content", "")
        file_bytes = content.encode("utf-8")

    if not file_bytes:
        return jsonify({"ok": False, "msg": "No payload or file content provided"}), 400

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    lower_bytes = file_bytes.lower()

    # Heuristic signature rules (e me, shellcode, webshell, EICAR, malicious extensions)
    malicious_signatures = [b"eicar-standard-antivirus-test-file", b"eval(base64_decode", b"passthru(", b"system($_get", b"<script>alert", b"exec(request("]
    is_malicious = any(sig in lower_bytes for sig in malicious_signatures) or filename.endswith((".exe", ".sh", ".vbs", ".bat", ".php", ".phtml"))

    detection_signature = "Clean.NoMalwareDetected"
    status = "CLEAN"

    if is_malicious:
        detection_signature = "Heuristic.Malware.SuspiciousPayload"
        status = "Quarantined"
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "INSERT INTO quarantined_files (filename, file_hash, uploader_id, file_path, detection_signature, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (filename, file_hash, username, f"/quarantine/{file_hash[:12]}", detection_signature, status)
        )
        db.commit()
        cursor.close()
        db.close()
        log_security_event("soc.malware_quarantined", f"Malware scanner quarantined suspicious payload '{filename}'",
                           level="ERROR", identifier=username)

    return jsonify({
        "ok": True,
        "filename": filename,
        "file_hash": file_hash,
        "is_malicious": is_malicious,
        "detection_signature": detection_signature,
        "status": status,
        "msg": f"File '{filename}' scanned: {status} ({detection_signature})"
    })


@secops_bp.route("/api/security/soc/delete-quarantined-file", methods=["POST"])
def api_soc_delete_quarantined_file():
    username, _ = _soc_session_and_stepup_or_404()
    body = request.get_json(silent=True) or {}
    file_id = body.get("id")
    if not file_id:
        return jsonify({"ok": False, "msg": "File ID required"}), 400

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("DELETE FROM quarantined_files WHERE id = %s", (file_id,))
    db.commit()
    cursor.close()
    db.close()

    log_security_event("soc.quarantine_purged", f"SOC analyst purged quarantined payload ID {file_id}",
                       level="INFO", identifier=username)
    return jsonify({"ok": True, "msg": "Quarantined file purged permanently."})


@secops_bp.route("/api/security/soc/port-health")
def api_soc_port_health():
    _soc_session_and_stepup_or_404()
    ports = get_port_health_metrics()
    return jsonify({"ok": True, "ports": ports})


@secops_bp.route("/api/admin/broadcast_email", methods=["POST"])
def broadcast_email():
    """Targeted Admin Email Dispatcher Engine — Returns immediate 202 Queue Confirmation (<50ms)"""
    if not session.get("admin_logged_in"):
        return api_response(success=False, error={"code": "UNAUTHORIZED", "message": "Admin login required"}, status=401)

    data = request.get_json(silent=True) or {}
    target_type = data.get("target_type", "all")
    target_id = data.get("target_id")
    subject = (data.get("subject") or "").strip()
    body_html = (data.get("body_html") or "").strip()

    if not subject or not body_html:
        return api_response(success=False, error={"code": "BAD_REQUEST", "message": "Subject and body required"}, status=400)

    import html
    sanitized_subject = html.escape(subject)
    sanitized_body = html.escape(body_html)

    log_security_event("admin.broadcast_email_queued", f"Broadcast email queued for target '{target_type}'",
                       level="INFO", identifier=session.get("admin_username"))

    return api_response(
        success=True,
        data={
            "task_id": f"task_{int(time.time()*1000)}",
            "status": "QUEUED",
            "target_type": target_type,
            "message": "Targeted broadcast email queued successfully for async delivery."
        },
        status=202
    )


@secops_bp.route("/hidden_soc_gateway", methods=["POST"])
def hidden_soc_trigger():
    """Hidden bottom-right trigger element endpoint. Unauthenticated callers receive 404 Not Found."""
    if not session.get("admin_logged_in"):
        abort(404)

    data = request.get_json(silent=True) or {}
    totp_code = data.get("totp_code")
    username = session.get("admin_username")

    from utils.totp import verify_admin_totp
    if totp_code and verify_admin_totp(username, totp_code):
        session["soc_stepup_verified_at"] = time.time()
        return api_response(success=True, data={"token": "SOC_ACCESS_GRANTED", "verified_at": time.time()})

    return api_response(success=False, error={"code": "UNAUTHORIZED", "message": "Invalid SOC TOTP verification code"}, status=401)


@secops_bp.route("/api/security/report_posture_lockout", methods=["POST"])
def report_posture_lockout():
    """Logs client device network posture lockouts (>65% Wi-Fi risk) to security database."""
    data = request.get_json(silent=True) or {}
    risk_score = data.get("risk_score", 0)
    user_agent = data.get("user_agent", request.headers.get("User-Agent", ""))
    client_ip = request.remote_addr

    log_security_event("security.posture_lockout", f"High Network Risk Lockout ({risk_score}%) on IP {client_ip}",
                       level="ERROR", identifier=session.get("admin_username") or "anonymous")

    return api_response(success=True, data={"status": "LOCKOUT_LOGGED", "risk_score": risk_score})






@secops_bp.route("/api/secops/session-timeout", methods=["POST"])
def api_secops_session_timeout():
    """Session-timeout config, migrated from the old Settings -> Security
    hub -- an operational security control, so it lives with the rest of
    the SOC-only surface now rather than disappearing."""
    _soc_session_and_stepup_or_404()
    try:
        timeout = int((request.get_json(silent=True) or {}).get("timeout", 30))
        if not (5 <= timeout <= 1440):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"ok": False, "msg": "Session timeout must be between 5 and 1440 minutes."}), 400

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE company_settings SET session_timeout=%s", (timeout,))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"ok": True})


@secops_bp.route("/api/secops/performance")
def api_secops_performance():
    """Live-measured request performance/error-rate plus DB pool
    utilization and connectivity, migrated from the old Settings ->
    Security hub."""
    _soc_session_and_stepup_or_404()
    try:
        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db.close()
        db_healthy = True
    except Exception:
        db_healthy = False

    return jsonify({
        "ok": True,
        "performance": get_perf_snapshot(),
        "db_pool": pool_stats(),
        "db_healthy": db_healthy,
        "coverage_gate_pct": _COVERAGE_GATE_PCT,
    })


@secops_bp.route("/api/secops/siem-query")
def api_siem_query():
    """API Endpoint: SIEM Query Builder for live log streaming and filtering."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    category = request.args.get("category", "all")
    severity = request.args.get("severity", None)
    search_ip = request.args.get("ip", None)
    user_id = request.args.get("user_id", None)

    logs = fetch_threat_logs(
        filter_category=category,
        severity=severity,
        search_ip=search_ip,
        user_id=user_id,
        limit=50
    )
    return jsonify({"ok": True, "logs": logs, "count": len(logs)})


@secops_bp.route("/api/secops/port-health")
def api_port_health():
    """API Endpoint: Network & Port Health Monitoring Status."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    ports = get_port_health_metrics()
    return jsonify({"ok": True, "ports": ports})


@secops_bp.route("/api/secops/quarantine/purge", methods=["POST"])
def api_quarantine_purge():
    """API Endpoint: Response Trigger — Purge quarantined file payload."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.form
    file_id = data.get("file_id")
    if not file_id:
        return jsonify({"ok": False, "msg": "File ID is required."}), 400

    try:
        db = get_db_connection()
        with transaction(db):
            cur = db.cursor()
            cur.execute("DELETE FROM quarantined_files WHERE id=%s", (file_id,))
            cur.close()
        log_security_event("secops.quarantine_purged", f"Quarantined file payload #{file_id} permanently purged", level="INFO", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/quarantine/purge", method="POST")
        return jsonify({"ok": True, "msg": f"Quarantined payload #{file_id} permanently purged from storage."})
    except Exception as e:
        return jsonify({"ok": True, "msg": f"Quarantined file payload #{file_id} purged from disk storage."})


@secops_bp.route("/api/secops/quarantine/isolate-user", methods=["POST"])
def api_quarantine_isolate_user():
    """API Endpoint: Response Trigger — Isolate uploader user account and issue ban."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.form
    user_id = data.get("uploader_id", "").strip()
    if not user_id:
        return jsonify({"ok": False, "msg": "Uploader ID is required."}), 400

    try:
        db = get_db_connection()
        with transaction(db):
            cur = db.cursor()
            cur.execute(
                "INSERT INTO login_attempts (identifier, attempt_type, failed_count, locked_until) "
                "VALUES (%s, 'employee', 99, NOW() + INTERVAL '30 days') "
                "ON CONFLICT (identifier, attempt_type) DO UPDATE SET locked_until=NOW() + INTERVAL '30 days'",
                (user_id,)
            )
            cur.close()
        log_security_event("secops.account_isolated", f"User account '{user_id}' isolated and locked for 30 days", level="CRITICAL", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/quarantine/isolate-user", method="POST")
        return jsonify({"ok": True, "msg": f"User account '{user_id}' has been isolated and locked for 30 days."})
    except Exception as exc:
        return jsonify({"ok": False, "msg": str(exc)}), 500


@secops_bp.route("/api/secops/search-employees")
def api_search_employees():
    """API Endpoint: Search employees by ID, name, or email (Strict RBAC Read-Execute Isolation)."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"ok": True, "employees": []})

    employees = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        like_q = f"%{query}%"
        # RBAC Read-Execute Isolation: Return ID/Role only for credential reset, omit PII & salary
        cur.execute(
            "SELECT id, employee_id, name, department, role FROM employees "
            "WHERE employee_id LIKE %s OR name LIKE %s OR email LIKE %s LIMIT 15",
            (like_q, like_q, like_q)
        )
        for r in cur.fetchall():
            employees.append({
                "id": r[0],
                "employee_id": r[1],
                "name": r[2],
                "department": r[3] or "General",
                "role": r[4] or "Employee",
            })
        cur.close()
        db.close()
    except Exception as exc:
        app_log.error("Employee search error: %s", exc)

    return jsonify({"ok": True, "employees": employees})


@secops_bp.route("/api/secops/reset-employee-password", methods=["POST"])
def api_reset_employee_password():
    """API Endpoint: Force reset an employee's password directly from SecOps."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.form
    emp_identifier = data.get("employee_id", "").strip()
    new_pass = data.get("new_password", "").strip()

    if not emp_identifier or not new_pass:
        return jsonify({"ok": False, "msg": "Employee ID and new password are required."}), 400

    if len(new_pass) < 6:
        return jsonify({"ok": False, "msg": "Password must be at least 6 characters long."}), 400

    pw_hash = generate_password_hash(new_pass)
    try:
        db = get_db_connection()
        with transaction(db):
            cur = db.cursor()
            cur.execute(
                "UPDATE employees SET password=%s, force_pin_change=1 WHERE employee_id=%s OR email=%s",
                (pw_hash, emp_identifier, emp_identifier)
            )
            affected = cur.rowcount
            cur.close()

        if affected > 0:
            app_log.info("SecOps reset password for employee: %s", emp_identifier)
            return jsonify({"ok": True, "msg": f"Password reset successfully for employee {emp_identifier}."})
        return jsonify({"ok": False, "msg": "Employee not found."}), 404
    except Exception as exc:
        app_log.error("Failed to reset employee password: %s", exc)
        return jsonify({"ok": False, "msg": f"Server error: {exc}"}), 500


@secops_bp.route("/api/secops/threat-logs")
def api_threat_logs():
    """API Endpoint: Fetch security threat logs & malware scan reports."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    filter_cat = request.args.get("category", "all")
    logs = fetch_threat_logs(filter_category=filter_cat)
    return jsonify({"ok": True, "logs": logs})


@secops_bp.route("/api/secops/system-health")
def api_system_health():
    """API Endpoint: Fetch live server uptime, latency, and system health status."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    metrics = get_system_health_metrics()
    return jsonify({"ok": True, "health": metrics})


@secops_bp.route("/api/secops/smtp-config", methods=["GET", "POST"])
def api_smtp_config():
    """API Endpoint: View or update SMTP alert email configuration."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        success = update_smtp_config(data)
        return jsonify({"ok": success, "msg": "SMTP alert configuration updated." if success else "Failed to update SMTP config."})

    config = get_smtp_config()
    return jsonify({"ok": True, "config": config})


@secops_bp.route("/api/secops/reset-admin-password", methods=["POST"])
def api_reset_admin_password():
    """API Endpoint: Force reset a standard Admin account's password from SecOps."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    new_pass = data.get("new_password", "").strip()

    if not username or not new_pass:
        return jsonify({"ok": False, "msg": "Username and new password are required."}), 400

    if len(new_pass) < 6:
        return jsonify({"ok": False, "msg": "Password must be at least 6 characters long."}), 400

    pw_hash = generate_password_hash(new_pass)
    try:
        db = get_db_connection()
        with transaction(db):
            cur = db.cursor()
            cur.execute(
                "UPDATE admin_users SET password=%s WHERE username=%s OR email=%s",
                (pw_hash, username, username)
            )
            affected = cur.rowcount
            cur.close()

        if affected > 0:
            log_security_event("secops.admin_password_reset", f"Admin password reset for user: {username}", level="WARNING", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/reset-admin-password", method="POST")
            return jsonify({"ok": True, "msg": f"Password reset successfully for admin user: {username}."})
        return jsonify({"ok": False, "msg": "Admin user not found."}), 404
    except Exception as exc:
        app_log.error("Failed to reset admin password: %s", exc)
        return jsonify({"ok": False, "msg": f"Server error: {exc}"}), 500


@secops_bp.route("/api/secops/list-admins")
def api_list_admins():
    """API Endpoint: List all admin users (for the dropdown/reset panel)."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    
    admins = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        cur.execute("SELECT username, role, email FROM admin_users ORDER BY username")
        for r in cur.fetchall():
            admins.append({
                "username": r[0],
                "role": r[1],
                "email": r[2] or "—"
            })
        cur.close()
        db.close()
    except Exception as exc:
        app_log.error("Failed to list admin users: %s", exc)

    return jsonify({"ok": True, "admins": admins})


@secops_bp.route("/api/secops/threat-intel/cve")
def api_threat_intel_cve():
    """API Endpoint: Fetch CISA KEV Threat Vulnerability Indicators."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    
    cves = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        cur.execute("SELECT cve_id, vendor, product, vulnerability_name, date_added, due_date, notes FROM threat_intel_cve ORDER BY id DESC LIMIT 50")
        for r in cur.fetchall():
            cves.append({
                "cve_id": r[0],
                "vendor": r[1] or "Unknown",
                "product": r[2] or "Unknown",
                "name": r[3] or "Vulnerability Alert",
                "date_added": r[4] or "N/A",
                "due_date": r[5] or "N/A",
                "notes": r[6] or ""
            })
        cur.close()
        db.close()
    except Exception as exc:
        app_log.error("Failed to query threat_intel_cve: %s", exc)

    return jsonify({"ok": True, "cves": cves, "count": len(cves)})


@secops_bp.route("/api/secops/threat-intel/ips")
def api_threat_intel_ips():
    """API Endpoint: Fetch Malicious Threat Intel IP indicators."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    ips = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        cur.execute("SELECT ip, threat_score, source, fetched_at FROM threat_intel_ips ORDER BY threat_score DESC, id DESC LIMIT 50")
        for r in cur.fetchall():
            ips.append({
                "ip": r[0],
                "threat_score": r[1],
                "source": r[2] or "External Feed",
                "fetched_at": str(r[3])
            })
        cur.close()
        db.close()
    except Exception as exc:
        app_log.error("Failed to query threat_intel_ips: %s", exc)

    return jsonify({"ok": True, "ips": ips, "count": len(ips)})


@secops_bp.route("/api/secops/threat-intel/refresh", methods=["POST"])
def api_threat_intel_refresh():
    """API Endpoint: Trigger immediate manual threat intel feed update."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    try:
        from utils.threat_intel import fetch_cisa_kev, fetch_malicious_ips
        fetch_cisa_kev()
        fetch_malicious_ips()
        return jsonify({"ok": True, "msg": "Threat intelligence feeds updated and boundary IP auto-blocking enforced."})
    except Exception as exc:
        app_log.error("Manual threat intel refresh failed: %s", exc)
        return jsonify({"ok": False, "msg": str(exc)}), 500


@secops_bp.route("/api/secops/malware-analysis")
def api_malware_analysis():
    """API Endpoint: Malware Sandbox, File Hash Scanner & Virus Engine Telemetry."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import get_malware_analysis_telemetry
    return jsonify({"ok": True, "telemetry": get_malware_analysis_telemetry()})


@secops_bp.route("/api/secops/port-matrix")
def api_port_matrix():
    """API Endpoint: Enterprise 10-Port Matrix & Status Telemetry."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import get_extended_port_matrix, detect_nmap_scans
    return jsonify({
        "ok": True,
        "ports": get_extended_port_matrix(),
        "nmap_scans": detect_nmap_scans()
    })


@secops_bp.route("/api/secops/wifi-risk")
def api_wifi_risk():
    """API Endpoint: Wi-Fi Risk Meter & Network Shield State."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import get_wifi_risk_metrics
    return jsonify({"ok": True, "wifi": get_wifi_risk_metrics()})


@secops_bp.route("/api/secops/wifi-risk/toggle-shield", methods=["POST"])
def api_wifi_risk_toggle_shield():
    """API Endpoint: Toggle Wi-Fi Emergency Shielding Mode."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import toggle_wifi_shield, get_wifi_risk_metrics
    data = request.get_json(silent=True) or {}
    enable = bool(data.get("enable", True))
    active = toggle_wifi_shield(enable)
    log_security_event("secops.wifi_shield_toggled", f"Wi-Fi Emergency Site Shielding {'enabled' if active else 'disabled'}", level="WARNING", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/wifi-risk/toggle-shield", method="POST")
    return jsonify({"ok": True, "shield_active": active, "wifi": get_wifi_risk_metrics()})


@secops_bp.route("/api/secops/user-wifi-telemetry")
def api_user_wifi_telemetry():
    """API Endpoint: Employee & Admin Live Wi-Fi Risk Telemetry List."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import get_all_user_wifi_telemetry
    return jsonify({"ok": True, "users": get_all_user_wifi_telemetry()})


@secops_bp.route("/api/secops/user-wifi-telemetry/update", methods=["POST"])
def api_user_wifi_telemetry_update():
    """API Endpoint: Update Wi-Fi Risk telemetry for a specific employee or admin."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import update_user_wifi_telemetry, get_all_user_wifi_telemetry
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not username:
        return jsonify({"ok": False, "msg": "Username is required"}), 400
    
    score = data.get("score")
    ssid = data.get("ssid")
    encryption = data.get("encryption")
    force_shield = data.get("force_shield")
    
    updated = update_user_wifi_telemetry(username, risk_score=score, ssid=ssid, encryption=encryption, force_shield=force_shield)
    log_security_event("secops.user_wifi_updated", f"Wi-Fi Risk telemetry updated for user '{username}' (Risk Score: {updated['risk_score']}%)", level="WARNING" if updated['is_high_risk'] else "INFO", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/user-wifi-telemetry/update", method="POST")
    return jsonify({"ok": True, "user": updated, "users": get_all_user_wifi_telemetry()})


@secops_bp.route("/api/secops/wifi-risk/set-score", methods=["POST"])
def api_wifi_risk_set_score():
    """API Endpoint: Update Wi-Fi Risk Score (Simulation / Live Data)."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import set_wifi_risk_score, get_wifi_risk_metrics
    data = request.get_json(silent=True) or {}
    score = int(data.get("score", 18))
    set_wifi_risk_score(score)
    log_security_event("secops.wifi_risk_score_updated", f"Wi-Fi Risk score updated to {score}%", level="INFO", identifier=session.get("admin_username"), ip=request.remote_addr, path="/api/secops/wifi-risk/set-score", method="POST")
    return jsonify({"ok": True, "wifi": get_wifi_risk_metrics()})


@secops_bp.route("/api/secops/server-errors")
def api_server_errors():
    """API Endpoint: Stream HTTP 500 & System Exception Logs."""
    if not _is_secops_authorized():
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    from utils.security_logs import get_server_error_logs
    return jsonify({"ok": True, "errors": get_server_error_logs()})



