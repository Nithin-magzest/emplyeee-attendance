"""Slack & Microsoft Teams HR Integration Blueprint."""
import requests
from flask import Blueprint, request, jsonify, render_template
from database import get_db_connection
from utils.auth import role_required

integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/api/integrations/send_notification", methods=["POST"])
@role_required("admin")
def send_bot_notification():
    data = request.json or {}
    platform = data.get("platform", "slack")
    webhook_url = data.get("webhook_url")
    message = data.get("message", "HRMS Alert: Action Required.")

    if not webhook_url:
        return jsonify({"ok": False, "msg": "Webhook URL is required"}), 400

    try:
        if platform == "slack":
            payload = {"text": f"🤖 *MagHR Premier Alert*\n{message}"}
        else:
            payload = {"text": message}

        res = requests.post(webhook_url, json=payload, timeout=5)
        return jsonify({"ok": True, "status_code": res.status_code, "msg": "Notification dispatched to bot!"})
    except Exception as ex:
        return jsonify({"ok": False, "msg": f"Failed to send bot notification: {ex}"}), 500
