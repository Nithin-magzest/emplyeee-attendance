"""Tests for the hidden SOC Analyst security-dashboard gate: the role check
+ TOTP step-up on POST /api/security/soc/verify-2fa and GET
/admin/security-dashboard (blueprints/admin_views.py), and the 404-disguise
behavior for every unauthorized path (anonymous, wrong role, wrong code)."""
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
def soc_admin(seed_admin, db_engine):
    """A seeded admin promoted to soc_analyst with TOTP enrolled+enabled."""
    cur = db_engine.cursor()
    cur.execute("UPDATE admin_users SET role='soc_analyst' WHERE username=%s", (seed_admin["username"],))
    db_engine.commit(); cur.close()
    secret, _ = totp_module.get_or_create_admin_totp_secret(seed_admin["username"])
    totp_module.mark_totp_enabled(seed_admin["username"])
    yield seed_admin["username"], secret
    cur = db_engine.cursor()
    cur.execute("UPDATE admin_users SET role='admin', totp_secret=NULL, totp_enabled=0 WHERE username=%s",
                (seed_admin["username"],))
    db_engine.commit(); cur.close()


class TestSocStepUpSession:
    def test_no_flag_means_invalid(self, client):
        with client.application.test_request_context():
            assert auth_module.soc_step_up_valid() is False

    def test_refresh_then_valid(self, client):
        with client.application.test_request_context():
            auth_module.soc_step_up_refresh()
            assert auth_module.soc_step_up_valid() is True

    def test_clear_invalidates(self, client):
        with client.application.test_request_context():
            auth_module.soc_step_up_refresh()
            auth_module.soc_step_up_clear()
            assert auth_module.soc_step_up_valid() is False

    def test_separate_from_email_settings_gate(self, client):
        # Passing one step-up gate must not silently grant the other.
        with client.application.test_request_context():
            auth_module.email_settings_step_up_refresh()
            assert auth_module.soc_step_up_valid() is False
            auth_module.soc_step_up_refresh()
            auth_module.email_settings_step_up_clear()
            assert auth_module.soc_step_up_valid() is True


class TestSocVerifyGate:
    def test_anonymous_gets_404(self, client):
        resp = client.post("/api/security/soc/verify-2fa", json={"code": "123456"})
        assert resp.status_code == 404

    def test_regular_admin_gets_404(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        resp = client.post("/api/security/soc/verify-2fa", json={"code": "123456"})
        assert resp.status_code == 404

    def test_manager_gets_404(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="manager")
        resp = client.post("/api/security/soc/verify-2fa", json={"code": "123456"})
        assert resp.status_code == 404

    def test_soc_role_wrong_code_gets_404(self, client, soc_admin):
        username, _ = soc_admin
        _admin_session(client, username, role="soc_analyst")
        resp = client.post("/api/security/soc/verify-2fa", json={"code": "000000"})
        assert resp.status_code == 404

    def test_soc_role_correct_code_succeeds(self, client, soc_admin):
        username, secret = soc_admin
        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        resp = client.post("/api/security/soc/verify-2fa", json={"code": code})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["redirect"] == "/admin/security-dashboard"

    def test_failure_response_body_is_generic(self, client, seed_admin):
        # Body/shape must not differ between "no session" and "wrong role"
        # and "wrong code" — that's the whole point of the disguise.
        anon = client.post("/api/security/soc/verify-2fa", json={"code": "1"})
        _admin_session(client, seed_admin["username"], role="admin")
        wrong_role = client.post("/api/security/soc/verify-2fa", json={"code": "1"})
        assert anon.status_code == wrong_role.status_code == 404


class TestSocNavVisibility:
    def test_regular_admin_does_not_see_nav_item(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert b"SOC / Security Center" not in resp.data

    def test_soc_analyst_sees_nav_item(self, client, soc_admin):
        username, _ = soc_admin
        _admin_session(client, username, role="soc_analyst")
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert b"SOC / Security Center" in resp.data


class TestSocDashboardRoute:
    def test_anonymous_gets_404(self, client):
        assert client.get("/admin/security-dashboard").status_code == 404

    def test_soc_role_without_stepup_gets_404(self, client, soc_admin):
        username, _ = soc_admin
        _admin_session(client, username, role="soc_analyst")
        assert client.get("/admin/security-dashboard").status_code == 404

    def test_soc_role_with_stepup_succeeds(self, client, soc_admin):
        username, secret = soc_admin
        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        verify = client.post("/api/security/soc/verify-2fa", json={"code": code})
        assert verify.status_code == 200
        resp = client.get("/admin/security-dashboard")
        assert resp.status_code == 200
        assert b"Security Dashboard" in resp.data

    def test_regular_admin_with_stepup_flag_forged_still_404s(self, client, seed_admin):
        # Even if a regular admin's session somehow carries a soc_2fa_verified_at
        # timestamp (e.g. stale data), the role check alone must still block —
        # step-up proves identity, not entitlement.
        _admin_session(client, seed_admin["username"], role="admin")
        with client.session_transaction() as sess:
            import time
            sess["soc_2fa_verified_at"] = time.time()
        assert client.get("/admin/security-dashboard").status_code == 404

    def test_lock_reasserts_gate(self, client, soc_admin):
        username, secret = soc_admin
        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        client.post("/api/security/soc/verify-2fa", json={"code": code})
        assert client.get("/admin/security-dashboard").status_code == 200

        client.post("/api/security/soc/lock")
        assert client.get("/admin/security-dashboard").status_code == 404

    def test_dashboard_shows_real_compromised_session_data(self, client, soc_admin, db_engine):
        username, secret = soc_admin
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO session_risk (sid, identifier, attempt_type, score, status, last_reason) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (sid) DO NOTHING",
            ("test-sid-soc-dash", "EMP999", "employee", 100, "compromised", "Wi-Fi risk score 90 exceeded 60"),
        )
        db_engine.commit(); cur.close()

        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        client.post("/api/security/soc/verify-2fa", json={"code": code})
        resp = client.get("/admin/security-dashboard")
        assert resp.status_code == 200
        assert b"EMP999" in resp.data
        assert b"Wi-Fi risk score 90" in resp.data

        cur = db_engine.cursor()
        cur.execute("DELETE FROM session_risk WHERE sid='test-sid-soc-dash'")
        db_engine.commit(); cur.close()

    def test_dashboard_shows_recent_security_events(self, client, soc_admin, db_engine):
        username, secret = soc_admin
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO security_events (event_type, level, message, identifier) "
            "VALUES (%s,%s,%s,%s)",
            ("access.denied", "WARNING", "Test event for dashboard rendering", "PROBE_USER_XYZ"),
        )
        db_engine.commit(); cur.close()

        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        client.post("/api/security/soc/verify-2fa", json={"code": code})
        resp = client.get("/admin/security-dashboard")
        assert resp.status_code == 200
        assert b"Security Event Log" in resp.data
        assert b"PROBE_USER_XYZ" in resp.data
        assert b"Test event for dashboard rendering" in resp.data

        cur = db_engine.cursor()
        cur.execute("DELETE FROM security_events WHERE identifier='PROBE_USER_XYZ'")
        db_engine.commit(); cur.close()

    def test_dashboard_shows_security_posture_and_mfa_panels(self, client, soc_admin):
        username, secret = soc_admin
        _admin_session(client, username, role="soc_analyst")
        code = pyotp.TOTP(secret).now()
        client.post("/api/security/soc/verify-2fa", json={"code": code})
        resp = client.get("/admin/security-dashboard")
        assert resp.status_code == 200
        assert b"Security Posture" in resp.data
        assert b"Admin MFA Enrollment" in resp.data
        # This admin account is itself enrolled (soc_admin fixture enables
        # TOTP) — its own row should show up as enrolled in the table.
        assert username.encode() in resp.data
