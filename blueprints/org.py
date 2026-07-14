"""Org blueprint — multi-tenant org provisioning, org chart."""
import datetime
import os
import secrets

from flask import (Blueprint, session, request, redirect, render_template,
                   flash, url_for, jsonify, abort)

from extensions import app_log
from database import get_db_connection
from utils.auth import admin_required, api_required, generate_password_hash
from utils.helpers import get_company_settings, _db, _audit

org_bp = Blueprint("org", __name__)


def init_master_db():
    """Create the att_master tenant-registry schema and its tenants table if
    they don't exist."""
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute('CREATE SCHEMA IF NOT EXISTS att_master')
        db.commit()
        cur.close(); db.close()

        from database import get_master_db
        db = get_master_db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(200) NOT NULL,
                subdomain VARCHAR(100) UNIQUE NOT NULL,
                db_name VARCHAR(100) UNIQUE NOT NULL,
                admin_email VARCHAR(200) DEFAULT NULL,
                plan VARCHAR(50) DEFAULT 'starter',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        cur.close()
        db.close()
    except Exception as _e:
        app_log.warning("init_master_db failed (non-fatal for single-tenant mode): %s", _e)


def init_tenant_db(schema_name: str):
    """Initialize schema in a freshly created tenant schema."""
    from flask import g as _g
    _g.tenant_db = schema_name
    init_db()


def sort_tree(node):
        node["children"].sort(key=lambda x: x["name"])
        for child in node["children"]:
            sort_tree(child)
        return node



@org_bp.route("/create_org", methods=["GET"])
def create_org_page():
    if not _SIGNUP_SECRET:
        # Provisioning disabled: no SIGNUP_SECRET configured in .env
        return render_template("create_org.html", signup_disabled=True)
    return render_template("create_org.html", signup_disabled=False)


@org_bp.route("/create_org", methods=["POST"])
def create_org():
    # Require a server-side secret token to prevent anonymous tenant creation.
    if not _SIGNUP_SECRET:
        flash("Organisation self-registration is disabled on this server.", "error")
        return redirect("/create_org")
    submitted_secret = request.form.get("signup_secret", "").strip()
    if not secrets.compare_digest(_SIGNUP_SECRET, submitted_secret):
        flash("Invalid signup code. Contact your administrator.", "error")
        return redirect("/create_org")

    company_name    = request.form.get("company_name", "").strip()
    subdomain       = request.form.get("subdomain", "").strip().lower()
    admin_username  = request.form.get("admin_username", "").strip()
    admin_password  = request.form.get("admin_password", "").strip()
    admin_email     = request.form.get("admin_email", "").strip() or None

    # Validate
    if not all([company_name, subdomain, admin_username, admin_password]):
        flash("All fields (company name, subdomain, admin username and password) are required.", "error")
        return redirect("/create_org")
    if not _SUBDOMAIN_RE.match(subdomain):
        flash("Subdomain may only contain lowercase letters, digits, and hyphens.", "error")
        return redirect("/create_org")
    if len(admin_password) < 8:
        flash("Admin password must be at least 8 characters.", "error")
        return redirect("/create_org")

    # Check subdomain not taken
    try:
        from database import get_master_db
        mconn = get_master_db()
        mcur  = mconn.cursor(buffered=True)
        mcur.execute("SELECT id FROM tenants WHERE subdomain=%s", (subdomain,))
        if mcur.fetchone():
            mcur.close(); mconn.close()
            flash(f"Subdomain '{subdomain}' is already taken. Choose another.", "error")
            return redirect("/create_org")
        mcur.close(); mconn.close()
    except Exception as exc:
        app_log.error("create_org subdomain check failed: %s", exc)
        flash("Could not check subdomain availability. Please try again.", "error")
        return redirect("/create_org")

    # Derive DB name
    db_name = "att_" + subdomain.replace("-", "_")

    try:
        from database import create_tenant_schema
        create_tenant_schema(db_name)
    except Exception as exc:
        app_log.error("create_org DB creation failed: %s", exc)
        flash("Failed to create organisation. Please contact support.", "error")
        return redirect("/create_org")

    try:
        from flask import g as _g
        _g.tenant_db = db_name
        init_tenant_db(db_name)
    except Exception as exc:
        app_log.error("create_org schema init failed: %s", exc)
        flash("Failed to initialise organisation schema. Please contact support.", "error")
        return redirect("/create_org")

    # Insert company settings and admin user into the new tenant DB
    try:
        from database import get_tenant_db
        tconn = get_tenant_db(db_name)
        tcur  = tconn.cursor()
        tcur.execute(
            "UPDATE company_settings SET company_name=%s, setup_done=1 WHERE id=1",
            (company_name,)
        )
        tcur.execute(
            "INSERT INTO admin_users (username, password, email) VALUES (%s, %s, %s)"
            " ON CONFLICT (username) DO UPDATE SET password=EXCLUDED.password",
            (admin_username, generate_password_hash(admin_password), admin_email)
        )
        tconn.commit()
        tcur.close(); tconn.close()
    except Exception as exc:
        flash(f"Failed to seed tenant data: {exc}", "error")
        return redirect("/create_org")

    # Register tenant in master DB
    try:
        from database import get_master_db
        mconn = get_master_db()
        mcur  = mconn.cursor()
        mcur.execute(
            "INSERT INTO tenants (company_name, subdomain, db_name, admin_email, status) "
            "VALUES (%s, %s, %s, %s, 'active')",
            (company_name, subdomain, db_name, admin_email)
        )
        mconn.commit()
        mcur.close(); mconn.close()
    except Exception as exc:
        flash(f"Tenant registered in DB but master registry failed: {exc}", "error")
        return redirect("/create_org")

    flash(f"Organisation '{company_name}' created! Subdomain: {subdomain}. You can now log in.", "success")
    return redirect("/admin_login")


@org_bp.route("/org_chart")
@admin_required
def org_chart_page():
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    active_cid = session.get("active_company_id")
    _co_sub = "AND employee_id IN (SELECT employee_id FROM employees WHERE company_id=%s)" if active_cid else ""
    _co_args = (active_cid,) if active_cid else ()
    cursor.execute(f"SELECT COUNT(*) FROM leave_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_leaves = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM resignation_requests WHERE status='Pending' {_co_sub}", _co_args)
    pending_resignations = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM tickets WHERE status='Open' {_co_sub}", _co_args)
    pending_tickets = cursor.fetchone()[0]
    if active_cid:
        cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != '' AND company_id=%s ORDER BY department", (active_cid,))
    else:
        cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != '' ORDER BY department")
    departments = [r[0] for r in cursor.fetchall()]
    co = get_company_settings()
    cursor.close(); db.close()
    return render_template("org_chart.html",
        co=co, departments=departments,
        pending_leaves=pending_leaves,
        pending_resignations=pending_resignations,
        pending_tickets=pending_tickets,
    
        active_nav="admin_tools",
    )


@org_bp.route("/api/org_chart_data")
@admin_required
def api_org_chart_data():
    dept_filter = request.args.get("dept", "")
    active_cid  = session.get("active_company_id")
    db = get_db_connection(); cursor = db.cursor()
    query = """
        SELECT e.employee_id, e.name, e.role, e.department,
               e.manager_id, e.face_image,
               COALESCE(e.manager_name, '') as manager_name
        FROM employees e
        WHERE COALESCE(e.is_active, 1) = 1
    """
    params = []
    if active_cid:
        query += " AND e.company_id = %s"
        params.append(active_cid)
    if dept_filter:
        query += " AND e.department = %s"
        params.append(dept_filter)
    query += " ORDER BY e.name"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close(); db.close()

    emp_map = {}
    for r in rows:
        emp_map[r[0]] = {
            "id":         r[0],
            "name":       r[1],
            "role":       r[2] or "Employee",
            "department": r[3] or "",
            "manager_id": r[4],
            "has_photo":  bool(r[5] and os.path.exists(r[5])),
            "children":   []
        }

    roots = []
    for emp in emp_map.values():
        mid = emp["manager_id"]
        if mid and mid in emp_map and mid != emp["id"]:
            emp_map[mid]["children"].append(emp)
        else:
            roots.append(emp)

    # Sort children alphabetically
    def sort_tree(node):
        node["children"].sort(key=lambda x: x["name"])
        for child in node["children"]:
            sort_tree(child)
        return node

    roots.sort(key=lambda x: x["name"])
    tree = [sort_tree(r) for r in roots]
    return jsonify({"ok": True, "tree": tree, "total": len(emp_map)})

