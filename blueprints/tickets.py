"""Tickets blueprint — support ticket lifecycle."""
from flask import Blueprint

tickets_bp = Blueprint("tickets", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → tickets_bp):
#
#   /raise_ticket                  → raise_ticket         (POST)
#   /tickets                       → tickets_page
#   /ticket_action/<tid>           → ticket_action        (POST)
#   /api/tickets (GET)             → api_tickets_list
#   /api/tickets/<tid>/action      → api_ticket_action    (POST)
#   /api/employee/tickets (GET)    → api_employee_tickets
#   /api/employee/raise_ticket     → api_employee_raise_ticket (POST)
#
# Key imports:
#   from utils.auth import (admin_required, employee_required,
#       manager_or_admin_required, api_required, employee_api_required)
#   from utils.helpers import _audit, _create_notification
#   from utils.email_utils import send_email_async, get_email_config
# ─────────────────────────────────────────────────────────────────────────────
