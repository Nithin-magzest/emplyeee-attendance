"""Notifications blueprint — in-app notification feeds.

Migrated from app.py (lines 13255–13354). Routes:
  GET  /api/notifications                    → api_get_notifications         (admin, Bearer)
  POST /api/notifications/mark_read          → api_mark_notifications_read   (admin, Bearer)
  GET  /api/employee/notifications           → api_employee_get_notifications (employee, Bearer)
  POST /api/employee/notifications/mark_read → api_employee_mark_notifications_read (employee, Bearer)
  POST /web/notifications/mark_read          → web_employee_mark_notifications_read (employee, session)
  GET  /web/notifications/list               → web_employee_notifications_list      (employee, session)
"""
from flask import Blueprint, jsonify, session, g as _g
from database import get_db_connection
from utils.auth import api_required, employee_api_required, employee_required

notifications_bp = Blueprint("notifications", __name__)


def _fmt(row):
    return {
        "id": row[0],
        "title": row[1],
        "message": row[2],
        "is_read": bool(row[3]),
        "created_at": row[4].strftime("%d %b %Y, %I:%M %p") if row[4] else "",
    }


# ── Admin notifications (Bearer-token API) ────────────────────────────────────

@notifications_bp.route("/api/notifications", methods=["GET"])
@api_required
def api_get_notifications():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='admin' ORDER BY created_at DESC LIMIT 50"
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "notifications": [_fmt(r) for r in rows]})


@notifications_bp.route("/api/notifications/mark_read", methods=["POST"])
@api_required
def api_mark_notifications_read():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read=TRUE WHERE recipient_type='admin'")
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"ok": True})


# ── Employee notifications (Bearer-token API) ─────────────────────────────────

@notifications_bp.route("/api/employee/notifications", methods=["GET"])
@employee_api_required
def api_employee_get_notifications():
    emp_id = _g.api_emp_id
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='employee' AND employee_id=%s ORDER BY created_at DESC LIMIT 50",
        (emp_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "notifications": [_fmt(r) for r in rows]})


@notifications_bp.route("/api/employee/notifications/mark_read", methods=["POST"])
@employee_api_required
def api_employee_mark_notifications_read():
    emp_id = _g.api_emp_id
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=TRUE WHERE recipient_type='employee' AND employee_id=%s",
        (emp_id,),
    )
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"ok": True})


# ── Employee notifications (session-based web) ────────────────────────────────

@notifications_bp.route("/web/notifications/mark_read", methods=["POST"])
@employee_required
def web_employee_mark_notifications_read():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=TRUE WHERE recipient_type='employee' AND employee_id=%s",
        (emp_id,),
    )
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"ok": True})


@notifications_bp.route("/web/notifications/list")
@employee_required
def web_employee_notifications_list():
    emp_id = session["employee_id"]
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT id, title, message, is_read, created_at FROM notifications "
        "WHERE recipient_type='employee' AND employee_id=%s ORDER BY created_at DESC LIMIT 30",
        (emp_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({"ok": True, "notifications": [_fmt(r) for r in rows]})


# ── Web Admin & SecOps Notifications ───────────────────────────────────────────

@notifications_bp.route("/web/admin/notifications")
def web_admin_notifications():
    """Fetch live HR notifications for Admin header bell dropdown."""
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    items = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        # Fetch DB notifications for admin
        cur.execute(
            "SELECT id, title, message, is_read, created_at FROM notifications "
            "WHERE recipient_type='admin' ORDER BY created_at DESC LIMIT 15"
        )
        for r in cur.fetchall():
            items.append(_fmt(r))

        # Check pending HR items
        cur.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'")
        p_leave = cur.fetchone()[0] or 0
        if p_leave > 0:
            items.insert(0, {
                "id": 901,
                "title": "Pending Leave Requests",
                "message": f"{p_leave} employee leave request(s) awaiting approval.",
                "is_read": False,
                "created_at": "Just now"
            })

        cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
        p_tickets = cur.fetchone()[0] or 0
        if p_tickets > 0:
            items.insert(0, {
                "id": 902,
                "title": "Open Support Tickets",
                "message": f"{p_tickets} support ticket(s) requiring attention.",
                "is_read": False,
                "created_at": "Just now"
            })

        cur.close()
        db.close()
    except Exception as e:
        pass

    unread_cnt = sum(1 for i in items if not i.get("is_read"))
    return jsonify({"ok": True, "notifications": items, "unread_count": unread_cnt})


@notifications_bp.route("/web/admin/notifications/mark_read", methods=["POST"])
def web_admin_mark_read():
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("UPDATE notifications SET is_read=TRUE WHERE recipient_type='admin'")
        db.commit()
        cur.close()
        db.close()
    except Exception:
        pass
    return jsonify({"ok": True})


@notifications_bp.route("/web/secops/notifications")
def web_secops_notifications():
    """Fetch live Security threat notifications for SecOps Analyst header bell dropdown."""
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    items = []
    try:
        db = get_db_connection()
        cur = db.cursor(buffered=True)
        # Fetch critical security events
        cur.execute(
            "SELECT id, event_type, message, level, created_at FROM security_events "
            "ORDER BY created_at DESC LIMIT 10"
        )
        for r in cur.fetchall():
            items.append({
                "id": r[0],
                "title": f"[{r[3]}] {r[1]}",
                "message": r[2],
                "is_read": False,
                "created_at": str(r[4]) if r[4] else "Recent"
            })

        cur.execute("SELECT COUNT(*) FROM quarantined_files WHERE status='Quarantined'")
        q_count = cur.fetchone()[0] or 0
        if q_count > 0:
            items.insert(0, {
                "id": 801,
                "title": "🛡️ Malware Quarantine Alert",
                "message": f"{q_count} malicious payload(s) currently held in quarantine queue.",
                "is_read": False,
                "created_at": "Active"
            })

        cur.close()
        db.close()
    except Exception:
        pass

    if not items:
        items = [{
            "id": 800,
            "title": "System Secure",
            "message": "All security systems operational — 0 active threats.",
            "is_read": True,
            "created_at": "Now"
        }]

    unread_cnt = sum(1 for i in items if not i.get("is_read"))
    return jsonify({"ok": True, "notifications": items, "unread_count": unread_cnt})


@notifications_bp.route("/web/secops/notifications/mark_read", methods=["POST"])
def web_secops_mark_read():
    if not session.get("admin_logged_in"):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    return jsonify({"ok": True})

