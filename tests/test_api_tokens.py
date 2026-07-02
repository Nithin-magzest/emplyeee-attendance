"""Tests for API token lifecycle: hashing, issuance, expiry, revocation."""
import hashlib
import secrets
import time
import pytest


def _sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── Token hash helper ─────────────────────────────────────────────────────────

class TestTokenHash:
    def test_hash_is_sha256_hex(self):
        raw = "some-random-token-value"
        h = _sha256(raw)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_input_same_hash(self):
        t = secrets.token_hex(32)
        assert _sha256(t) == _sha256(t)

    def test_different_inputs_different_hashes(self):
        assert _sha256("abc") != _sha256("def")


# ── /api/login endpoint ───────────────────────────────────────────────────────

class TestApiLoginEndpoint:
    def test_missing_body_returns_error(self, client):
        resp = client.post("/api/login", json={})
        assert resp.status_code in (400, 401)

    def test_wrong_content_type_handled(self, client):
        resp = client.post("/api/login", data="username=x&password=y",
                           content_type="application/x-www-form-urlencoded")
        # Should not crash with 500
        assert resp.status_code != 500

    def test_bad_credentials_return_401_or_ok_false(self, client):
        resp = client.post("/api/login", json={
            "username": "nonexistent_admin_xyz", "password": "nope"
        })
        data = resp.get_json()
        if resp.status_code == 200:
            assert not data["ok"]
        else:
            assert resp.status_code == 401

    def test_good_credentials_return_token(self, client, seed_admin):
        resp = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"]
        assert "token" in data
        assert len(data["token"]) > 20

    def test_token_is_stored_hashed_not_plaintext(self, client, seed_admin, db_engine):
        resp = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = resp.get_json()["token"]
        token_hash = _sha256(token)

        cur = db_engine.cursor()
        cur.execute("SELECT token_hash FROM api_tokens WHERE token_hash=%s", (token_hash,))
        row = cur.fetchone()
        cur.close()
        assert row is not None, "Token hash must be stored in api_tokens table"


# ── /api/logout endpoint ──────────────────────────────────────────────────────

class TestApiLogout:
    def test_logout_invalidates_token(self, client, seed_admin):
        # Login
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        auth = {"Authorization": f"Bearer {token}"}

        # Verify token works
        r2 = client.get("/api/employees", headers=auth)
        assert r2.status_code == 200

        # Logout
        r3 = client.post("/api/logout", headers=auth)
        assert r3.get_json()["ok"]

        # Token should be dead
        r4 = client.get("/api/employees", headers=auth)
        assert r4.status_code == 401

    def test_double_logout_is_safe(self, client, seed_admin):
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        auth = {"Authorization": f"Bearer {token}"}

        client.post("/api/logout", headers=auth)
        r2 = client.post("/api/logout", headers=auth)
        # Second logout should not crash (200 ok:false or 401, not 500)
        assert r2.status_code != 500


# ── Token expiry ──────────────────────────────────────────────────────────────

class TestTokenExpiry:
    def test_expired_token_rejected(self, client, seed_admin, db_engine):
        """Manually expire a token in the DB and verify it is rejected."""
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        token_hash = _sha256(token)

        # Backdate expiry to past
        cur = db_engine.cursor()
        cur.execute(
            "UPDATE api_tokens SET expires_at = NOW() - INTERVAL 1 HOUR WHERE token_hash=%s",
            (token_hash,)
        )
        cur.close()

        resp = client.get("/api/employees",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ── Employee API token ────────────────────────────────────────────────────────

class TestEmployeeApiToken:
    def test_employee_login_returns_token(self, client, seed_employee):
        resp = client.post("/api/employee/login", json={
            "employee_id": seed_employee["employee_id"],
            "password":    seed_employee["password"],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"]
        assert "token" in data

    def test_employee_token_cannot_access_admin_endpoint(self, client, seed_employee):
        r1 = client.post("/api/employee/login", json={
            "employee_id": seed_employee["employee_id"],
            "password":    seed_employee["password"],
        })
        token = r1.get_json()["token"]
        # Admin-only endpoint
        resp = client.get("/api/employees",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_admin_token_cannot_access_employee_endpoint(self, client, seed_admin):
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        resp = client.get("/api/employee/portal",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ── /api/v1/ aliases ─────────────────────────────────────────────────────────

class TestApiV1Aliases:
    def test_v1_login_endpoint_exists(self, client, seed_admin):
        resp = client.post("/api/v1/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        # Should reach the route (200 with token, not 404)
        assert resp.status_code != 404

    def test_v1_employees_endpoint_exists(self, client, seed_admin):
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        resp = client.get("/api/v1/employees",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code != 404

    def test_v1_and_v0_return_same_data(self, client, seed_admin):
        r1 = client.post("/api/login", json={
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        })
        token = r1.get_json()["token"]
        auth = {"Authorization": f"Bearer {token}"}

        r_v0 = client.get("/api/employees", headers=auth)
        r_v1 = client.get("/api/v1/employees", headers=auth)
        assert r_v0.status_code == r_v1.status_code
        assert r_v0.get_json() == r_v1.get_json()
