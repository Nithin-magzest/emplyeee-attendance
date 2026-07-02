"""Performance blueprint — reviews, KPIs, hikes, bonuses."""
from flask import Blueprint

performance_bp = Blueprint("performance", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → performance_bp):
#
#   /performance                   → performance
#   /performance_review/<emp_id>   → performance_review   (GET)
#   /performance_save_review       → performance_save_review (POST)
#   /performance_add_kpi           → performance_add_kpi  (POST)
#   /performance_rate_kpi          → performance_rate_kpi (POST)
#   /performance_delete_kpi        → performance_delete_kpi (POST)
#   /my_performance                → my_performance
#   /performance_employee_comment  → performance_employee_comment (POST)
#   /performance_export            → performance_export
#   /performance_import            → performance_import   (POST)
#   /apply_hike                    → apply_hike           (POST)
#   /award_performance_bonus       → award_performance_bonus (POST)
#   /save_hike_config              → save_hike_config     (POST)
#
# Key imports:
#   from utils.auth import admin_required, employee_required, manager_or_admin_required
#   from utils.helpers import _audit, _create_notification
#   from utils.email_utils import send_email_async, get_email_config
# ─────────────────────────────────────────────────────────────────────────────
