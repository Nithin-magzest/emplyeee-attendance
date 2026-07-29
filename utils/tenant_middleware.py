"""Cloud Subdomain & Tenant Routing Middleware.

Resolves tenant organization from HTTP Host header (e.g. acme.maghr.cloud -> tenant_acme)
and dynamically switches PostgreSQL search_path for schema-per-tenant isolation.
"""
import re
import logging
from flask import request, g
from database import get_db_connection

logger = logging.getLogger("attendance")


def resolve_tenant_from_request():
    """Extracts tenant slug from Host header or Query parameter."""
    host = request.headers.get("Host", "").split(":")[0]
    
    # Check for subdomain pattern (e.g. acme.maghr.cloud or acme.localhost)
    parts = host.split(".")
    if len(parts) >= 3 and parts[0] not in ("www", "app", "api", "localhost"):
        tenant_slug = parts[0].lower()
    else:
        tenant_slug = request.args.get("tenant") or request.headers.get("X-Tenant-ID", "public")

    # Sanitize tenant slug for PostgreSQL schema name safety
    tenant_slug = re.sub(r'[^a-zA-Z0-9_]', '', tenant_slug) or "public"
    schema_name = f"tenant_{tenant_slug}" if tenant_slug != "public" else "public"
    
    g.tenant_slug = tenant_slug
    g.tenant_schema = schema_name
    return schema_name


def set_request_tenant_schema():
    """Flask before_request hook to apply search_path to the active request context."""
    schema = resolve_tenant_from_request()
    if schema != "public":
        try:
            db = get_db_connection()
            cur = db.cursor()
            cur.execute(f'SET search_path TO "{schema}", public')
            cur.close()
            db.close()
        except Exception as ex:
            logger.warning(f"[TenantMiddleware] Could not switch to schema {schema}: {ex}")
