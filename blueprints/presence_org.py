"""Live Presence & Interactive Org Chart Directory Blueprint."""
import datetime
from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from utils.auth import employee_required

presence_org_bp = Blueprint("presence_org", __name__)


@presence_org_bp.route("/api/presence/heartbeat", methods=["POST"])
@employee_required
def presence_heartbeat():
    emp_id = session.get("emp_id")
    data = request.json or {}
    status = data.get("status", "Active")
    message = data.get("message", "")

    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        """INSERT INTO live_employee_presence (employee_id, status, custom_message, last_ping)
           VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
           ON CONFLICT (employee_id) DO UPDATE SET
           status=EXCLUDED.status, custom_message=EXCLUDED.custom_message, last_ping=CURRENT_TIMESTAMP""",
        (emp_id, status, message)
    )
    db.commit()
    cur.close(); db.close()
    return jsonify({"ok": True, "msg": "Presence updated"})


@presence_org_bp.route("/api/presence/live_directory")
def get_live_directory():
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    cur.execute(
        """SELECT e.employee_id, e.name, e.department, e.role, COALESCE(p.status, 'Offline'), COALESCE(p.custom_message, '')
           FROM employees e
           LEFT JOIN live_employee_presence p ON e.employee_id = p.employee_id
           ORDER BY e.name"""
    )
    employees = cur.fetchall()
    cur.close(); db.close()

    directory = []
    for emp in employees:
        directory.append({
            "employee_id": emp[0],
            "name": emp[1],
            "department": emp[2],
            "role": emp[3],
            "status": emp[4],
            "custom_message": emp[5]
        })

    return jsonify({"ok": True, "directory": directory})
