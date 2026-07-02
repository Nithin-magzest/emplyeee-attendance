"""Admin views blueprint — dashboard, settings, companies, analytics, audit."""
from flask import Blueprint

admin_views_bp = Blueprint("admin_views", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → admin_views_bp):
#
#   /admin                         → admin (dashboard)
#   /api/dashboard_live            → dashboard_live
#   /api/attendance_chart_data     → attendance_chart_data
#   /settings                      → settings_page
#   /save_salary_rules             → save_salary_rules    (POST)
#   /save_default_onboarding_template→save_default_onboarding_template (POST)
#   /toggle_auth_method            → toggle_auth_method   (POST)
#   /toggle_fingerprint            → toggle_fingerprint   (POST)
#   /save_company_code             → save_company_code    (POST)
#   /save_company_info             → save_company_info    (POST)
#   /toggle_feature                → toggle_feature       (POST)
#   /save_geo_radius               → save_geo_radius      (POST)
#   /save_security_settings        → save_security_settings (POST)
#   /switch_company                → switch_company       (POST)
#   /clear_company                 → clear_company        (POST)
#   /set_company_pin               → set_company_pin      (POST)
#   /companies                     → view_companies
#   /companies/add                 → add_company          (POST)
#   /companies/<cid>/edit          → edit_company         (POST)
#   /companies/<cid>/delete        → delete_company       (POST)
#   /announcements                 → announcements_admin  (GET/POST)
#   /test_email                    → test_email           (POST)
#   /analytics                     → analytics
#   /audit_logs                    → audit_logs
#   /admin_tools                   → admin_tools
#   /api/org_chart_data            → api_org_chart_data
#   /org_chart                     → org_chart
#   /api/admin/expiring_documents  → api_admin_expiring_documents
#   /api/dashboard (via api_admin_bp normally)
#
# Key imports:
#   from utils.auth import admin_required, manager_or_admin_required, api_required
#   from utils.helpers import (_audit, get_company_settings, invalidate_settings_cache,
#       _upsert_co_feature, _upsert_co_features, get_co_features)
#   from utils.email_utils import send_email_smtp, get_email_config
#   from utils.config import load_default_shift, load_salary_rules
# ─────────────────────────────────────────────────────────────────────────────
