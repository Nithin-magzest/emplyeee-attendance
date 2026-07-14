"""Shared Flask extensions — imported by blueprints to avoid circular imports."""
import os
import logging
import sys
import secrets
import warnings
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pythonjsonlogger import jsonlogger

# ── Logging ──────────────────────────────────────────────────────────────────
_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(module)s %(message)s",
    rename_fields={"asctime": "time", "levelname": "level"},
))
app_log = logging.getLogger("attendance")
if not app_log.handlers:
    app_log.addHandler(_log_handler)
app_log.setLevel(logging.INFO)
app_log.propagate = False

# ── Structured security-event logging ──────────────────────────────────────
# Distinct from routine app_log.info/warning/error calls: every event logged
# here is tagged security_event=true with a short event_type slug (e.g.
# "auth.failure", "access.denied", "validation.failure"), so a log
# pipeline/SIEM can filter and alert on these without regex-parsing
# free-text messages.
#
# Log injection note: JsonFormatter renders each call as one JSON object —
# control characters (newlines, quotes) inside any field value are escaped
# by the JSON encoder, so attacker-controlled data can't split a line into
# a second forged record the way it could against a naive plain-text
# logger. Even so, always pass variable/attacker-controlled data as `extra`
# fields rather than interpolating it into `message` itself — keeping the
# message a fixed, code-controlled string means a hostile value can never
# be mistaken for log-formatting content by anything downstream that
# treats `message` as free text, independent of the JSON-encoding safety
# net.
_SECURITY_LOG_LEVELS = {
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

# Python's LogRecord already owns these attribute names — passing any of
# them through `extra=` raises KeyError("Attempt to overwrite ... in
# LogRecord") and crashes the *caller*, not just the log call. Discovered
# the hard way: utils/helpers.py's upload validators passed filename=...,
# which collided with LogRecord's own `filename` (the source .py file of
# the log call site) and turned every rejected upload into a 500 instead
# of a clean error message. Fixed at those call sites, but also guarded
# here so no future caller can reintroduce the same crash with a
# differently-named collision (module, process, thread, ...).
_LOGRECORD_RESERVED = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
})

def log_security_event(event_type: str, message: str, level: str = "WARNING", **fields):
    """Emit a structured security-relevant log event.

    event_type: short dotted slug identifying the event class — the thing a
    SIEM rule filters on (e.g. "auth.failure", "access.denied").
    fields: structured context (identifier, reason, ...) merged into the
    JSON record. Never put attacker-controlled values into `message` —
    pass them as fields instead. Field names colliding with a reserved
    LogRecord attribute (see _LOGRECORD_RESERVED) are auto-prefixed with
    `field_` rather than raising — pick a different name at the call site
    when you see one show up prefixed like that in the logs.
    """
    try:
        from flask import request as _req
        ip, path, method = _req.remote_addr, _req.path, _req.method
    except Exception:
        ip = path = method = None
    safe_fields = {
        (f"field_{k}" if k in _LOGRECORD_RESERVED else k): v
        for k, v in fields.items()
    }
    app_log.log(
        _SECURITY_LOG_LEVELS.get(level.upper(), logging.WARNING),
        message,
        extra={"security_event": True, "event_type": event_type,
               "ip": ip, "path": path, "method": method, **safe_fields},
    )
    # ERROR-level security events get a real-time webhook alert on top of
    # the log line — lockouts, malware detections, injection-shaped input,
    # privilege-escalation attempts. INFO/WARNING stay log-only; paging a
    # human for every anonymous 401 would make the channel worth ignoring.
    # Lazy import: utils/alerts.py imports app_log from this module, so
    # importing it at module load time here would be circular.
    if level.upper() == "ERROR":
        from utils.alerts import send_security_alert
        send_security_alert(event_type, message, level="ERROR",
                             ip=ip, path=path, method=method, **fields)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")

# Secret key: env var → persisted local file → generated once
_env_key = os.environ.get("SECRET_KEY", "").strip()
if _env_key:
    app.secret_key = _env_key
else:
    _key_file = os.path.join(os.path.dirname(__file__), ".secret_key")
    if os.path.exists(_key_file):
        with open(_key_file) as _f:
            app.secret_key = _f.read().strip()
    else:
        app.secret_key = secrets.token_hex(32)
        with open(_key_file, "w") as _f:
            _f.write(app.secret_key)
        try:
            os.chmod(_key_file, 0o600)
        except Exception:
            pass

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"]   = os.environ.get("APP_ENV", "production") != "development"
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["PERMANENT_SESSION_LIFETIME"] = 28800  # 8 hours

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB — guards direct access without nginx
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
_app_env     = os.environ.get("APP_ENV", "production")
if not _raw_origins:
    if _app_env != "development":
        app_log.critical(
            "ALLOWED_ORIGINS is not configured — CORS set to deny-all for /api/*. "
            "Set ALLOWED_ORIGINS=https://yourdomain.com in .env."
        )
        warnings.warn(
            "ALLOWED_ORIGINS is unset in production — CORS set to deny-all for /api/*.",
            stacklevel=1,
        )
    _allowed_origins = "*" if _app_env == "development" else []
elif _raw_origins == "*":
    if _app_env != "development":
        app_log.warning(
            "ALLOWED_ORIGINS='*' in production allows all origins for /api/*. "
            "Restrict it to your domain(s)."
        )
        warnings.warn("ALLOWED_ORIGINS='*' in production — all origins allowed.", stacklevel=1)
    _allowed_origins = "*"
else:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
CORS(app, resources={r"/api/*": {"origins": _allowed_origins}})

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    default_limits=["300 per minute"],
)
