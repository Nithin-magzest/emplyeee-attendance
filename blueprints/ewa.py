"""Earned Wage Access (EWA) & On-Demand Pay Blueprint.

Allows employees to view accrued earnings mid-month and request salary advances.
Automatically integrates with payroll to deduct approved advances during payslip processing.
"""
import datetime
import calendar
from flask import Blueprint, request, jsonify, render_template, session
from database import get_db_connection
from utils.auth import role_required, employee_required

ewa_bp = Blueprint("ewa", __name__)


def calculate_accrued_salary(emp_id):
    """Calculates available mid-month earned salary."""
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    today = datetime.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    
    cur.execute("SELECT salary_per_day FROM salary_config WHERE employee_id = %s", (emp_id,))
    row = cur.fetchone()
    daily_rate = float(row[0]) if row and row[0] else 0.0

    # Count present days this month
    start_str = today.replace(day=1).strftime("%Y-%m-%d")
    cur.execute(
        "SELECT COUNT(*) FROM attendance WHERE employee_id = %s AND date >= %s AND status IN ('Full Day Login', 'Completed', 'Late Login')",
        (emp_id, start_str)
    )
    worked_days = cur.fetchone()[0] or 0

    # Calculate total advances already drawn this month
    cur.execute(
        "SELECT COALESCE(SUM(requested_amount), 0) FROM salary_advances WHERE employee_id = %s AND status IN ('approved', 'pending') AND requested_at >= %s",
        (emp_id, start_str)
    )
    drawn_amount = float(cur.fetchone()[0] or 0.0)

    earned = worked_days * daily_rate
    available = max(0.0, (earned * 0.70) - drawn_amount)  # Max 70% drawdown policy

    cur.close()
    db.close()
    return {
        "worked_days": worked_days,
        "daily_rate": daily_rate,
        "earned_so_far": round(earned, 2),
        "drawn_amount": round(drawn_amount, 2),
        "available_advance": round(available, 2)
    }


@ewa_bp.route("/api/ewa/accrued", methods=["GET"])
@employee_required
def get_accrued_advance():
    emp_id = session.get("emp_id")
    data = calculate_accrued_salary(emp_id)
    return jsonify({"ok": True, "data": data})


@ewa_bp.route("/api/ewa/request", methods=["POST"])
@employee_required
def request_salary_advance():
    emp_id = session.get("emp_id")
    req_data = request.json or {}
    amount = float(req_data.get("amount", 0))

    accrual = calculate_accrued_salary(emp_id)
    if amount <= 0 or amount > accrual["available_advance"]:
        return jsonify({"ok": False, "msg": f"Invalid amount. Maximum available for advance is ₹{accrual['available_advance']}"}), 400

    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO salary_advances (employee_id, requested_amount, accrued_amount, status) VALUES (%s, %s, %s, 'pending')",
        (emp_id, amount, accrual["earned_so_far"])
    )
    db.commit()
    cur.close()
    db.close()
    return jsonify({"ok": True, "msg": f"Salary advance request of ₹{amount} submitted for approval!"})


@ewa_bp.route("/api/ewa/admin_list", methods=["GET"])
@role_required("admin")
def list_advances():
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    cur.execute(
        "SELECT a.id, a.employee_id, e.name, a.requested_amount, a.accrued_amount, a.status, a.requested_at FROM salary_advances a JOIN employees e ON a.employee_id = e.employee_id ORDER BY a.id DESC"
    )
    advances = cur.fetchall()
    cur.close()
    db.close()
    return jsonify({"ok": True, "advances": advances})


@ewa_bp.route("/api/ewa/approve/<int:adv_id>", methods=["POST"])
@role_required("admin")
def approve_advance(adv_id):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "UPDATE salary_advances SET status = 'approved', approved_at = CURRENT_TIMESTAMP, payout_ref = %s WHERE id = %s",
        (f"PAYOUT-EWA-{adv_id}", adv_id)
    )
    db.commit()
    cur.close()
    db.close()
    return jsonify({"ok": True, "msg": "Salary advance approved & payout initiated!"})
