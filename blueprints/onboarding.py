"""Onboarding blueprint — templates, tasks, offer letters, employee portal onboarding."""
from flask import Blueprint

onboarding_bp = Blueprint("onboarding", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → onboarding_bp):
#
#   /onboarding                         → onboarding
#   /onboarding_template_save           → onboarding_template_save    (POST)
#   /bulk_assign_onboarding             → bulk_assign_onboarding      (POST)
#   /export_onboarding_csv              → export_onboarding_csv
#   /onboarding_template_duplicate      → onboarding_template_duplicate (POST)
#   /onboarding_template_delete         → onboarding_template_delete  (POST)
#   /onboarding_task_save               → onboarding_task_save        (POST)
#   /onboarding_task_delete             → onboarding_task_delete      (POST)
#   /onboarding_template_detail/<tid>   → onboarding_template_detail
#   /onboarding_assign                  → onboarding_assign           (POST)
#   /onboarding_detail/<ob_id>          → onboarding_detail
#   /onboarding_admin_task_update       → onboarding_admin_task_update (POST)
#   /onboarding_close                   → onboarding_close            (POST)
#   /offer_letter/<ob_id>               → offer_letter
#   /offer_letter_save                  → offer_letter_save           (POST)
#   /offer_letter_view/<letter_id>      → offer_letter_view
#   /offer_letter_send/<letter_id>      → offer_letter_send           (POST)
#   /offer_letter_pdf/<token>           → offer_letter_pdf
#   /offer_letter_respond/<token>/<act> → offer_letter_respond
#   /my_onboarding                      → my_onboarding
#   /my_onboarding_task_done            → my_onboarding_task_done     (POST)
#
# Key imports:
#   from utils.auth import admin_required, employee_required
#   from utils.helpers import _audit, _create_notification
#   from utils.email_utils import send_email_smtp, send_email_async, get_email_config
#   import hashlib, secrets
#   from werkzeug.utils import secure_filename
# ─────────────────────────────────────────────────────────────────────────────
