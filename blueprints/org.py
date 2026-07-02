"""Org blueprint — multi-tenant org creation."""
from flask import Blueprint

org_bp = Blueprint("org", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → org_bp):
#
#   /create_org (GET)              → create_org_form
#   /create_org (POST)             → create_org
#
# Key imports:
#   from database import create_tenant_database, get_master_db
#   from extensions import app_log
# ─────────────────────────────────────────────────────────────────────────────
