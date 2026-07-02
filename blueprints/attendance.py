"""Attendance blueprint — check-in/out, shifts, breaks, bulk actions."""
from flask import Blueprint

attendance_bp = Blueprint("attendance", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → attendance_bp):
#
#   /location                      → location            (POST)
#   /attendance                    → attendance           (POST)
#   /today_present                 → today_present
#   /today_absent                  → today_absent
#   /today_late                    → today_late
#   /admin_action                  → admin_action         (POST)
#   /correct_attendance            → correct_attendance   (POST)
#   /bulk_mark_attendance          → bulk_mark_attendance (GET/POST)
#   /employee_attendance_detail/<> → employee_attendance_detail
#   /monthly_report                → monthly_report
#   /monthly_report_export         → monthly_report_export
#   /send_absentee_report          → send_absentee_report (POST)
#   /shifts                        → shifts               (GET)
#   /add_shift                     → add_shift            (POST)
#   /delete_shift                  → delete_shift         (POST)
#   /edit_shift/<sid>              → edit_shift           (POST)
#   /bulk_assign_shift             → bulk_assign_shift    (POST)
#   /update_default_shift          → update_default_shift (POST)
#   /assign_shift                  → assign_shift         (POST)
#   /submit_shift_swap             → submit_shift_swap    (POST)
#   /respond_shift_swap/<req_id>   → respond_shift_swap   (POST)
#   /admin_shift_swap/<req_id>     → admin_shift_swap     (POST)
#   /admin_shift_swaps             → admin_shift_swaps
#   /api/breaks                    → api_breaks           (keep @limiter.limit)
#   /break_config                  → break_config
#   /add_break                     → add_break            (POST)
#   /update_break, /update_break/<bid> → update_break
#   /delete_break, /delete_break/<bid> → delete_break
#   /api/attendance/checkin        → api_checkin          (POST)
#   /api/shifts (GET/POST)         → api_shifts
#   /api/shifts/<sid> (DELETE)     → api_delete_shift
#   /api/shifts/assign             → api_assign_shift     (POST)
#
# Key imports:
#   from utils.auth import admin_required, employee_required, api_required
#   from utils.attendance_utils import (classify_by_worked_minutes, detect_overtime,
#       get_attendance_type, get_employee_shift, _td_to_time, get_working_days,
#       fetch_holidays_set, fetch_leave_map, infer_type_legacy)
#   from utils.helpers import _audit, get_co_features
#   import utils.config as cfg
# ─────────────────────────────────────────────────────────────────────────────
