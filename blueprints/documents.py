"""Documents blueprint — admin and employee document management."""
from flask import Blueprint

documents_bp = Blueprint("documents", __name__)

# ── Routes in this blueprint ──────────────────────────────────────────────────
# Source routes (app.py → documents_bp):
#
#   /documents                     → documents
#   /upload_document               → upload_document      (POST)
#   /delete_document/<did>         → delete_document      (POST)
#   /download_document/<did>       → download_document
#   /upload_my_document            → upload_my_document   (POST)
#   /delete_my_document/<did>      → delete_my_document   (POST)
#
# Key imports:
#   from utils.auth import admin_required, employee_required
#   from utils.helpers import _audit, _validate_upload
#   from database import get_db_connection
# ─────────────────────────────────────────────────────────────────────────────
