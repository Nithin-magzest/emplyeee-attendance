"""Tests for the application-layer IP ban: app.py's _enforce_ip_ban
before_request hook (runs before every other hook, blocking a banned source
before session/auth logic even runs) and the SOC dashboard's tactical
mitigation endpoints (blueprints/admin_views.py: ban-ip/unban-ip/banned-ips)."""
import datetime
import pyotp
import pytest
import utils.totp as totp_module


def _admin_session(client, username, role="admin"):
    with client.session_transaction() as sess:
        sess["admin_logged_in"] = True
        sess["admin_username"] = username
        sess["admin_role"] = role


def _ban(db_engine, ip, reason="test", banned_by="tester", expires_at=None):
    cur = db_engine.cursor()
    cur.execute(
        "INSERT INTO banned_ips (ip, reason, banned_by, expires_at) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (ip) DO UPDATE SET reason=EXCLUDED.reason, expires_at=EXCLUDED.expires_at",
        (ip, reason, banned_by, expires_at),
    )
    db_engine.commit(); cur.close()


def _unban(db_engine, ip):
    cur = db_engine.cursor()
    cur.execute("DELETE FROM banned_ips WHERE ip=%s", (ip,))
    db_engine.commit(); cur.close()


@pytest.fixture
def soc_admin(seed_admin, db_engine):
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


@pytest.fixture
def soc_admin_verified(client, soc_admin):
    username, secret = soc_admin
    _admin_session(client, username, role="soc_analyst")
    code = pyotp.TOTP(secret).now()
    client.post("/api/security/soc/verify-2fa", json={"code": code})
    return username, secret


class TestEnforceIpBanHook:
    def test_banned_ip_gets_403(self, client, db_engine):
        _ban(db_engine, "203.0.113.9")
        resp = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "203.0.113.9"})
        assert resp.status_code == 403
        _unban(db_engine, "203.0.113.9")

    def test_non_banned_ip_unaffected(self, client, db_engine):
        resp = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "203.0.113.10"})
        assert resp.status_code == 200

    def test_expired_ban_does_not_block(self, client, db_engine):
        _ban(db_engine, "203.0.113.11", expires_at=datetime.datetime.now() - datetime.timedelta(minutes=1))
        resp = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "203.0.113.11"})
        assert resp.status_code == 200
        _unban(db_engine, "203.0.113.11")

    def test_permanent_ban_has_no_expiry(self, client, db_engine):
        _ban(db_engine, "203.0.113.12", expires_at=None)
        resp = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "203.0.113.12"})
        assert resp.status_code == 403
        _unban(db_engine, "203.0.113.12")

    def test_static_assets_stay_reachable_for_banned_ip(self, client, db_engine):
        _ban(db_engine, "203.0.113.13")
        resp = client.get("/static/shared.css", environ_overrides={"REMOTE_ADDR": "203.0.113.13"})
        assert resp.status_code != 403
        _unban(db_engine, "203.0.113.13")


class TestSocBanEndpoints:
    def test_anonymous_gets_404_on_all_three(self, client):
        assert client.get("/api/security/soc/banned-ips").status_code == 404
        assert client.post("/api/security/soc/ban-ip", json={"ip": "1.2.3.4"}).status_code == 404
        assert client.post("/api/security/soc/unban-ip", json={"ip": "1.2.3.4"}).status_code == 404

    def test_regular_admin_gets_404(self, client, seed_admin):
        _admin_session(client, seed_admin["username"], role="admin")
        assert client.post("/api/security/soc/ban-ip", json={"ip": "1.2.3.4"}).status_code == 404

    def test_soc_role_without_stepup_gets_404(self, client, soc_admin):
        username, _ = soc_admin
        _admin_session(client, username, role="soc_analyst")
        assert client.post("/api/security/soc/ban-ip", json={"ip": "1.2.3.4"}).status_code == 404

    def test_ban_invalid_ip_rejected(self, client, soc_admin_verified):
        resp = client.post("/api/security/soc/ban-ip", json={"ip": "not-an-ip"})
        assert resp.status_code == 400

    def test_ban_then_it_blocks_and_appears_in_list(self, client, soc_admin_verified, db_engine):
        resp = client.post("/api/security/soc/ban-ip", json={"ip": "198.51.100.5", "reason": "test ban"})
        assert resp.get_json()["ok"] is True

        listing = client.get("/api/security/soc/banned-ips").get_json()
        assert any(b["ip"] == "198.51.100.5" for b in listing["banned_ips"])

        blocked = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "198.51.100.5"})
        assert blocked.status_code == 403

        _unban(db_engine, "198.51.100.5")

    def test_unban_removes_block(self, client, soc_admin_verified, db_engine):
        _ban(db_engine, "198.51.100.6")
        resp = client.post("/api/security/soc/unban-ip", json={"ip": "198.51.100.6"})
        assert resp.get_json()["ok"] is True

        listing = client.get("/api/security/soc/banned-ips").get_json()
        assert not any(b["ip"] == "198.51.100.6" for b in listing["banned_ips"])

        # This client is already logged in (soc_admin_verified), so
        # /admin_login itself would 302 regardless of ban status — the
        # thing under test is that the ban no longer 403s, not the redirect.
        allowed = client.get("/admin_login", environ_overrides={"REMOTE_ADDR": "198.51.100.6"})
        assert allowed.status_code != 403

    def test_temporary_ban_sets_expiry(self, client, soc_admin_verified, db_engine):
        resp = client.post("/api/security/soc/ban-ip", json={"ip": "198.51.100.7", "duration_minutes": 30})
        assert resp.get_json()["ok"] is True

        cur = db_engine.cursor()
        cur.execute("SELECT expires_at FROM banned_ips WHERE ip=%s", ("198.51.100.7",))
        expires_at = cur.fetchone()[0]
        cur.close()
        assert expires_at is not None
        assert expires_at > datetime.datetime.now()

        _unban(db_engine, "198.51.100.7")
