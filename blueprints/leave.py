"""Leave blueprint — requests, types, holidays, resignation, overtime, comp-off."""
from flask import Blueprint

leave_bp = Blueprint("leave", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → leave_bp):
#
#   /admin_leave_types             → admin_leave_types    (GET/POST)
#   /leave_requests                → leave_requests
#   /leave_action/<lid>            → leave_action         (POST)
#   /bulk_leave_action             → bulk_leave_action    (POST)
#   /leave_balance                 → leave_balance
#   /set_leave_balance             → set_leave_balance    (POST)
#   /leave_holidays                → leave_holidays
#   /leave_calendar                → leave_calendar
#   /request_leave                 → request_leave        (POST)
#   /cancel_leave/<lid>            → cancel_leave         (POST)
#   /view_holidays                 → view_holidays
#   /add_holiday                   → add_holiday          (POST)
#   /delete_holiday/<hid>          → delete_holiday       (POST)
#   /import_indian_holidays        → import_indian_holidays (POST)
#   /request_resignation           → request_resignation  (POST)
#   /resignation_requests          → resignation_requests
#   /resignation_action/<rid>      → resignation_action   (POST)
#   /overtime                      → overtime
#   /overtime_action/<oid>         → overtime_action      (POST)
#   /compoff                       → compoff
#   /compoff_old                   → compoff_old
#   /compoff_settings              → compoff_settings     (POST)
#   /my_compoff                    → my_compoff
#   /api/leave_requests (GET)      → api_leave_requests
#   /api/leave_requests/<lid>/action→ api_leave_action    (POST)
#   /api/resignation_requests (GET)→ api_resignation_requests
#   /api/resignation_requests/<rid>/action→api_resignation_action (POST)
#   /api/employee/leave_request    → api_employee_leave_request (POST)
#   /api/employee/resign           → api_employee_resign   (POST)
#   /api/employee/leaves           → api_employee_leaves   (GET)
#   /api/employee/cancel_leave/<lid>→api_employee_cancel_leave (POST)
#   /api/employee/request_overtime → api_employee_request_overtime (POST)
#   /api/employee/my_overtime      → api_employee_my_overtime (GET)
#   /api/employee/holidays         → api_employee_holidays (GET)
#   /api/holidays (GET/POST)       → api_holidays
#
# Key imports:
#   from utils.auth import (admin_required, employee_required,
#       manager_or_admin_required, api_required, employee_api_required)
#   from utils.helpers import _audit, _create_notification, get_co_features
#   from utils.email_utils import send_email_async, get_email_config, get_admin_emails
# ─────────────────────────────────────────────────────────────────────────────
