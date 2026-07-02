"""Payroll blueprint — salary, payslips, payroll settings, reports."""
from flask import Blueprint

payroll_bp = Blueprint("payroll", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → payroll_bp):
#
#   /view_salary                   → view_salary
#   /update_salary                 → update_salary        (POST)
#   /salary_report                 → salary_report
#   /salary_report_export          → salary_report_export
#   /email_config                  → email_config         (GET/POST)
#   /send_salary_email             → send_salary_email    (POST)
#   /send_all_salary_emails        → send_all_salary_emails (POST)
#   /lock_payroll                  → lock_payroll         (POST)
#   /unlock_payroll                → unlock_payroll       (POST)
#   /view_payslip/<emp_id>/<y>/<m> → view_payslip
#   /download_payslip/<>/<y>/<m>   → download_payslip
#   /admin_payslips                → admin_payslips
#   /payroll_settings              → payroll_settings     (GET/POST)
#   /my_payslip_summary/<y>/<m>    → my_payslip_summary
#   /my_attendance_pdf             → my_attendance_pdf
#   /api/salary_config (GET/POST)  → api_salary_config
#   /api/monthly_report            → api_monthly_report
#   /api/salary_report             → api_salary_report
#   /api/email_config (GET/POST)   → api_email_config
#   /api/send_salary_email         → api_send_salary_email (POST)
#   /apply_hike                    → apply_hike           (POST)
#   /award_performance_bonus       → award_performance_bonus (POST)
#   /save_hike_config              → save_hike_config     (POST)
#
# Key imports:
#   from utils.auth import admin_required, employee_required, api_required
#   from utils.helpers import _audit, get_co_features
#   from utils.email_utils import (send_email_smtp, send_email_async,
#       get_email_config, get_admin_emails)
#   from utils.attendance_utils import (compute_salary_entry — lives in salary_utils)
#   # Note: build_salary_slip_html and compute_salary_entry stay in app.py
#   # until extracted to utils/salary_utils.py
# ─────────────────────────────────────────────────────────────────────────────
