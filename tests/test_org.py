"""
Org blueprint tests — multi-tenant self-registration (/create_org).

_SIGNUP_SECRET is read from the environment once at module import time
(blueprints/org.py), not per-request, so these tests monkeypatch the
module attribute directly rather than the env var — the standard way to
test a value that's already been baked in at import time.

The full provisioning path creates a real Postgres schema via
create_tenant_schema() + init_tenant_db() (which runs the entire init_db()
schema bootstrap against it) — genuinely heavy, but this is exactly the
kind of "quiet until it silently breaks" flow worth one real end-to-end
test for, with explicit cleanup (DROP SCHEMA) after.

Run with:
    python -m pytest tests/test_org.py -v
"""
import pytest
import blueprints.org as org_module


@pytest.fixture
def signup_enabled():
    """Force _SIGNUP_SECRET on for the duration of a test, restoring the
    real value afterward so other tests see the environment as configured."""
    original = org_module._SIGNUP_SECRET
    org_module._SIGNUP_SECRET = "test-signup-secret-123"
    yield "test-signup-secret-123"
    org_module._SIGNUP_SECRET = original


@pytest.fixture
def signup_disabled():
    original = org_module._SIGNUP_SECRET
    org_module._SIGNUP_SECRET = ""
    yield
    org_module._SIGNUP_SECRET = original


def _drop_schema(db_engine, schema_name):
    cur = db_engine.cursor()
    cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    cur.execute("DELETE FROM att_master.tenants WHERE db_name=%s", (schema_name,))
    cur.close()


# ===========================================================================
# Signup-disabled path — the default in production unless SIGNUP_SECRET is
# explicitly configured. Security-critical: this must fail closed.
# ===========================================================================

class TestSignupDisabled:
    def test_get_page_shows_disabled(self, client, signup_disabled):
        resp = client.get("/create_org")
        assert resp.status_code == 200

    def test_post_rejected_even_with_no_secret_submitted(self, client, signup_disabled):
        resp = client.post("/create_org", data={}, follow_redirects=False)
        assert resp.status_code in (301, 302)

    def test_post_rejected_even_with_a_guessed_secret(self, client, signup_disabled):
        """Fail-closed check: an empty _SIGNUP_SECRET must reject every
        request, not just ones with a wrong-but-present secret field."""
        resp = client.post("/create_org", data={
            "signup_secret": "anything", "company_name": "X", "subdomain": "x",
            "admin_username": "a", "admin_password": "password123",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)


# ===========================================================================
# Signup-enabled — validation paths (no schema creation, fast)
# ===========================================================================

class TestSignupValidation:
    def test_get_page_shows_enabled(self, client, signup_enabled):
        resp = client.get("/create_org")
        assert resp.status_code == 200

    def test_wrong_secret_rejected(self, client, signup_enabled):
        resp = client.post("/create_org", data={
            "signup_secret": "wrong-secret", "company_name": "X", "subdomain": "x",
            "admin_username": "a", "admin_password": "password123",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)

    def test_missing_required_fields_rejected(self, client, signup_enabled):
        resp = client.post("/create_org", data={
            "signup_secret": signup_enabled, "company_name": "", "subdomain": "",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)

    def test_invalid_subdomain_format_rejected(self, client, signup_enabled):
        resp = client.post("/create_org", data={
            "signup_secret": signup_enabled, "company_name": "Acme",
            "subdomain": "Not Valid!", "admin_username": "admin",
            "admin_password": "password123",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)

    def test_short_password_rejected(self, client, signup_enabled):
        resp = client.post("/create_org", data={
            "signup_secret": signup_enabled, "company_name": "Acme",
            "subdomain": "acme-test", "admin_username": "admin",
            "admin_password": "short",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)


# ===========================================================================
# Full provisioning — real schema creation, one end-to-end test
# ===========================================================================

class TestFullProvisioning:
    def test_create_org_provisions_real_tenant_schema(self, client, db_engine, signup_enabled):
        from app import init_master_db
        init_master_db()

        subdomain = "e2e-test-org"
        schema_name = "att_" + subdomain.replace("-", "_")
        _drop_schema(db_engine, schema_name)
        try:
            resp = client.post("/create_org", data={
                "signup_secret": signup_enabled,
                "company_name": "E2E Test Org",
                "subdomain": subdomain,
                "admin_username": "e2e_admin",
                "admin_password": "password123",
                "admin_email": "e2e@test.local",
            }, follow_redirects=False)
            assert resp.status_code in (301, 302)
            assert resp.headers.get("Location", "").endswith("/admin_login")

            cur = db_engine.cursor()
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s",
                (schema_name,),
            )
            assert cur.fetchone() is not None, "tenant schema was not created"

            cur.execute("SELECT db_name, status FROM att_master.tenants WHERE subdomain=%s", (subdomain,))
            row = cur.fetchone()
            assert row is not None, "tenant was not registered in att_master.tenants"
            assert row[0] == schema_name
            assert row[1] == "active"

            cur.execute(f'SELECT username FROM "{schema_name}".admin_users WHERE username=%s', ("e2e_admin",))
            assert cur.fetchone() is not None, "admin user was not seeded into the new tenant schema"
            cur.close()
        finally:
            _drop_schema(db_engine, schema_name)

    def test_subdomain_colliding_with_master_registry_schema_rejected(self, client, db_engine, signup_enabled):
        # subdomain "master" derives db_name "att_master" — the tenant
        # registry schema itself. Previously this only checked the tenants
        # table (which has no row for "master"), so CREATE SCHEMA IF NOT
        # EXISTS would silently no-op and the flow would seed an
        # attacker-controlled admin account straight into the registry
        # schema. Must be rejected before any provisioning happens.
        from app import init_master_db
        init_master_db()

        resp = client.post("/create_org", data={
            "signup_secret": signup_enabled, "company_name": "Evil Org",
            "subdomain": "master", "admin_username": "evil_admin",
            "admin_password": "password123",
        }, follow_redirects=False)
        assert resp.status_code in (301, 302)
        assert resp.headers.get("Location") == "/create_org"

        # If the vulnerability were still present, the tenant-schema migration
        # would have run against att_master, creating an admin_users table
        # there (att_master normally only ever has `tenants`) and seeding
        # evil_admin into it.
        cur = db_engine.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='att_master' AND table_name='admin_users'"
        )
        polluted = cur.fetchone() is not None
        cur.close()
        assert not polluted, "tenant schema migration leaked into the master registry schema"

    def test_duplicate_subdomain_rejected(self, client, db_engine, signup_enabled):
        from app import init_master_db
        init_master_db()

        subdomain = "e2e-dup-org"
        schema_name = "att_" + subdomain.replace("-", "_")
        _drop_schema(db_engine, schema_name)
        try:
            payload = {
                "signup_secret": signup_enabled, "company_name": "Dup Org",
                "subdomain": subdomain, "admin_username": "dup_admin",
                "admin_password": "password123",
            }
            r1 = client.post("/create_org", data=payload, follow_redirects=False)
            assert r1.status_code in (301, 302)
            assert r1.headers.get("Location", "").endswith("/admin_login")

            r2 = client.post("/create_org", data=payload, follow_redirects=False)
            assert r2.status_code in (301, 302)
            assert r2.headers.get("Location") == "/create_org"
        finally:
            _drop_schema(db_engine, schema_name)
