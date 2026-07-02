"""Notifications blueprint — in-app notification feeds."""
from flask import Blueprint

notifications_bp = Blueprint("notifications", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → notifications_bp):
#
#   /api/notifications (GET)           → api_notifications
#   /api/notifications/mark_read       → api_notifications_mark_read (POST)
#   /api/employee/notifications (GET)  → api_employee_notifications
#   /api/employee/notifications/mark_read→api_employee_notifications_mark_read (POST)
#   /web/notifications/mark_read       → web_notifications_mark_read (POST)
#   /web/notifications/list            → web_notifications_list
#
# Key imports:
#   from utils.auth import (admin_required, employee_required,
#       api_required, employee_api_required)
#   from database import get_db_connection
# ─────────────────────────────────────────────────────────────────────────────
