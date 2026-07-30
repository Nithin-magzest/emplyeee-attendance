"""Enterprise Web Application Firewall (WAF) & Threat Inspection Engine.

Provides deep packet inspection for SQL Injection (SQLi), Cross-Site Scripting (XSS),
Path Traversal (LFI), Remote Code Execution (RCE), and Command Injection.
Automatically bans offending client IPs into PostgreSQL 'banned_ips'.
"""
import re
import datetime
import logging
from flask import request, render_template, g
from database import get_db_connection
from extensions import log_security_event

logger = logging.getLogger("attendance")

# Threat Signatures
SQLI_PATTERNS = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|GRANT|REVOKE|TRUNCATE)\b|"
    r"(--)|(/\*|\*/)|(\bOR\b\s+\d+=\d+)|(\bAND\b\s+\d+=\d+)|(SLEEP\(|BENCHMARK\())",
    re.IGNORECASE
)

XSS_PATTERNS = re.compile(
    r"(<script.*?>|javascript:|onload\s*=|onerror\s*=|onclick\s*=|document\.cookie|<iframe|<object|<embed)",
    re.IGNORECASE
)

LFI_PATTERNS = re.compile(
    r"(\.\./|\.\.\\|/etc/passwd|/proc/self/|c:\\boot\.ini)",
    re.IGNORECASE
)

RCE_PATTERNS = re.compile(
    r"(;\s*(cat|ls|whoami|id|bash|sh|curl|wget|nc|python|perl|ruby)\b|\|\s*(bash|sh)|`.*`)",
    re.IGNORECASE
)

SUSPICIOUS_USER_AGENTS = re.compile(
    r"(nikto|sqlmap|nmap|masscan|dirbuster|gobuster|wpscan|python-requests|acunetix|havij)",
    re.IGNORECASE
)


def inspect_request():
    """Flask before_request hook: Deep packet inspection for security threats."""
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")
    path = request.path
    method = request.method

    # 1. User-Agent Scanner Inspection
    if SUSPICIOUS_USER_AGENTS.search(user_agent):
        _trigger_waf_block(client_ip, "Automated Vulnerability Scanner Detected", f"User-Agent: {user_agent}")
        return render_template("firewall_blocked.html",
                               client_ip=client_ip,
                               threat_category="Security Scanner Detected",
                               path=path,
                               timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 403

    # 2. Inspect Query String Parameters & Path
    query_str = request.query_string.decode("utf-8", errors="ignore")
    full_url = f"{path}?{query_str}"

    threat = _scan_payload(full_url)
    if threat:
        _trigger_waf_block(client_ip, threat["category"], f"Matched signature: {threat['matched']} in URL {path}")
        return render_template("firewall_blocked.html",
                               client_ip=client_ip,
                               threat_category=threat["category"],
                               path=path,
                               timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 403

    # 3. Inspect Form & JSON Payload (if text-based content)
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            if request.is_json:
                json_str = str(request.get_json(silent=True) or "")
                threat = _scan_payload(json_str)
            else:
                form_data = " ".join([f"{k}={v}" for k, v in request.form.items()])
                threat = _scan_payload(form_data)

            if threat:
                _trigger_waf_block(client_ip, threat["category"], f"Matched signature in POST body on path {path}")
                return render_template("firewall_blocked.html",
                                       client_ip=client_ip,
                                       threat_category=threat["category"],
                                       path=path,
                                       timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 403
        except Exception as ex:
            logger.warning(f"[WAF] Error inspecting POST payload: {ex}")

    return None


def _scan_payload(payload_str):
    """Scans a text payload against WAF threat signatures."""
    if not payload_str:
        return None

    if SQLI_PATTERNS.search(payload_str):
        return {"category": "SQL Injection (SQLi) Attack", "matched": "SQLi Signature"}
    if XSS_PATTERNS.search(payload_str):
        return {"category": "Cross-Site Scripting (XSS) Attack", "matched": "XSS Signature"}
    if LFI_PATTERNS.search(payload_str):
        return {"category": "Path Traversal / Local File Inclusion", "matched": "LFI Signature"}
    if RCE_PATTERNS.search(payload_str):
        return {"category": "Remote Code Execution (RCE)", "matched": "RCE Signature"}
    return None


def _trigger_waf_block(client_ip, threat_category, details):
    """Logs threat event and automatically bans offending IP for 24 hours."""
    log_security_event(
        "waf.attack_blocked",
        f"WAF Intercepted Threat ({threat_category}): {details}",
        level="CRITICAL",
        ip=client_ip,
        path=request.path,
        method=request.method
    )

    # Auto-ban offending IP for 24 hours
    try:
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO banned_ips (ip, reason, banned_by, expires_at) VALUES (%s, %s, 'WAF Engine', %s) "
            "ON CONFLICT (ip) DO UPDATE SET reason=EXCLUDED.reason, expires_at=EXCLUDED.expires_at",
            (client_ip, f"WAF Auto-Ban: {threat_category}", expires_at)
        )
        db.commit()
        cursor.close()
        db.close()
        logger.warning(f"[WAF] Auto-banned IP {client_ip} for threat: {threat_category}")
    except Exception as ex:
        logger.error(f"[WAF] Failed to insert auto-ban for IP {client_ip}: {ex}")
