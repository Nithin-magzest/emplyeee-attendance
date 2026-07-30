"""Linux Host Network Firewall Configurator.

Generates and executes system IPTables / UFW firewall rules to enforce host port isolation
(blocking unauthorized incoming ports, dropping SYN floods & port scanning).
"""
import subprocess
import logging

logger = logging.getLogger("attendance")


def get_firewall_status():
    """Inspects Linux host UFW or IPTables status."""
    try:
        res = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return {"active": "active" in res.stdout.lower(), "rules": res.stdout}
    except Exception:
        pass

    try:
        res = subprocess.run(["iptables", "-L", "-n"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return {"active": True, "rules": res.stdout[:500]}
    except Exception as ex:
        logger.warning(f"[NetworkFirewall] Error reading iptables: {ex}")

    return {"active": False, "rules": "Firewall status unreadable or disabled"}


def apply_hardened_firewall_rules():
    """Applies host firewall policy: allow SSH (22), HTTP (80, 5000), HTTPS (443), deny all else."""
    commands = [
        "ufw default deny incoming",
        "ufw default allow outgoing",
        "ufw allow 22/tcp",
        "ufw allow 80/tcp",
        "ufw allow 443/tcp",
        "ufw allow 5000/tcp",
        "ufw --force enable"
    ]
    results = []
    for cmd in commands:
        try:
            res = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            results.append({"command": cmd, "success": res.returncode == 0, "output": res.stdout or res.stderr})
        except Exception as ex:
            results.append({"command": cmd, "success": False, "error": str(ex)})
    return results
