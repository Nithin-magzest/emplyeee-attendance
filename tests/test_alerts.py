"""Tests for utils/alerts.py: sanitization, masking, and HMAC signing for
the security-notification webhook pipeline. No network calls — these test
the pure sanitize/mask/sign functions directly, not delivery (delivery is
a fire-and-forget background thread hitting an external webhook, verified
separately against a local HTTP receiver when this module was built)."""
import hmac
import hashlib
import json

from utils.alerts import (
    _sanitize_fields,
    _sanitize_description,
    mask_raw_payload,
    _sign,
)


# ── _sanitize_fields: allowlist over known call-site fields ─────────────────

class TestSanitizeFields:
    def test_allowlisted_field_passes_through(self):
        out = _sanitize_fields({"identifier": "admin", "ip": "1.2.3.4"})
        assert out == {"identifier": "admin", "ip": "1.2.3.4"}

    def test_unknown_field_is_dropped(self):
        out = _sanitize_fields({"identifier": "admin", "totally_unexpected_field": "value"})
        assert "totally_unexpected_field" not in out
        assert out["identifier"] == "admin"

    def test_password_field_is_dropped_not_just_redacted(self):
        # "password" was never added to the allowlist at all — this must
        # never appear in the output under any key spelling.
        out = _sanitize_fields({"identifier": "admin", "password": "hunter2"})
        assert "password" not in out
        assert "hunter2" not in json.dumps(out)

    def test_secret_shaped_value_redacted_even_under_allowlisted_key(self):
        # "reason" is allowlisted by name, but a credential-shaped VALUE
        # smuggled in under it must still be caught — defense in depth
        # against a future call site passing the wrong thing under a
        # legitimate key.
        out = _sanitize_fields({"reason": "token=abc123secret"})
        assert out["reason"] == "[redacted]"

    def test_none_values_dropped(self):
        out = _sanitize_fields({"identifier": None, "ip": "1.2.3.4"})
        assert "identifier" not in out
        assert out["ip"] == "1.2.3.4"

    def test_long_value_truncated(self):
        out = _sanitize_fields({"reason": "x" * 500})
        assert len(out["reason"]) <= 202  # 200 chars + ellipsis
        assert out["reason"].endswith("…")


class TestSanitizeDescription:
    def test_plain_description_passes_through(self):
        assert _sanitize_description("Account locked after repeated failures") == \
            "Account locked after repeated failures"

    def test_credential_shaped_description_redacted(self):
        out = _sanitize_description("Login failed with password=hunter2")
        assert "hunter2" not in out
        assert "redacted" in out

    def test_long_description_truncated(self):
        out = _sanitize_description("x" * 2000)
        assert len(out) <= 1001


# ── mask_raw_payload: recursive masking of an arbitrary/unknown object ──────

class TestMaskRawPayload:
    def test_password_key_redacted(self):
        out = mask_raw_payload({"username": "bob", "password": "hunter2"})
        assert out["password"] == "[redacted]"
        assert out["username"] == "bob"

    def test_pii_keys_redacted(self):
        # These match the exact PII fields this app already encrypts at
        # rest (utils/helpers.py encrypt_pii) — pan_number, uan_number,
        # bank_account — masking here must cover the same set.
        raw = {
            "pan_number": "ABCDE1234F",
            "uan_number": "123456789012",
            "bank_account": "000111222333",
            "email": "employee@example.com",
            "department": "Engineering",
        }
        out = mask_raw_payload(raw)
        assert out["pan_number"] == "[redacted]"
        assert out["uan_number"] == "[redacted]"
        assert out["bank_account"] == "[redacted]"
        assert out["email"] == "[redacted]"
        assert out["department"] == "Engineering"

    def test_token_shaped_value_redacted_under_innocuous_key(self):
        # No sensitive key name here at all — this must be caught purely
        # by the VALUE looking like a token/API key/hash.
        out = mask_raw_payload({"note": "auth succeeded with x9J2kL8pQmN4rT6vY1wZ3bC5dF7gH0jK"})
        assert "redacted-token" in out["note"]
        assert "x9J2kL8pQmN4rT6vY1wZ3bC5dF7gH0jK" not in out["note"]

    def test_email_shaped_value_redacted_under_innocuous_key(self):
        out = mask_raw_payload({"contact": "reach me at someone@company.com please"})
        assert "redacted-email" in out["contact"]
        assert "someone@company.com" not in out["contact"]

    def test_nested_dict_masked_recursively(self):
        raw = {"request": {"headers": {"Authorization": "Bearer abc123secrettoken"},
                            "body": {"employee_name": "Priya"}}}
        out = mask_raw_payload(raw)
        assert out["request"]["headers"]["Authorization"] == "[redacted]"
        assert out["request"]["body"]["employee_name"] == "Priya"

    def test_list_of_dicts_masked(self):
        raw = {"attempts": [{"password": "a"}, {"password": "b"}, {"user": "ok"}]}
        out = mask_raw_payload(raw)
        assert all(item.get("password", "[redacted]") == "[redacted]"
                   for item in out["attempts"] if "password" in item)
        assert out["attempts"][2]["user"] == "ok"

    def test_depth_limit_prevents_unbounded_recursion(self):
        # A pathologically deep structure (or a circular exception
        # __context__ chain) must collapse to a marker instead of hanging
        # or raising RecursionError.
        raw = {"a": {"b": {"c": {"d": {"e": {"f": "too deep"}}}}}}
        out = mask_raw_payload(raw)
        # Walk down until we hit the collapsed marker rather than a dict
        node = out
        depths = 0
        while isinstance(node, dict) and depths < 10:
            node = next(iter(node.values()))
            depths += 1
        assert node == "[max depth reached]"

    def test_non_string_scalars_pass_through_unmasked(self):
        out = mask_raw_payload({"count": 42, "active": True, "ratio": 3.14, "missing": None})
        assert out == {"count": 42, "active": True, "ratio": 3.14, "missing": None}

    def test_oversized_list_is_truncated(self):
        out = mask_raw_payload({"items": list(range(100))})
        assert len(out["items"]) == 21  # 20 items + one truncation marker
        assert "truncated" in out["items"][-1]


# ── HMAC signing: integrity guarantee ────────────────────────────────────────

class TestHmacSigning:
    def test_signature_is_deterministic_for_same_body_and_secret(self):
        body = json.dumps({"event": "test"}).encode()
        assert _sign(body) == _sign(body)

    def test_signature_changes_if_payload_tampered(self):
        body_a = json.dumps({"event": "test", "severity": "ERROR"}).encode()
        body_b = json.dumps({"event": "test", "severity": "CRITICAL"}).encode()
        assert _sign(body_a) != _sign(body_b)

    def test_signature_matches_manual_hmac_sha256(self):
        # Confirms this is genuinely HMAC-SHA256 over the exact body bytes,
        # not some other construction — verifiable independently by
        # whatever's on the receiving end of X-Signature-256.
        import utils.alerts as alerts_module
        body = b'{"event":"integrity-check"}'
        expected = hmac.new(
            alerts_module._SIGNING_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        assert _sign(body) == expected

    def test_signature_is_hex_sha256_length(self):
        # SHA-256 digests are 32 bytes -> 64 hex characters, regardless of
        # input size.
        assert len(_sign(b"short")) == 64
        assert len(_sign(b"x" * 10_000)) == 64
