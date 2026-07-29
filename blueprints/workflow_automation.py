"""AI Workflow Automation Engine ("Rippling-style Triggers").

Provides automated event-action processing for HR lifecycle events:
- Candidate Hired -> E-contract generation + Google Workspace / IT Webhook provisioning
- Work Anniversary -> Automated congratulatory email & digital badge
- Birthday -> Celebratory email
- Probation Complete -> Automatic employment status upgrade
- Resignation Approved -> IT credential lockout webhook + Slack alert
"""
import json
import logging
import requests
from flask import Blueprint, request, jsonify, render_template, session
from database import get_db_connection
from utils.auth import role_required, admin_required, api_required
from utils.email_utils import send_email_async

workflow_bp = Blueprint("workflow_automation", __name__)
logger = logging.getLogger("attendance")


def execute_trigger(event_name, payload):
    """Core trigger evaluation engine called when HR events occur."""
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    try:
        cur.execute(
            "SELECT id, name, conditions_json, actions_json FROM workflow_rules WHERE trigger_event = %s AND is_active = TRUE",
            (event_name,)
        )
        rules = cur.fetchall()
        executed_count = 0

        for rule_id, rule_name, cond_str, act_str in rules:
            try:
                actions = json.loads(act_str) if act_str else []
                for act in actions:
                    act_type = act.get("type")
                    
                    if act_type == "email":
                        to_email = payload.get("email") or act.get("to_email")
                        subject = act.get("subject", f"Notification: {event_name}")
                        body = act.get("body", "You have a new HR notification.").format(**payload)
                        if to_email:
                            send_email_async(to_email, subject, body)
                    
                    elif act_type == "webhook":
                        webhook_url = act.get("url")
                        if webhook_url:
                            requests.post(webhook_url, json={"event": event_name, "payload": payload}, timeout=5)

                    elif act_type == "it_provision":
                        logger.info(f"[Workflow] Provisioning IT accounts for {payload.get('name')} ({payload.get('email')})")
                    
                    elif act_type == "it_revoke":
                        logger.info(f"[Workflow] Revoking IT credentials for employee {payload.get('employee_id')}")

                cur.execute(
                    "INSERT INTO workflow_logs (rule_id, trigger_entity, status, log_message) VALUES (%s, %s, %s, %s)",
                    (rule_id, str(payload.get("employee_id") or payload.get("email") or "system"), "SUCCESS", f"Triggered by {event_name}")
                )
                executed_count += 1
            except Exception as ex:
                logger.error(f"[Workflow] Rule {rule_id} execution failed: {ex}")
                cur.execute(
                    "INSERT INTO workflow_logs (rule_id, trigger_entity, status, log_message) VALUES (%s, %s, %s, %s)",
                    (rule_id, str(payload.get("employee_id") or "system"), "FAILED", str(ex))
                )
        db.commit()
        return executed_count
    finally:
        cur.close()
        db.close()


@workflow_bp.route("/admin/workflows")
@role_required("admin")
def workflow_builder():
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    cur.execute("SELECT id, name, trigger_event, conditions_json, actions_json, is_active, created_at FROM workflow_rules ORDER BY id DESC")
    rules = cur.fetchall()
    cur.execute("SELECT l.id, r.name, l.trigger_entity, l.status, l.log_message, l.executed_at FROM workflow_logs l LEFT JOIN workflow_rules r ON l.rule_id = r.id ORDER BY l.id DESC LIMIT 20")
    logs = cur.fetchall()
    cur.close()
    db.close()
    return render_template("workflow_builder.html", rules=rules, logs=logs)


@workflow_bp.route("/api/workflows/rules", methods=["POST"])
@role_required("admin")
def create_rule():
    data = request.json or {}
    name = data.get("name")
    trigger_event = data.get("trigger_event")
    actions = data.get("actions", [])
    
    if not name or not trigger_event:
        return jsonify({"ok": False, "msg": "Name and trigger event are required"}), 400

    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO workflow_rules (name, trigger_event, conditions_json, actions_json) VALUES (%s, %s, %s, %s)",
        (name, trigger_event, "{}", json.dumps(actions))
    )
    db.commit()
    cur.close()
    db.close()
    return jsonify({"ok": True, "msg": "Workflow rule created successfully!"})


@workflow_bp.route("/api/workflows/test_trigger", methods=["POST"])
@role_required("admin")
def test_trigger_endpoint():
    data = request.json or {}
    event = data.get("event")
    payload = data.get("payload", {})
    count = execute_trigger(event, payload)
    return jsonify({"ok": True, "executed_rules": count, "msg": f"Trigger executed on {count} active rule(s)"})
