"""Employees blueprint — CRUD, photos, QR codes, ID cards."""
from flask import Blueprint

employees_bp = Blueprint("employees", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → employees_bp):
#
#   /employees                     → view_employees
#   /employee_profile/<emp_id>     → employee_profile
#   /employee_detail/<emp_id>      → employee_detail
#   /add_employee_page             → add_employee_page    (POST)
#   /edit_employee_page/<emp_id>   → edit_employee_page   (GET)
#   /edit_employee                 → edit_employee        (POST)
#   /delete_employee/<emp_id>      → delete_employee      (POST)
#   /update_employee_photo/<emp_id>→ update_employee_photo (POST)
#   /regenerate_qr/<emp_id>        → regenerate_qr        (POST)
#   /view_qrcodes                  → view_qrcodes
#   /view_photos                   → view_photos
#   /update_photo/<emp_id>         → update_photo         (POST)
#   /my_photo                      → my_photo
#   /dataset/<path:filename>       → serve_dataset
#   /admin_id_card/<emp_id>        → admin_id_card
#   /admin_view_id_card/<emp_id>   → admin_view_id_card
#   /api/employee_info/<emp_id>    → api_employee_info
#   /api/generate_emp_id           → api_generate_emp_id
#   /api/employees  (GET)          → api_employees_list
#   /api/employees  (POST)         → api_add_employee
#   /api/employees/<emp_id> (GET)  → api_employee_detail
#   /api/employees/<emp_id> (PUT)  → api_update_employee
#   /api/employees/<emp_id> (DELETE)→ api_delete_employee
#
# Key imports:
#   from utils.auth import admin_required, employee_required, api_required
#   from utils.helpers import _audit, _validate_image_file, _validate_upload
#   from qr_generator import generate_qr
#   from database import get_db_connection
# ─────────────────────────────────────────────────────────────────────────────
