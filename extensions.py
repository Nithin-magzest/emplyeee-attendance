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

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")

# Secret key: env var → persisted local file → generated once
_env_key = os.environ.get("SECRET_KEY", "").strip()
if _env_key:
    app.secret_key = _env_key
else:
    _key_file = os.path.join(os.path.dirname(__file__), "hashi", ".secret_key")
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
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
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
