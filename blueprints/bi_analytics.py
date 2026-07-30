"""Executive BI Analytics & Custom Report Builder Blueprint."""
import json
from flask import Blueprint, request, jsonify, render_template, session
from database import get_db_connection
from utils.auth import role_required
from utils.analytics_automation import get_overall_executive_figures

bi_bp = Blueprint("bi_analytics", __name__)


@bi_bp.route("/admin/bi_analytics")
@role_required("admin")
def bi_dashboard():
    figures = get_overall_executive_figures()
    return render_template("analytics_suite.html", figures=figures)


@bi_bp.route("/api/bi/generate_report", methods=["POST"])
@role_required("admin")
def generate_report():
    data = request.json or {}
    title = data.get("title", "Custom HR Report")
    report_type = data.get("report_type", "turnover")
    
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO custom_bi_reports (title, report_type, config_json, created_by) VALUES (%s, %s, %s, %s)",
        (title, report_type, json.dumps(data.get("filters", {})), session.get("admin_username", "admin"))
    )
    db.commit()
    cur.close()
    db.close()
    return jsonify({"ok": True, "msg": f"Report '{title}' generated & saved!"})


@bi_bp.route("/api/analytics/summary")
@role_required("admin")
def api_analytics_summary():
    """API endpoint returning live JSON analytics figures."""
    figures = get_overall_executive_figures()
    return jsonify({"ok": True, "figures": figures})
