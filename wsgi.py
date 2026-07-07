"""
Application factory entry point for the refactored blueprint structure.

Usage:
  gunicorn wsgi:application          # production
  python wsgi.py                     # local dev (SSL-aware)

Migration status
----------------
The blueprint split is in progress. Routes are being moved from app.py
(monolith) into blueprints/ incrementally. Each blueprint file documents
exactly which routes belong there and the imports each route needs.

Current state:
  ✅ extensions.py    — Flask app + limiter (shared by all blueprints)
  ✅ utils/config.py  — shift/salary runtime constants
  ✅ utils/helpers.py — audit, cache, encryption, validation, notifications
  ✅ utils/auth.py    — decorators, lockout, password hashing
  ✅ utils/email_utils.py     — SMTP + DB-backed queue worker
  ✅ utils/attendance_utils.py— attendance calculations
  🔄 blueprints/*.py  — route stubs with full migration instructions
  🔄 app.py           — still contains all routes (being drained into blueprints)

To migrate a route from app.py into its blueprint:
  1. Copy the route function from app.py to the blueprint file
  2. Change @app.route → @<name>_bp.route
  3. Update imports at top of blueprint file (see each file's Key imports section)
  4. Delete the route from app.py
  5. Run: python -m py_compile app.py && python -m py_compile blueprints/<file>.py
"""
import os
import sys

# ── Encoding fix for Windows ──────────────────────────────────────────────────
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv()

# ── Import shared extensions FIRST (no side-effects) ─────────────────────────
from extensions import app, app_log  # noqa: F401
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ── Start the email queue worker ──────────────────────────────────────────────
import threading
from utils.email_utils import _email_queue_worker
threading.Thread(target=_email_queue_worker, daemon=True, name="email-queue-worker").start()

# ── Register blueprints (uncomment as routes are migrated from app.py) ────────
#
# Migration status:
#   ✅ health.py          — /healthz, /favicon.ico
#   ✅ notifications.py   — /api/notifications/*, /web/notifications/*
#   🔄 auth.py            — login, logout, password reset, WebAuthn
#   🔄 employees.py       — employee CRUD, photos, QR, ID cards
#   🔄 attendance.py      — check-in/out, face recognition, QR scan
#   🔄 payroll.py         — salary, payslips, reports, export
#   🔄 leave.py           — leave requests, approval, holidays
#   🔄 tickets.py         — support tickets
#   🔄 admin_views.py     — admin dashboard, settings, companies
#   🔄 performance.py     — KPIs, reviews, hike/bonus
#   🔄 onboarding.py      — onboarding templates and tasks
#   🔄 documents.py       — employee document management
#   🔄 org.py             — multi-tenant org provisioning
#   🔄 employee_portal.py — employee self-service portal

# ✅ Migrated blueprints
from blueprints.health import health_bp
from blueprints.notifications import notifications_bp

app.register_blueprint(health_bp)
app.register_blueprint(notifications_bp)

# 🔄 Pending migration (routes still served from app.py below)
# from blueprints.auth import auth_bp
# from blueprints.employees import employees_bp
# from blueprints.attendance import attendance_bp
# from blueprints.payroll import payroll_bp
# from blueprints.leave import leave_bp
# from blueprints.tickets import tickets_bp
# from blueprints.admin_views import admin_views_bp
# from blueprints.performance import performance_bp
# from blueprints.onboarding import onboarding_bp
# from blueprints.documents import documents_bp
# from blueprints.org import org_bp
# from blueprints.employee_portal import employee_portal_bp
#
# app.register_blueprint(auth_bp)
# app.register_blueprint(employees_bp)
# app.register_blueprint(attendance_bp)
# app.register_blueprint(payroll_bp)
# app.register_blueprint(leave_bp)
# app.register_blueprint(tickets_bp)
# app.register_blueprint(admin_views_bp)
# app.register_blueprint(performance_bp)
# app.register_blueprint(onboarding_bp)
# app.register_blueprint(documents_bp)
# app.register_blueprint(org_bp)
# app.register_blueprint(employee_portal_bp)

# ── Load all existing routes from monolithic app.py (transitional) ────────────
import app as _app_module  # noqa: F401 — registers all @app.route decorators

# ── Startup DB init ───────────────────────────────────────────────────────────
with app.app_context():
    try:
        from app import init_master_db, init_db, load_default_shift, load_salary_rules
        init_master_db()
        init_db()
        load_default_shift()
        load_salary_rules()
    except Exception as _e:
        app_log.warning("Startup init failed (non-fatal): %s", _e)

# ── WSGI export ───────────────────────────────────────────────────────────────
application = app   # gunicorn / uWSGI entry point

if __name__ == "__main__":
    import os as _os
    _cert = _os.environ.get("SSL_CERT_PATH") or _os.path.join(_os.path.dirname(__file__), "cert.pem")
    _key  = _os.environ.get("SSL_KEY_PATH")  or _os.path.join(_os.path.dirname(__file__), "key.pem")
    if _os.path.exists(_cert) and _os.path.exists(_key):
        print("SSL cert found — starting on https://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False,
                ssl_context=(_cert, _key))
    else:
        print("No cert.pem / key.pem — starting on http://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
