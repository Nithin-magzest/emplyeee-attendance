"""Tests for security_events persistence: every log_security_event() call
(extensions.py) now also writes to the security_events table via the
background writer thread (utils/async_writer.py), so the SOC dashboard has
real data to show instead of just the log stream."""
import time
from extensions import log_security_event


def _wait_for_event(db_engine, identifier, timeout=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        cur = db_engine.cursor()
        cur.execute("SELECT event_type, level, message FROM security_events WHERE identifier=%s", (identifier,))
        row = cur.fetchone()
        cur.close()
        if row:
            return row
        time.sleep(0.05)
    return None


class TestSecurityEventPersistence:
    def test_event_lands_in_db_asynchronously(self, client, db_engine):
        # `client` fixture ensures the Flask app (and its background writer
        # thread) is initialized before this runs.
        identifier = "TEST_PERSIST_001"
        with client.application.test_request_context("/some/path"):
            log_security_event("test.event", "A test security event", level="WARNING",
                                identifier=identifier)

        row = _wait_for_event(db_engine, identifier)
        assert row is not None
        event_type, level, message = row
        assert event_type == "test.event"
        assert level == "WARNING"
        assert message == "A test security event"

        cur = db_engine.cursor()
        cur.execute("DELETE FROM security_events WHERE identifier=%s", (identifier,))
        db_engine.commit(); cur.close()

    def test_extra_fields_stored_as_json(self, client, db_engine):
        identifier = "TEST_PERSIST_002"
        with client.application.test_request_context("/some/path"):
            log_security_event("test.event2", "Another test event", level="INFO",
                                identifier=identifier, custom_field="custom_value", score="42")

        row = _wait_for_event(db_engine, identifier)
        assert row is not None

        cur = db_engine.cursor()
        cur.execute("SELECT extra_json FROM security_events WHERE identifier=%s", (identifier,))
        extra_json = cur.fetchone()[0]
        cur.close()
        assert extra_json is not None
        assert "custom_value" in extra_json
        assert "42" in extra_json

        cur = db_engine.cursor()
        cur.execute("DELETE FROM security_events WHERE identifier=%s", (identifier,))
        db_engine.commit(); cur.close()

    def test_error_level_still_persists_alongside_webhook(self, client, db_engine, monkeypatch):
        # send_security_alert is lazily imported inside log_security_event;
        # stub it so this test doesn't attempt a real webhook call.
        import utils.alerts
        monkeypatch.setattr(utils.alerts, "send_security_alert", lambda *a, **kw: None)

        identifier = "TEST_PERSIST_003"
        with client.application.test_request_context("/some/path"):
            log_security_event("test.error_event", "A test ERROR event", level="ERROR",
                                identifier=identifier)

        row = _wait_for_event(db_engine, identifier)
        assert row is not None
        assert row[1] == "ERROR"

        cur = db_engine.cursor()
        cur.execute("DELETE FROM security_events WHERE identifier=%s", (identifier,))
        db_engine.commit(); cur.close()
