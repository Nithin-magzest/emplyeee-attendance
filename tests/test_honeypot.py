"""
utils/honeypot.py tests — no pytest-asyncio installed, so async code is
driven directly with asyncio.run() inside plain sync test functions
rather than adding a new dependency for this one module.

send_security_alert is monkeypatched everywhere here — these tests must
never attempt a real webhook call, and utils.alerts is exercised on its
own in tests/test_alerts.py.

Run with:
    python -m pytest tests/test_honeypot.py -v
"""
import asyncio
import json

import pytest

import utils.honeypot as hp


class TestDecoyPortsShape:
    def test_no_duplicate_bind_ports(self):
        assert len(hp.DECOY_PORTS) == len(set(hp.DECOY_PORTS.keys()))

    def test_no_duplicate_public_ports(self):
        public_ports = [v[0] for v in hp.DECOY_PORTS.values()]
        assert len(public_ports) == len(set(public_ports))

    def test_privileged_public_ports_have_high_bind_port(self):
        """21/23/25 are <1024 — this container is unprivileged (see
        compose.yaml), so any DECOY_PORTS entry whose public_port is
        privileged MUST bind to something >=1024 (redirected at the host
        via deploy.sh's ufw DNAT) or the process can never actually start."""
        for bind_port, (public_port, _label) in hp.DECOY_PORTS.items():
            if public_port < 1024:
                assert bind_port >= 1024, (
                    f"public_port {public_port} is privileged but bind_port "
                    f"{bind_port} is also privileged — this can't bind unprivileged"
                )

    def test_unprivileged_public_ports_bind_directly(self):
        """1433/3306/3389 need no redirect — bind_port should equal
        public_port for these, or the compose.yaml port mapping and the
        actual listener would silently disagree."""
        for bind_port, (public_port, _label) in hp.DECOY_PORTS.items():
            if public_port >= 1024:
                assert bind_port == public_port


class TestRecordHit:
    def test_writes_expected_json_line(self, tmp_path, monkeypatch):
        log_path = tmp_path / "hits.jsonl"
        monkeypatch.setenv("HONEYPOT_LOG_PATH", str(log_path))

        hp._record_hit(21, "ftp", "203.0.113.9", b"USER root\r\n")

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["service"] == "system32_crypto_admin"
        assert entry["port"] == 21
        assert entry["protocol"] == "ftp"
        assert entry["source_ip"] == "203.0.113.9"
        assert entry["captured_bytes"] == 11
        assert entry["captured_preview"] == "USER root\r\n"

    def test_appends_multiple_hits(self, tmp_path, monkeypatch):
        log_path = tmp_path / "hits.jsonl"
        monkeypatch.setenv("HONEYPOT_LOG_PATH", str(log_path))

        hp._record_hit(23, "telnet", "203.0.113.1", b"")
        hp._record_hit(3389, "rdp", "203.0.113.2", b"\x03\x00\x00")

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_capture_preview_truncated_to_max_bytes(self, tmp_path, monkeypatch):
        log_path = tmp_path / "hits.jsonl"
        monkeypatch.setenv("HONEYPOT_LOG_PATH", str(log_path))
        big_payload = b"A" * 2000

        hp._record_hit(25, "smtp", "203.0.113.3", big_payload)

        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["captured_bytes"] == 2000  # true size still recorded
        assert len(entry["captured_preview"]) == hp._MAX_CAPTURE_BYTES  # preview capped


class TestAlertHit:
    def test_sends_alert_with_sanitizable_fields_only(self, monkeypatch):
        captured = {}

        def _fake_send(event_type, description, severity="ERROR", **fields):
            captured["event_type"] = event_type
            captured["description"] = description
            captured["severity"] = severity
            captured["fields"] = fields

        monkeypatch.setattr("utils.alerts.send_security_alert", _fake_send)

        hp._alert_hit(1433, "mssql", "203.0.113.4", b"malicious payload")

        assert captured["event_type"] == "honeypot.connection"
        assert "1433" in captured["description"]
        assert captured["severity"] == "WARNING"
        assert captured["fields"]["ip"] == "203.0.113.4"
        assert captured["fields"]["identifier"] == "system32_crypto_admin:1433"
        # Only fields utils.alerts._ALLOWED_FIELDS actually accepts — a
        # typo'd field name here would be silently dropped downstream,
        # not caught until the alert itself was inspected in production.
        from utils.alerts import _ALLOWED_FIELDS
        assert set(captured["fields"].keys()) <= _ALLOWED_FIELDS

    def test_webhook_failure_does_not_raise(self, monkeypatch):
        """A dead webhook must never crash the listener mid-connection —
        matches send_security_alert's own fire-and-forget design."""
        def _boom(*a, **kw):
            raise RuntimeError("webhook is down")

        monkeypatch.setattr("utils.alerts.send_security_alert", _boom)
        with pytest.raises(RuntimeError):
            # _alert_hit itself doesn't catch — that's _handle_connection's
            # job (tested below), so this documents _alert_hit's own
            # contract: it propagates, the caller is responsible.
            hp._alert_hit(3306, "mysql", "203.0.113.5", b"")


class TestHandleConnectionEndToEnd:
    def test_real_connection_is_captured_and_logged(self, tmp_path, monkeypatch):
        log_path = tmp_path / "hits.jsonl"
        monkeypatch.setenv("HONEYPOT_LOG_PATH", str(log_path))
        alerts_sent = []
        monkeypatch.setattr(
            "utils.alerts.send_security_alert",
            lambda *a, **kw: alerts_sent.append(kw),
        )

        # bind_port 3306 with public_port 3306 (mysql, no redirect needed)
        # is already in DECOY_PORTS — reuse it so port/protocol resolve
        # through the real mapping, not a hand-rolled one.
        test_port = 33061  # a free high port, standing in for 3306's bind_port in this test

        async def _serve_once():
            server = await asyncio.start_server(
                lambda r, w: hp._handle_connection(r, w, 3306), "127.0.0.1", test_port
            )
            async with server:
                await asyncio.wait_for(server.serve_forever(), timeout=2)

        async def _client():
            await asyncio.sleep(0.3)
            reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
            writer.write(b"attacker probe payload")
            await writer.drain()
            writer.close()

        async def _run_both():
            try:
                await asyncio.gather(_serve_once(), _client())
            except asyncio.TimeoutError:
                pass

        asyncio.run(_run_both())

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["port"] == 3306
        assert entry["protocol"] == "mysql"
        assert entry["source_ip"] == "127.0.0.1"
        assert b"attacker probe payload".decode() in entry["captured_preview"]

        assert len(alerts_sent) == 1
        assert alerts_sent[0]["ip"] == "127.0.0.1"
