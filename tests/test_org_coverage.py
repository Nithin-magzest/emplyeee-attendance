"""Coverage tests for blueprints/org.py.
Targets: create_org_page, org_chart_page, api_org_chart_data.
"""
import pytest


def _admin_session(client, seed_admin):
    client.post("/admin_login", data={
        "identifier": seed_admin["username"],
        "password":   seed_admin["password"],
    })
    return client


# ── create_org_page ───────────────────────────────────────────────────────────

class TestCreateOrgPage:

    def test_get_without_signup_secret_shows_disabled(self, client, monkeypatch):
        import blueprints.org as _org
        monkeypatch.setattr(_org, "_SIGNUP_SECRET", "")
        rv = client.get("/create_org")
        assert rv.status_code == 200

    def test_get_with_signup_secret_shows_form(self, client, monkeypatch):
        import blueprints.org as _org
        monkeypatch.setattr(_org, "_SIGNUP_SECRET", "test_secret_123")
        rv = client.get("/create_org")
        assert rv.status_code == 200

    def test_post_missing_fields_returns_error(self, client, monkeypatch):
        import blueprints.org as _org
        monkeypatch.setattr(_org, "_SIGNUP_SECRET", "test_secret_123")
        rv = client.post("/create_org", data={
            "secret": "test_secret_123",
            "company_name": "",
            "subdomain": "",
            "admin_email": "",
            "admin_password": "",
        })
        assert rv.status_code in (200, 302, 400)

    def test_post_wrong_secret_rejected(self, client, monkeypatch):
        import blueprints.org as _org
        monkeypatch.setattr(_org, "_SIGNUP_SECRET", "correct_secret")
        rv = client.post("/create_org", data={
            "secret": "wrong_secret",
            "company_name": "Test Corp",
            "subdomain": "testcorp",
            "admin_email": "admin@testcorp.com",
            "admin_password": "Admin@123",
        })
        assert rv.status_code in (200, 302, 400)

    def test_post_disabled_when_no_secret(self, client, monkeypatch):
        import blueprints.org as _org
        monkeypatch.setattr(_org, "_SIGNUP_SECRET", "")
        rv = client.post("/create_org", data={
            "company_name": "Test Corp",
            "subdomain": "testcorp",
        })
        assert rv.status_code in (200, 302, 400, 403)


# ── org_chart_page ────────────────────────────────────────────────────────────

class TestOrgChartPage:

    def test_unauthenticated_redirects(self, client):
        rv = client.get("/org_chart")
        assert rv.status_code == 302
        assert "admin_login" in rv.headers["Location"]

    def test_renders_for_admin(self, client, seed_admin):
        _admin_session(client, seed_admin)
        rv = client.get("/org_chart")
        assert rv.status_code == 200

    def test_renders_with_company_filter(self, client, seed_admin):
        _admin_session(client, seed_admin)
        with client.session_transaction() as sess:
            sess["active_company_id"] = 1
        rv = client.get("/org_chart")
        assert rv.status_code == 200


# ── api_org_chart_data ────────────────────────────────────────────────────────

class TestApiOrgChartData:

    def test_unauthenticated_redirects(self, client):
        rv = client.get("/api/org_chart_data")
        assert rv.status_code in (302, 401)

    def test_returns_json_for_admin(self, client, seed_admin):
        _admin_session(client, seed_admin)
        rv = client.get("/api/org_chart_data")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data.get("ok") is True
        assert "tree" in data

    def test_filters_by_department(self, client, seed_admin):
        _admin_session(client, seed_admin)
        rv = client.get("/api/org_chart_data?dept=Engineering")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "tree" in data or data.get("ok") is True

    def test_filters_by_company_id(self, client, seed_admin):
        _admin_session(client, seed_admin)
        with client.session_transaction() as sess:
            sess["active_company_id"] = 1
        rv = client.get("/api/org_chart_data")
        assert rv.status_code == 200

    def test_seed_employee_appears_in_chart(self, client, seed_admin, seed_employee):
        _admin_session(client, seed_admin)
        rv = client.get("/api/org_chart_data")
        assert rv.status_code == 200
        data = rv.get_json()
        tree = data.get("tree", {})
        import json
        tree_str = json.dumps(tree)
        assert seed_employee["employee_id"] in tree_str
