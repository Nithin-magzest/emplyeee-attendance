"""GDPR & SOC 2 Compliance Vault Blueprint.

Provides GDPR data export, right-to-be-forgotten employee data anonymizer, and cryptographically hashed audit trails.
"""
import hashlib
import json
import datetime
from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from utils.auth import role_required

compliance_bp = Blueprint("compliance", __name__)


@compliance_bp.route("/api/compliance/gdpr_export/<emp_id>")
@role_required("admin")
def gdpr_export(emp_id):
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    cur.execute("SELECT employee_id, name, email, department, role FROM employees WHERE employee_id = %s", (emp_id,))
    emp = cur.fetchone()
    if not emp:
        cur.close(); db.close()
        return jsonify({"ok": False, "msg": "Employee not found"}), 404

    cur.execute("SELECT date, login_time, logout_time, status FROM attendance WHERE employee_id = %s LIMIT 100", (emp_id,))
    att = cur.fetchall()

    export_data = {
        "profile": {"id": emp[0], "name": emp[1], "email": emp[2], "dept": emp[3], "role": emp[4]},
        "attendance": att,
        "exported_at": str(datetime.datetime.now())
    }

    checksum = hashlib.sha256(json.dumps(export_data, default=str).encode()).hexdigest()
    cur.execute(
        "INSERT INTO compliance_gdpr_vault (request_type, employee_id, hash_checksum, performed_by) VALUES (%s, %s, %s, %s)",
        ("GDPR_DATA_EXPORT", emp_id, checksum, session.get("admin_username", "admin"))
    )
    db.commit()
    cur.close(); db.close()

    return jsonify({"ok": True, "checksum": checksum, "data": export_data})


@compliance_bp.route("/api/compliance/anonymize/<emp_id>", methods=["POST"])
@role_required("admin")
def gdpr_anonymize(emp_id):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "UPDATE employees SET name = %s, email = %s, phone = %s WHERE employee_id = %s",
        (f"Anonymized User {emp_id}", f"anonymized_{emp_id}@gdpr-vault.internal", "0000000000", emp_id)
    )
    cur.execute(
        "INSERT INTO compliance_gdpr_vault (request_type, employee_id, hash_checksum, performed_by) VALUES (%s, %s, %s, %s)",
        ("GDPR_RIGHT_TO_BE_FORGOTTEN", emp_id, "ANONYMIZED", session.get("admin_username", "admin"))
    )
    db.commit()
    cur.close(); db.close()
    return jsonify({"ok": True, "msg": f"Employee {emp_id} personal data anonymized per GDPR Right-to-be-Forgotten."})
