"""Employee portal blueprint — self-service: profile, payslips, QR, attendance PDF."""
from flask import Blueprint

employee_portal_bp = Blueprint("employee_portal", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → employee_portal_bp):
#
#   /employee_portal               → employee_portal
#   /update_my_profile             → update_my_profile    (POST)
#   /update_my_bank_details        → update_my_bank_details (POST)
#   /add_experience                → add_experience        (POST)
#   /delete_experience/<entry_id>  → delete_experience    (POST)
#   /add_education_entry           → add_education_entry  (POST)
#   /delete_education_entry/<id>   → delete_education_entry (POST)
#   /update_my_photo               → update_my_photo      (POST)
#   /my_qr                         → my_qr
#   /my_id_card                    → my_id_card
#   /my_payslip_summary/<y>/<m>    → my_payslip_summary
#   /my_attendance_pdf             → my_attendance_pdf
#   /api/employee/portal (GET)     → api_employee_portal
#   /api/employee/change-password  → api_employee_change_password (POST)
#   /api/employee/profile (GET)    → api_employee_profile
#   /api/employee/photo (POST)     → api_employee_photo
#   /api/employee/salary (GET)     → api_employee_salary
#   /api/employee/attendance (GET) → api_employee_attendance
#   /api/employee/auth-config (GET)→ api_employee_auth_config
#   /api/employee/checkin (POST)   → api_employee_checkin
#   /api/employee/sync_punches     → api_employee_sync_punches (POST)
#   /api/employee/qr-face-checkin  → api_employee_qr_face_checkin (POST, @limiter)
#
# Key imports:
#   from utils.auth import employee_required, employee_api_required
#   from utils.helpers import _audit, _create_notification, _validate_image_file
#   from utils.email_utils import send_email_async, get_email_config
#   from utils.attendance_utils import (get_attendance_type, get_employee_shift,
#       classify_by_worked_minutes, detect_overtime, infer_type_legacy)
#   from utils.helpers import get_auth_config, get_co_features
#   import utils.config as cfg
# ─────────────────────────────────────────────────────────────────────────────
