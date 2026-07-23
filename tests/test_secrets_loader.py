"""
utils/secrets_loader.py tests.

boto3 is imported locally inside load_aws_secrets() (kept out of the
module's top-level imports so local dev / test environments that never set
AWS_SECRET_ID don't need the SDK installed at all). These tests inject a
fake boto3 module via sys.modules rather than requiring the real SDK —
this also means no test here can ever make a real AWS API call by
accident, and it works regardless of which Python version boto3 itself
supports (the pinned boto3>=1.34.0 requires Python >=3.8; this dev
machine's default interpreter is 3.7, though CI and the production
Containerfile both run 3.11).

Run with:
    python -m pytest tests/test_secrets_loader.py -v
"""
import sys
import json
import types
import pytest
from utils.secrets_loader import load_aws_secrets


class _FakeClientError(Exception):
    pass


class _FakeBotoCoreError(Exception):
    pass


def _install_fake_boto3(monkeypatch, secret_string=None, raise_error=None):
    """Patch sys.modules so `import boto3` / `from botocore.exceptions
    import ...` inside load_aws_secrets() resolve to fakes we control."""
    calls = {}

    class FakeSecretsManagerClient:
        def get_secret_value(self, SecretId):
            calls["secret_id"] = SecretId
            if raise_error is not None:
                raise raise_error
            return {"SecretString": secret_string}

    fake_boto3 = types.ModuleType("boto3")

    def _client(service_name, region_name=None):
        calls["region_name"] = region_name
        calls["service_name"] = service_name
        return FakeSecretsManagerClient()
    fake_boto3.client = _client

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_exceptions = types.ModuleType("botocore.exceptions")
    fake_botocore_exceptions.BotoCoreError = _FakeBotoCoreError
    fake_botocore_exceptions.ClientError = _FakeClientError
    fake_botocore.exceptions = fake_botocore_exceptions

    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_botocore_exceptions)
    return calls


# ===========================================================================
# No-op path — the default for every local/dev run
# ===========================================================================

class TestNoOpWhenUnconfigured:
    def test_returns_false_when_no_secret_id_anywhere(self, monkeypatch):
        monkeypatch.delenv("AWS_SECRET_ID", raising=False)
        assert load_aws_secrets() is False

    def test_does_not_touch_boto3_when_unconfigured(self, monkeypatch):
        """If AWS_SECRET_ID is unset, boto3 must never even be imported —
        this is what keeps local dev working without the SDK installed."""
        monkeypatch.delenv("AWS_SECRET_ID", raising=False)
        monkeypatch.setitem(sys.modules, "boto3", None)  # import would raise
        assert load_aws_secrets() is False


# ===========================================================================
# Happy path
# ===========================================================================

class TestLoadsSecretsIntoEnviron:
    def test_populates_environ_from_secret_payload(self, monkeypatch):
        payload = json.dumps({"SECRET_KEY": "sk-123", "DB_PASS": "pw-456"})
        _install_fake_boto3(monkeypatch, secret_string=payload)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("DB_PASS", raising=False)

        result = load_aws_secrets("my-secret-id")

        assert result is True
        import os
        assert os.environ["SECRET_KEY"] == "sk-123"
        assert os.environ["DB_PASS"] == "pw-456"

    def test_uses_explicit_secret_id_over_env_var(self, monkeypatch):
        payload = json.dumps({"X": "1"})
        calls = _install_fake_boto3(monkeypatch, secret_string=payload)
        monkeypatch.setenv("AWS_SECRET_ID", "env-configured-id")

        load_aws_secrets("explicit-id")

        assert calls["secret_id"] == "explicit-id"

    def test_falls_back_to_env_var_secret_id(self, monkeypatch):
        payload = json.dumps({"Y": "2"})
        calls = _install_fake_boto3(monkeypatch, secret_string=payload)
        monkeypatch.setenv("AWS_SECRET_ID", "env-configured-id")

        load_aws_secrets()

        assert calls["secret_id"] == "env-configured-id"

    def test_uses_configured_region_or_default(self, monkeypatch):
        payload = json.dumps({"Z": "3"})
        calls = _install_fake_boto3(monkeypatch, secret_string=payload)
        monkeypatch.delenv("AWS_REGION", raising=False)

        load_aws_secrets("some-id")
        assert calls["region_name"] == "ap-south-1"

        monkeypatch.setenv("AWS_REGION", "us-east-1")
        load_aws_secrets("some-id")
        assert calls["region_name"] == "us-east-1"

    def test_does_not_override_already_set_env_vars(self, monkeypatch):
        """setdefault semantics — a real local .env value must always win
        over Secrets Manager, matching wsgi.py calling this before
        load_dotenv()."""
        payload = json.dumps({"SECRET_KEY": "from-aws"})
        _install_fake_boto3(monkeypatch, secret_string=payload)
        monkeypatch.setenv("SECRET_KEY", "already-set-locally")

        load_aws_secrets("my-secret-id")

        import os
        assert os.environ["SECRET_KEY"] == "already-set-locally"


# ===========================================================================
# Failure path — must fail loudly, not boot with missing secrets
# ===========================================================================

class TestFailsLoudlyOnError:
    def test_client_error_propagates(self, monkeypatch):
        _install_fake_boto3(monkeypatch, raise_error=_FakeClientError("access denied"))
        with pytest.raises(_FakeClientError):
            load_aws_secrets("bad-id")

    def test_botocore_error_propagates(self, monkeypatch):
        _install_fake_boto3(monkeypatch, raise_error=_FakeBotoCoreError("network issue"))
        with pytest.raises(_FakeBotoCoreError):
            load_aws_secrets("bad-id")
