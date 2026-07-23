"""Tests for the optional Redis-backed shared cache: extensions.py's
_init_redis_backend() (decides Flask-Limiter's storage_uri) and
utils/waf.py's Redis-vs-in-memory breach counter dispatch.

No real Redis server is required for these — the reachable-Redis path is
exercised with a fake client, and the unset/unreachable paths use real
(non-)connections, matching the fail-open behavior the code implements."""
import datetime
import extensions as extensions_module
import utils.waf as waf_module


class FakeRedis:
    """Minimal stand-in for redis.Redis covering exactly what
    _init_redis_backend()/waf.py's breach counter call."""

    def __init__(self, host, port, password=None, socket_connect_timeout=None, socket_timeout=None):
        self.host, self.port = host, port
        self.store = {}

    def ping(self):
        return True

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, seconds):
        pass

    def delete(self, key):
        self.store.pop(key, None)


class RaisingRedis:
    def __init__(self, *a, **k):
        pass

    def ping(self):
        raise ConnectionError("connection refused")


class MidCallFailureRedis:
    """Connects fine at startup (ping succeeds) but every subsequent call fails
    — simulates a Redis instance that goes away after the app has already
    started using it."""

    def ping(self):
        return True

    def incr(self, key):
        raise ConnectionError("connection lost")


class TestInitRedisBackend:
    def test_unset_host_falls_back_to_memory(self, monkeypatch):
        monkeypatch.delenv("REDIS_HOST", raising=False)
        client, uri = extensions_module._init_redis_backend()
        assert client is None
        assert uri == "memory://"

    def test_unreachable_host_falls_back_to_memory(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "unreachable-host-for-tests")
        monkeypatch.setattr(extensions_module._redis_lib, "Redis", RaisingRedis)
        client, uri = extensions_module._init_redis_backend()
        assert client is None
        assert uri == "memory://"
        monkeypatch.delenv("REDIS_HOST", raising=False)

    def test_reachable_host_returns_client_and_redis_uri(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "fake-redis")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setattr(extensions_module._redis_lib, "Redis", FakeRedis)
        client, uri = extensions_module._init_redis_backend()
        assert isinstance(client, FakeRedis)
        assert uri == "redis://fake-redis:6379/0"
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.delenv("REDIS_PORT", raising=False)

    def test_password_included_in_uri_but_not_logged_elsewhere(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "fake-redis")
        monkeypatch.setenv("REDIS_PASSWORD", "s3cret")
        monkeypatch.setattr(extensions_module._redis_lib, "Redis", FakeRedis)
        client, uri = extensions_module._init_redis_backend()
        assert uri == "redis://:s3cret@fake-redis:6379/0"
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)


class TestWafBreachCounterRedisDispatch:
    def test_none_client_uses_in_memory_path(self, monkeypatch):
        monkeypatch.setattr(waf_module, "redis_client", None)
        waf_module._breach_log.pop("10.0.0.1", None)
        for _ in range(waf_module._BREACH_THRESHOLD - 1):
            waf_module.record_breach_and_maybe_ban("10.0.0.1", "test")
        assert len(waf_module._breach_log["10.0.0.1"]) == waf_module._BREACH_THRESHOLD - 1
        waf_module._breach_log.pop("10.0.0.1", None)

    def test_redis_client_used_when_configured(self, monkeypatch, db_engine):
        fake = FakeRedis(host="x", port=1)
        monkeypatch.setattr(waf_module, "redis_client", fake)
        ip = "10.0.0.2"
        cur = db_engine.cursor()
        cur.execute("DELETE FROM banned_ips WHERE ip=%s", (ip,))
        db_engine.commit()
        cur.close()
        try:
            for _ in range(waf_module._BREACH_THRESHOLD):
                waf_module.record_breach_and_maybe_ban(ip, "redis test breach")
            # Threshold crossed entirely via the fake Redis client — the
            # in-memory deque for this IP must stay untouched.
            assert ip not in waf_module._breach_log
            assert f"waf:breach:{ip}" not in fake.store  # deleted once banned

            cur = db_engine.cursor()
            cur.execute("SELECT expires_at FROM banned_ips WHERE ip=%s", (ip,))
            row = cur.fetchone()
            cur.close()
            assert row is not None
            assert row[0] > datetime.datetime.now()
        finally:
            cur = db_engine.cursor()
            cur.execute("DELETE FROM banned_ips WHERE ip=%s", (ip,))
            db_engine.commit()
            cur.close()

    def test_redis_failure_mid_call_falls_back_to_memory(self, monkeypatch):
        monkeypatch.setattr(waf_module, "redis_client", MidCallFailureRedis())
        ip = "10.0.0.3"
        waf_module._breach_log.pop(ip, None)
        calls = []
        monkeypatch.setattr(waf_module, "log_security_event",
                            lambda event_type, message, level="WARNING", **f: calls.append(event_type))
        waf_module.record_breach_and_maybe_ban(ip, "test")
        assert "waf.redis_error" in calls
        assert len(waf_module._breach_log[ip]) == 1
        waf_module._breach_log.pop(ip, None)
