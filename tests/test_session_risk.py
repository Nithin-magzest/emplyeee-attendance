"""Tests for utils/session_risk.py — per-session risk scoring and the
server-side kill-switch check. _evaluate_session_risk_db is called directly
(bypassing the background writer queue in utils/async_writer.py) for
deterministic, synchronous assertions."""
import time
import secrets
import pytest
import utils.session_risk as session_risk
from utils.session_risk import (
    ensure_session_id,
    evaluate_session_risk,
    _evaluate_session_risk_db,
    is_session_compromised,
    _RISK_THRESHOLD,
)


@pytest.fixture
def sid():
    """A fresh session-risk row's key; cleaned up after the test."""
    return secrets.token_hex(16)


@pytest.fixture(autouse=True)
def _cleanup(sid, db_engine):
    yield
    cur = db_engine.cursor()
    cur.execute("DELETE FROM session_risk WHERE sid=%s", (sid,))
    db_engine.commit()
    cur.close()


class TestEnsureSessionId:
    def test_generates_a_new_id_when_absent(self):
        session = {}
        result = ensure_session_id(session)
        assert result == session["_sid"]
        assert len(result) == 32  # secrets.token_hex(16) -> 32 hex chars

    def test_reuses_existing_id(self):
        session = {"_sid": "already-set-value"}
        result = ensure_session_id(session)
        assert result == "already-set-value"

    def test_two_calls_produce_different_ids(self):
        assert ensure_session_id({}) != ensure_session_id({})


class TestEvaluateSessionRiskDb:
    def test_first_event_creates_row_with_score(self, sid):
        score = _evaluate_session_risk_db(sid, "admin1", "admin", 10, "failed login")
        assert score == 10

    def test_score_accumulates_across_events(self, sid):
        _evaluate_session_risk_db(sid, "admin1", "admin", 10, "first")
        score = _evaluate_session_risk_db(sid, "admin1", "admin", 15, "second")
        assert score == 25

    def test_stays_active_below_threshold(self, sid, db_engine):
        _evaluate_session_risk_db(sid, "admin1", "admin", _RISK_THRESHOLD - 1, "just under")
        cur = db_engine.cursor()
        cur.execute("SELECT status FROM session_risk WHERE sid=%s", (sid,))
        status = cur.fetchone()[0]
        cur.close()
        assert status == "active"
        assert is_session_compromised(sid) is False

    def test_crossing_threshold_marks_compromised(self, sid):
        _evaluate_session_risk_db(sid, "admin1", "admin", _RISK_THRESHOLD, "over the line")
        assert is_session_compromised(sid) is True

    def test_last_reason_is_updated_and_truncated(self, sid, db_engine):
        long_reason = "x" * 500
        _evaluate_session_risk_db(sid, "admin1", "admin", 5, long_reason)
        cur = db_engine.cursor()
        cur.execute("SELECT last_reason FROM session_risk WHERE sid=%s", (sid,))
        stored = cur.fetchone()[0]
        cur.close()
        assert len(stored) <= 300

    def test_once_compromised_stays_compromised_even_if_more_events_land(self, sid):
        _evaluate_session_risk_db(sid, "admin1", "admin", _RISK_THRESHOLD, "trip it")
        assert is_session_compromised(sid) is True
        _evaluate_session_risk_db(sid, "admin1", "admin", 1, "another event")
        assert is_session_compromised(sid) is True


class TestIsSessionCompromised:
    def test_unknown_sid_is_not_compromised(self):
        assert is_session_compromised(secrets.token_hex(16)) is False

    def test_empty_sid_is_not_compromised(self):
        assert is_session_compromised("") is False
        assert is_session_compromised(None) is False

    def test_db_failure_fails_open_not_closed(self, sid, monkeypatch):
        """A DB outage in this specific check must not lock every
        legitimate session out of the whole app — see the fail-open
        comment in is_session_compromised itself."""
        def _boom():
            raise RuntimeError("simulated DB outage")
        monkeypatch.setattr(session_risk, "get_db_connection", _boom)
        assert is_session_compromised(sid) is False


class TestEvaluateSessionRiskPublicWrapper:
    def test_enqueues_and_eventually_lands(self, sid):
        """evaluate_session_risk is fire-and-forget via the background
        writer thread — poll briefly for the write to land rather than
        assuming a fixed delay."""
        evaluate_session_risk(sid, "admin1", "admin", _RISK_THRESHOLD, "risk.test", "queued event")
        deadline = time.time() + 2
        while time.time() < deadline:
            if is_session_compromised(sid):
                break
            time.sleep(0.05)
        assert is_session_compromised(sid) is True


class TestEvaluateSessionRiskDbFailure:
    def test_db_failure_returns_zero_and_does_not_raise(self, sid, monkeypatch):
        def _boom():
            raise RuntimeError("simulated DB outage")
        monkeypatch.setattr(session_risk, "get_db_connection", _boom)
        score = _evaluate_session_risk_db(sid, "admin1", "admin", 10, "db is down")
        assert score == 0
