"""Tests for utils/ai_assistant.py (the employee chat assistant's context
builder + Claude call) and the /api/employee/chat route in
blueprints/employee_portal.py.

The real Anthropic API is never called here — `_call_claude` (the raw
urllib.request layer) is monkeypatched in `ask_assistant` tests, and the
route tests monkeypatch `ask_assistant` itself, matching the existing
convention of not mocking the code under test but isolating the
third-party network call (see tests/test_face_utils.py)."""
import utils.ai_assistant as ai_assistant
import blueprints.employee_portal as employee_portal_module
from utils.ai_assistant import (
    build_employee_context, ask_assistant, _sanitize_history, MAX_MESSAGE_LEN,
)


class TestBuildEmployeeContext:
    def test_includes_basic_profile_fields(self, db_engine, seed_employee):
        cur = db_engine.cursor()
        context = build_employee_context(cur, seed_employee["employee_id"])
        cur.close()
        assert seed_employee["employee_id"] in context
        assert seed_employee["name"] in context

    def test_unknown_employee_returns_not_found_message(self, db_engine):
        cur = db_engine.cursor()
        context = build_employee_context(cur, "NO_SUCH_EMP")
        cur.close()
        assert "No employee record found" in context

    def test_does_not_crash_with_no_leave_or_attendance_history(self, db_engine, seed_employee):
        cur = db_engine.cursor()
        context = build_employee_context(cur, seed_employee["employee_id"])
        cur.close()
        assert isinstance(context, str) and len(context) > 0


class TestSanitizeHistory:
    def test_keeps_well_formed_turns(self):
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        assert _sanitize_history(history) == history

    def test_drops_malformed_entries(self):
        history = [
            {"role": "user", "content": "ok"},
            {"role": "system", "content": "should be dropped"},
            {"role": "user", "content": 12345},
            "not-a-dict",
            {"content": "missing role"},
        ]
        result = _sanitize_history(history)
        assert result == [{"role": "user", "content": "ok"}]

    def test_truncates_long_content(self):
        long_text = "x" * (MAX_MESSAGE_LEN + 500)
        result = _sanitize_history([{"role": "user", "content": long_text}])
        assert len(result[0]["content"]) == MAX_MESSAGE_LEN

    def test_caps_to_max_history_turns(self):
        history = [{"role": "user", "content": str(i)} for i in range(20)]
        result = _sanitize_history(history)
        assert len(result) == ai_assistant.MAX_HISTORY_TURNS
        assert result[-1]["content"] == "19"

    def test_none_history_returns_empty(self):
        assert _sanitize_history(None) == []


class TestAskAssistant:
    def test_empty_message_rejected(self):
        ok, reply = ask_assistant("some context", "   ")
        assert ok is False
        assert "type a question" in reply.lower()

    def test_overlong_message_rejected(self):
        ok, reply = ask_assistant("ctx", "x" * (MAX_MESSAGE_LEN + 1))
        assert ok is False
        assert "too long" in reply.lower()

    def test_missing_api_key_returns_friendly_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ok, reply = ask_assistant("ctx", "How many leave days do I have?")
        assert ok is False
        assert "isn't configured" in reply.lower()

    def test_successful_call_returns_model_text(self, monkeypatch):
        def _fake_call(system_prompt, messages):
            assert system_prompt.startswith("You are the HR assistant")
            assert messages[-1] == {"role": "user", "content": "How many leave days do I have?"}
            return "You have 5 leave days remaining.", None

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_assistant, "_call_claude", _fake_call)
        ok, reply = ask_assistant("Leave balance: 5 days", "How many leave days do I have?")
        assert ok is True
        assert reply == "You have 5 leave days remaining."

    def test_api_failure_returns_friendly_error_not_exception(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_assistant, "_call_claude", lambda s, m: (None, "network error: simulated outage"))
        ok, reply = ask_assistant("ctx", "hello")
        assert ok is False
        assert "couldn't reach" in reply.lower()

    def test_history_passed_through_to_messages(self, monkeypatch):
        captured = {}

        def _fake_call(system_prompt, messages):
            captured["messages"] = messages
            return "ok", None

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_assistant, "_call_claude", _fake_call)
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello there"}]
        ask_assistant("ctx", "follow-up question", history)
        assert captured["messages"][0] == {"role": "user", "content": "hi"}
        assert captured["messages"][-1] == {"role": "user", "content": "follow-up question"}

    def test_real_http_call_hits_urlopen_with_expected_request(self, monkeypatch):
        """One test exercises _call_claude itself (not ask_assistant), mocking
        only urllib.request.urlopen — the actual network boundary — to prove
        the request is built correctly (headers, model, message shape)."""
        import json as _json

        captured = {}

        class _FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False

            def read(self):
                return _json.dumps({"content": [{"type": "text", "text": "Hi there!"}]}).encode()

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
            captured["body"] = _json.loads(req.data.decode())
            return _FakeResp()

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
        monkeypatch.setattr(ai_assistant.urllib.request, "urlopen", _fake_urlopen)
        text, err = ai_assistant._call_claude("system prompt", [{"role": "user", "content": "hi"}])
        assert err is None
        assert text == "Hi there!"
        assert captured["url"] == "https://api.anthropic.com/v1/messages"
        assert captured["headers"]["x-api-key"] == "sk-test-123"
        assert captured["body"]["model"] == "claude-sonnet-5"
        assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]


class TestChatRoute:
    def test_requires_employee_login(self, client):
        resp = client.post("/api/employee/chat", json={"message": "hi"}, follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_returns_assistant_reply_when_logged_in(self, client, seed_employee, monkeypatch):
        with client.session_transaction() as sess:
            sess["employee_id"] = seed_employee["employee_id"]

        monkeypatch.setattr(employee_portal_module, "ask_assistant", lambda context, message, history: (True, "Mocked reply"))

        resp = client.post("/api/employee/chat", json={"message": "How much leave do I have?"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["reply"] == "Mocked reply"

    def test_invalid_message_type_rejected(self, client, seed_employee):
        with client.session_transaction() as sess:
            sess["employee_id"] = seed_employee["employee_id"]
        resp = client.post("/api/employee/chat", json={"message": ["not", "a", "string"]})
        assert resp.status_code == 400

    def test_non_list_history_is_ignored_not_crashed(self, client, seed_employee, monkeypatch):
        with client.session_transaction() as sess:
            sess["employee_id"] = seed_employee["employee_id"]

        captured = {}

        def _fake_ask(context, message, history):
            captured["history"] = history
            return True, "ok"

        monkeypatch.setattr(employee_portal_module, "ask_assistant", _fake_ask)
        resp = client.post("/api/employee/chat", json={"message": "hi", "history": "not-a-list"})
        assert resp.status_code == 200
        assert captured["history"] == []
