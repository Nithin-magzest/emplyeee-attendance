"""Multi-Tenant White-Labeling & Subdomain Customization Blueprint."""
from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from utils.auth import role_required

whitelabel_bp = Blueprint("whitelabel", __name__)


@whitelabel_bp.route("/api/whitelabel/config", methods=["GET", "POST"])
@role_required("admin")
def whitelabel_config():
    db = get_db_connection()
    cur = db.cursor(buffered=True)
    tenant_id = session.get("active_company_id") or "default"

    if request.method == "POST":
        data = request.json or {}
        brand_name = data.get("brand_name", "MagHR Premier")
        logo_url = data.get("logo_url", "")
        primary_color = data.get("primary_color", "#4f46e5")
        custom_domain = data.get("custom_domain", "")

        cur.execute(
            """INSERT INTO tenant_whitelabel (tenant_id, brand_name, logo_url, primary_color, custom_domain)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET 
               brand_name=EXCLUDED.brand_name, logo_url=EXCLUDED.logo_url, primary_color=EXCLUDED.primary_color, custom_domain=EXCLUDED.custom_domain""",
            (tenant_id, brand_name, logo_url, primary_color, custom_domain)
        )
        db.commit()
        cur.close()
        db.close()
        return jsonify({"ok": True, "msg": "White-label branding updated!"})

    cur.execute("SELECT brand_name, logo_url, primary_color, custom_domain FROM tenant_whitelabel WHERE tenant_id = %s", (tenant_id,))
    row = cur.fetchone()
    cur.close()
    db.close()
    
    if row:
        config = {"brand_name": row[0], "logo_url": row[1], "primary_color": row[2], "custom_domain": row[3]}
    else:
        config = {"brand_name": "MagHR Premier", "logo_url": "", "primary_color": "#4f46e5", "custom_domain": ""}
        
    return jsonify({"ok": True, "config": config})
