"""Health blueprint — /healthz and /favicon.ico.

Migrated from app.py (lines 132–151). These routes carry no business logic
and no auth requirements, so they're the cleanest starting point for the
blueprint split.
"""
import os
from flask import Blueprint, jsonify, send_from_directory, current_app
from database import get_db_connection
from extensions import app_log

health_bp = Blueprint("health", __name__)


@health_bp.route("/favicon.ico")
def favicon():
    static = current_app.static_folder
    ico = os.path.join(static, "favicon.ico")
    if os.path.exists(ico):
        return send_from_directory(static, "favicon.ico", mimetype="image/x-icon")
    return ("", 204)


@health_bp.route("/healthz")
def healthz():
    """Health check endpoint used by Podman, nginx, and load balancers."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        app_log.error("Health check DB error: %s", e)
        return jsonify({"status": "error", "db": "unavailable"}), 503


@health_bp.route("/readyz")
def readyz():
    """Readiness probe endpoint for Kubernetes / ALB target group health checks."""
    checks = {}
    ready = True

    # 1. Check Database connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
        tbl_cnt = cur.fetchone()[0]
        cur.close()
        conn.close()
        checks["database"] = {"status": "up", "tables": tbl_cnt}
    except Exception as e:
        ready = False
        checks["database"] = {"status": "down", "error": str(e)}

    # 2. Application readiness status
    checks["application"] = {"status": "ready" if ready else "degraded"}

    code = 200 if ready else 503
    return jsonify({
        "status": "ready" if ready else "unready",
        "checks": checks
    }), code

