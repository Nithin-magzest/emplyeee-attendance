"""Tests for the consolidated Security Settings hub (Settings -> System ->
Security): its own MFA step-up gate (utils/auth.py's
require_security_settings_2fa) and the row-data API in
blueprints/admin_views.py (/api/settings/security/*). Any logged-in admin
can open this hub with their own TOTP code — unlike the SOC dashboard, it
has no role restriction; the SOC row inside it still enforces its own
separate, role-gated step-up when followed."""
import pyotp
import pytest
import utils.auth as auth_module
import utils.totp as totp_module


def _admin_session(client, username, role="admin"):
    with client.session_transaction() as sess:
        sess["admin_logged_in"] = True
        sess["admin_username"] = username
        sess["admin_role"] = role


@pytest.fixture
def mfa_admin(seed_admin, db_engine):
    """A seeded admin (regular role) with TOTP enrolled+enabled."""
    secret, _ = totp_module.get_or_create_admin_totp_secret(seed_admin["username"])
    totp_module.mark_totp_enabled(seed_admin["username"])
    yield seed_admin["username"], secret
    cur = db_engine.cursor()
    cur.execute("UPDATE admin_users SET totp_secret=NULL, totp_enabled=0 WHERE username=%s",
                (seed_admin["username"],))
    db_engine.commit()
    cur.close()


class TestSecurityHubPage:
    def test_page_renders_for_any_logged_in_admin(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        resp = client.get("/security")
        assert resp.status_code == 200
        assert b"Identity Verification Required" in resp.data

    def test_page_requires_admin_login(self, client):
        resp = client.get("/security", follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_admin_dashboard_links_to_standalone_page(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert b'href="/security"' in resp.data


class TestSecuritySettingsStepUp:
    def test_no_flag_means_invalid(self, client):
        with client.application.test_request_context():
            assert auth_module.security_settings_step_up_valid() is False

    def test_refresh_then_valid(self, client):
        with client.application.test_request_context():
            auth_module.security_settings_step_up_refresh()
            assert auth_module.security_settings_step_up_valid() is True

    def test_independent_of_email_and_soc_gates(self, client):
        with client.application.test_request_context():
            auth_module.email_settings_step_up_refresh()
            auth_module.soc_step_up_refresh()
            assert auth_module.security_settings_step_up_valid() is False


class TestSecuritySettingsRoutes:
    def test_overview_without_stepup_is_403(self, client, seed_admin):
        _admin_session(client, seed_admin["username"])
        resp = client.get("/api/settings/security/overview")
        assert resp.status_code == 403

    def test_verify_wrong_code_denied(self, client, mfa_admin):
        username, _ = mfa_admin
        _admin_session(client, username)
        resp = client.post("/api/settings/security/verify-2fa", json={"code": "000000"})
        assert resp.status_code == 401

    def test_verify_correct_code_unlocks_overview(self, client, mfa_admin):
        username, secret = mfa_admin
        _admin_session(client, username, role="admin")
        code = pyotp.TOTP(secret).now()
        verify = client.post("/api/settings/security/verify-2fa", json={"code": code})
        assert verify.status_code == 200

        resp = client.get("/api/settings/security/overview")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["is_soc_analyst"] is False
        assert data["own_totp_enrolled"] is True
        assert "security_posture" in data
        assert "session_timeout_minutes" in data

    def test_soc_analyst_flag_reflected_in_overview(self, client, mfa_admin, db_engine):
        username, secret = mfa_admin
        cur = db_engine.cursor()
        cur.execute("UPDATE admin_users SET role='soc_analyst' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})
        resp = client.get("/api/settings/security/overview")
        assert resp.get_json()["is_soc_analyst"] is True

        cur = db_engine.cursor()
        cur.execute("UPDATE admin_users SET role='admin' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

    def test_session_timeout_save_without_stepup_is_403(self, client, seed_admin):
        _admin_session(client, seed_admin["username"])
        resp = client.post("/api/settings/security/session-timeout", json={"timeout": 60})
        assert resp.status_code == 403

    def test_session_timeout_save_with_stepup_succeeds(self, client, mfa_admin, db_engine):
        username, secret = mfa_admin
        _admin_session(client, username)
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})

        resp = client.post("/api/settings/security/session-timeout", json={"timeout": 60})
        assert resp.get_json()["ok"] is True

        cur = db_engine.cursor()
        cur.execute("SELECT session_timeout FROM company_settings LIMIT 1")
        assert cur.fetchone()[0] == 60
        cur.close()
        # restore default
        cur = db_engine.cursor()
        cur.execute("UPDATE company_settings SET session_timeout=30")
        db_engine.commit()
        cur.close()

    def test_session_timeout_rejects_out_of_range(self, client, mfa_admin):
        username, secret = mfa_admin
        _admin_session(client, username)
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})

        resp = client.post("/api/settings/security/session-timeout", json={"timeout": 99999})
        assert resp.status_code == 400

    def test_lock_reasserts_gate(self, client, mfa_admin):
        username, secret = mfa_admin
        _admin_session(client, username)
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})
        assert client.get("/api/settings/security/overview").status_code == 200

        client.post("/api/settings/security/lock")
        assert client.get("/api/settings/security/overview").status_code == 403

    def test_legacy_save_security_settings_route_removed(self, client, seed_admin):
        _admin_session(client, seed_admin["username"])
        resp = client.post("/save_security_settings", data={"session_timeout": "60"})
        assert resp.status_code == 404

    def test_overview_hides_roster_for_non_admin_role(self, client, mfa_admin, db_engine):
        username, secret = mfa_admin
        cur = db_engine.cursor()
        cur.execute("UPDATE admin_users SET role='manager' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

        _admin_session(client, username, role="manager")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})
        resp = client.get("/api/settings/security/overview")
        data = resp.get_json()
        assert data["can_manage_roles"] is False
        assert data["admin_roster"] == []

        cur = db_engine.cursor()
        cur.execute("UPDATE admin_users SET role='admin' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

    def test_overview_shows_roster_for_admin_role(self, client, mfa_admin):
        username, secret = mfa_admin
        _admin_session(client, username, role="admin")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})
        resp = client.get("/api/settings/security/overview")
        data = resp.get_json()
        assert data["can_manage_roles"] is True
        assert any(row["username"] == username for row in data["admin_roster"])


class TestRoleManagement:
    def test_role_change_by_admin_succeeds(self, client, mfa_admin, db_engine):
        username, secret = mfa_admin
        _admin_session(client, username, role="admin")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})

        resp = client.post("/api/settings/security/roles",
                           json={"username": username, "role": "manager"})
        assert resp.get_json()["ok"] is True

        cur = db_engine.cursor()
        cur.execute("SELECT role FROM admin_users WHERE username=%s", (username,))
        assert cur.fetchone()[0] == "manager"
        cur.execute("UPDATE admin_users SET role='admin' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

    def test_role_change_by_non_admin_gets_404(self, client, mfa_admin, db_engine):
        username, secret = mfa_admin
        cur = db_engine.cursor()
        cur.execute("UPDATE admin_users SET role='manager' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

        _admin_session(client, username, role="manager")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})

        resp = client.post("/api/settings/security/roles",
                           json={"username": username, "role": "soc_analyst"})
        assert resp.status_code == 404

        cur = db_engine.cursor()
        cur.execute("SELECT role FROM admin_users WHERE username=%s", (username,))
        assert cur.fetchone()[0] == "manager"  # unchanged — the attempted escalation did not land
        cur.execute("UPDATE admin_users SET role='admin' WHERE username=%s", (username,))
        db_engine.commit()
        cur.close()

    def test_role_change_rejects_invalid_role_value(self, client, mfa_admin):
        username, secret = mfa_admin
        _admin_session(client, username, role="admin")
        code = pyotp.TOTP(secret).now()
        client.post("/api/settings/security/verify-2fa", json={"code": code})

        resp = client.post("/api/settings/security/roles",
                           json={"username": username, "role": "superadmin"})
        assert resp.status_code == 400

    def test_role_change_requires_stepup(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        resp = client.post("/api/settings/security/roles",
                           json={"username": seed_admin["username"], "role": "manager"})
        assert resp.status_code == 403
