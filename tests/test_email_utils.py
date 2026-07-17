"""Unit tests for utils/email_utils.py — SMTP config resolution, message
building/escaping, the DB-backed send queue, and new-login-IP notification
logic. The infinite-loop background worker (_email_queue_worker) is not
exercised here — it has no meaningful unit-testable boundary short of
either mocking away `while True` or opening a real SMTP connection.
"""
import utils.email_utils as email_utils


def _raise(*_a, **_k):
    raise RuntimeError("db down")


class TestGetEmailConfig:
    def test_db_row_found_decrypts_password(self, db_engine):
        from utils.helpers import encrypt_pii
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO email_config (smtp_host, smtp_port, smtp_user, smtp_pass, from_name, from_email) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            ("smtp.example.com", 587, "bot@example.com", encrypt_pii("s3cret"), "Bot", "bot@example.com"),
        )
        try:
            cfg = email_utils.get_email_config()
            assert cfg["host"] == "smtp.example.com"
            assert cfg["password"] == "s3cret"
            assert cfg["from_email"] == "bot@example.com"
        finally:
            cur.execute("DELETE FROM email_config WHERE smtp_user='bot@example.com'")
            cur.close()

    def test_falls_back_to_env_when_db_unavailable(self, monkeypatch):
        monkeypatch.setattr(email_utils, "get_db_connection", _raise)
        monkeypatch.setenv("SMTP_HOST", "smtp.env.test")
        monkeypatch.setenv("SMTP_USER", "envuser")
        monkeypatch.setenv("SMTP_PASS", "envpass")
        cfg = email_utils.get_email_config()
        assert cfg["host"] == "smtp.env.test"
        assert cfg["password"] == "envpass"

    def test_returns_none_when_nothing_configured(self, monkeypatch):
        monkeypatch.setattr(email_utils, "get_db_connection", _raise)
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASS", raising=False)
        assert email_utils.get_email_config() is None


class TestGetAdminEmails:
    def test_returns_emails_with_non_null_email(self, db_engine):
        from utils.auth import generate_password_hash
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO admin_users (username, password, email) VALUES (%s,%s,%s) "
            "ON CONFLICT (username) DO NOTHING",
            ("helper_email_admin", generate_password_hash("Test@1234"), "helperadmin@test.local"),
        )
        try:
            emails = email_utils.get_admin_emails()
            assert "helperadmin@test.local" in emails
        finally:
            cur.execute("DELETE FROM admin_users WHERE username='helper_email_admin'")
            cur.close()


class _FakeSmtpServer:
    def __init__(self):
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self):
        self.events.append("ehlo")

    def starttls(self, context=None):
        self.events.append("starttls")

    def login(self, u, p):
        self.events.append(("login", u, p))

    def sendmail(self, from_addr, to_addr, msg_str):
        self.events.append(("sendmail", from_addr, to_addr, msg_str))


class TestSendEmailSmtp:
    def test_starttls_path_used_for_non_ssl_port(self, monkeypatch):
        server = _FakeSmtpServer()
        monkeypatch.setattr(email_utils.smtplib, "SMTP", lambda host, port, timeout=20: server)
        cfg = {"host": "smtp.x.com", "port": 587, "user": "u", "password": "p",
               "from_name": "N", "from_email": "u@x.com"}
        email_utils.send_email_smtp("to@example.com", "Hi", "<p>body</p>", cfg)
        assert "starttls" in server.events
        assert ("login", "u", "p") in server.events

    def test_ssl_path_used_for_port_465(self, monkeypatch):
        server = _FakeSmtpServer()
        monkeypatch.setattr(email_utils.smtplib, "SMTP_SSL", lambda host, port, context=None, timeout=20: server)
        cfg = {"host": "smtp.x.com", "port": 465, "user": "u", "password": "p",
               "from_name": "N", "from_email": "u@x.com"}
        email_utils.send_email_smtp("to@example.com", "Hi", "<p>body</p>", cfg)
        assert any(e[0] == "sendmail" for e in server.events if isinstance(e, tuple))
        assert "starttls" not in server.events

    def test_attachment_is_attached_with_correct_filename(self, monkeypatch):
        server = _FakeSmtpServer()
        monkeypatch.setattr(email_utils.smtplib, "SMTP", lambda host, port, timeout=20: server)
        cfg = {"host": "smtp.x.com", "port": 587, "user": "u", "password": "p",
               "from_name": "N", "from_email": "u@x.com"}
        email_utils.send_email_smtp("to@example.com", "Hi", "<p>body</p>", cfg,
                                    attachment_bytes=b"PDFDATA", attachment_filename="report.pdf")
        sendmail_call = next(e for e in server.events if isinstance(e, tuple) and e[0] == "sendmail")
        msg_str = sendmail_call[3]
        assert 'filename="report.pdf"' in msg_str
        assert "Content-Disposition" in msg_str


class TestSendEmailAsync:
    def test_enqueues_row_on_success(self, db_engine):
        cfg = {"host": "x", "port": 587, "user": "a@b.com", "password": "p",
               "from_name": "N", "from_email": "a@b.com"}
        email_utils.send_email_async("to@example.com", "Helper Subj", "<p>hi</p>", cfg)
        cur = db_engine.cursor()
        cur.execute("SELECT to_email, subject FROM email_queue WHERE subject='Helper Subj'")
        row = cur.fetchone()
        cur.execute("DELETE FROM email_queue WHERE subject='Helper Subj'")
        cur.close()
        assert row == ("to@example.com", "Helper Subj")

    def test_falls_back_to_direct_send_thread_on_db_error(self, monkeypatch):
        monkeypatch.setattr(email_utils, "get_db_connection", _raise)
        calls = []

        class _SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        monkeypatch.setattr(email_utils.threading, "Thread", _SyncThread)
        monkeypatch.setattr(email_utils, "send_email_smtp", lambda *a, **k: calls.append((a, k)))
        cfg = {"host": "x", "port": 587, "user": "a@b.com", "password": "p",
               "from_name": "N", "from_email": "a@b.com"}
        email_utils.send_email_async("to@example.com", "Helper Subj2", "<p>hi</p>", cfg)
        assert len(calls) == 1


class TestBuildNewIpLoginEmail:
    def test_escapes_html_in_untrusted_fields(self):
        html_out = email_utils.build_new_ip_login_email("<script>Bad</script>", "emp1", "1.2.3.4", "1 Jan 2026")
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out

    def test_includes_ip_and_time(self):
        html_out = email_utils.build_new_ip_login_email("Alice", "emp1", "1.2.3.4", "1 Jan 2026, 10:00 AM")
        assert "1.2.3.4" in html_out
        assert "1 Jan 2026, 10:00 AM" in html_out


class TestBuildAttendanceEmail:
    def test_login_action_uses_checked_in_label(self):
        html_out = email_utils.build_attendance_email("Bob", "EMP1", "login", "On Time", "09:00", "2026-01-01")
        assert "Checked In" in html_out
        assert "#16a34a" in html_out

    def test_logout_action_uses_checked_out_label(self):
        html_out = email_utils.build_attendance_email("Bob", "EMP1", "logout", "On Time", "18:00", "2026-01-01")
        assert "Checked Out" in html_out
        assert "#2563eb" in html_out


class TestNotifyIfNewLoginIp:
    def _clear(self, db_engine, identifier):
        cur = db_engine.cursor()
        cur.execute("DELETE FROM known_login_ips WHERE identifier=%s", (identifier,))
        cur.close()

    def test_noop_without_ip_or_email(self, monkeypatch):
        def _fail(*a, **k):
            raise AssertionError("send_email_async should not be called")
        monkeypatch.setattr(email_utils, "send_email_async", _fail)
        email_utils.notify_if_new_login_ip("helper_noop", "admin", None, "Name", "a@b.com")
        email_utils.notify_if_new_login_ip("helper_noop", "admin", "1.2.3.4", "Name", None)

    def test_first_ever_login_records_but_does_not_email(self, db_engine, monkeypatch):
        identifier = "helper_notify_first"
        self._clear(db_engine, identifier)
        called = []
        monkeypatch.setattr(email_utils, "send_email_async", lambda *a, **k: called.append(1))
        try:
            email_utils.notify_if_new_login_ip(identifier, "admin", "1.1.1.1", "Name", "a@b.com")
            assert called == []
            cur = db_engine.cursor()
            cur.execute("SELECT ip_address FROM known_login_ips WHERE identifier=%s", (identifier,))
            assert cur.fetchone() == ("1.1.1.1",)
            cur.close()
        finally:
            self._clear(db_engine, identifier)

    def test_new_ip_after_established_history_triggers_email(self, db_engine, monkeypatch):
        identifier = "helper_notify_second"
        self._clear(db_engine, identifier)
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO known_login_ips (identifier, attempt_type, ip_address) VALUES (%s,%s,%s)",
            (identifier, "admin", "1.1.1.1"),
        )
        cur.close()
        called = []
        monkeypatch.setattr(email_utils, "send_email_async", lambda *a, **k: called.append(a))
        monkeypatch.setattr(email_utils, "get_email_config", lambda: {
            "host": "x", "port": 587, "user": "u", "password": "p",
            "from_name": "N", "from_email": "u@x.com",
        })
        try:
            email_utils.notify_if_new_login_ip(identifier, "admin", "2.2.2.2", "Name", "a@b.com")
            assert len(called) == 1
        finally:
            self._clear(db_engine, identifier)

    def test_already_known_ip_does_not_email(self, db_engine, monkeypatch):
        identifier = "helper_notify_known"
        self._clear(db_engine, identifier)
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO known_login_ips (identifier, attempt_type, ip_address) VALUES (%s,%s,%s)",
            (identifier, "admin", "1.1.1.1"),
        )
        cur.execute(
            "INSERT INTO known_login_ips (identifier, attempt_type, ip_address) VALUES (%s,%s,%s)",
            (identifier, "admin", "2.2.2.2"),
        )
        cur.close()
        called = []
        monkeypatch.setattr(email_utils, "send_email_async", lambda *a, **k: called.append(a))
        try:
            email_utils.notify_if_new_login_ip(identifier, "admin", "1.1.1.1", "Name", "a@b.com")
            assert called == []
        finally:
            self._clear(db_engine, identifier)

    def test_no_email_config_skips_send(self, db_engine, monkeypatch):
        identifier = "helper_notify_noconfig"
        self._clear(db_engine, identifier)
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO known_login_ips (identifier, attempt_type, ip_address) VALUES (%s,%s,%s)",
            (identifier, "admin", "1.1.1.1"),
        )
        cur.close()
        called = []
        monkeypatch.setattr(email_utils, "send_email_async", lambda *a, **k: called.append(a))
        monkeypatch.setattr(email_utils, "get_email_config", lambda: None)
        try:
            email_utils.notify_if_new_login_ip(identifier, "admin", "3.3.3.3", "Name", "a@b.com")
            assert called == []
        finally:
            self._clear(db_engine, identifier)

    def test_db_error_is_swallowed(self, monkeypatch):
        monkeypatch.setattr(email_utils, "get_db_connection", _raise)
        email_utils.notify_if_new_login_ip("helper_notify_err", "admin", "9.9.9.9", "Name", "a@b.com")
