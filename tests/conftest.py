"""
Pytest configuration and fixtures.

Tests run against a real test PostgreSQL database (att_test) to avoid
mock/prod divergence. Requires DB_* env vars pointing to a local PostgreSQL
instance. Set them in .env.test or export before running:

    DB_HOST=localhost DB_USER=postgres DB_PASS=secret pytest tests/
"""
import os
import pytest

# Load .env first so DB_USER/DB_PASS/DB_PORT come from the real credentials file,
# then force test-specific overrides on top.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

os.environ["DB_NAME"]    = "att_test"   # always use isolated test DB
os.environ["DB_HOST"]    = "localhost"
os.environ["APP_ENV"]    = "development"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", os.getenv("DB_USER", "postgres"))
os.environ.setdefault("DB_PASS", os.getenv("DB_PASS", ""))

# Import app AFTER env vars are set so all module-level reads pick up test values.
# app.py registers all routes on its own Flask `app` instance — use that directly.
import app as _app_module  # noqa: F401 — triggers route registration + init_db
flask_app = _app_module.app   # the real app with all routes registered

# wsgi.py (the real production entrypoint) also registers the migrated
# blueprints (health, notifications) on top of app.py's routes — mirror that
# here since tests import app.py directly and would otherwise miss them.
from blueprints.health import health_bp
from blueprints.notifications import notifications_bp
from blueprints.auth import auth_bp
from blueprints.employees import employees_bp
from blueprints.leave import leave_bp
from blueprints.attendance import attendance_bp
from blueprints.payroll import payroll_bp
flask_app.register_blueprint(health_bp)
flask_app.register_blueprint(notifications_bp)
flask_app.register_blueprint(auth_bp)
flask_app.register_blueprint(employees_bp)
flask_app.register_blueprint(leave_bp)
flask_app.register_blueprint(attendance_bp)
flask_app.register_blueprint(payroll_bp)

# Re-run v1 alias registration so blueprint routes (/api/employees etc.)
# also get /api/v1/* mirrors — the first run in app.py fires before blueprints register.
_app_module._register_api_v1_aliases()

# Disable Flask-Limiter for all tests — its .enabled attribute is set at init
# time (not dynamically from config), so we patch the instance directly.
_app_module.limiter.enabled = False


@pytest.fixture(scope="session")
def db_engine():
    """Return a raw psycopg2 connection to the test database for fixture setup."""
    import psycopg2
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ["DB_USER"],
        password=os.environ.get("DB_PASS", ""),
        dbname=os.environ["DB_NAME"],
    )
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _init_test_db(db_engine):
    """Run init_db() once per test session to set up schema in att_test."""
    with flask_app.app_context():
        from app import init_db
        init_db()
    # Clear transient state tables so stale data from prior runs doesn't bleed in
    cur = db_engine.cursor()
    cur.execute("DELETE FROM login_attempts WHERE 1=1")
    cur.close()


@pytest.fixture
def client():
    flask_app.config["TESTING"]               = True   # disables CSRF check + rate limits
    flask_app.config["WTF_CSRF_ENABLED"]      = False
    flask_app.config["SESSION_COOKIE_SECURE"] = False
    flask_app.config["RATELIMIT_ENABLED"]     = False  # Flask-Limiter 3.x flag
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def seed_admin(db_engine):
    """Insert a test admin user; clean up after the test."""
    from utils.auth import generate_password_hash
    cur = db_engine.cursor()
    cur.execute(
        "INSERT INTO admin_users (username, password, email) VALUES (%s,%s,%s) "
        "ON CONFLICT (username) DO NOTHING",
        ("test_admin", generate_password_hash("Test@1234"), "admin@test.local"),
    )
    yield {"username": "test_admin", "password": "Test@1234"}
    cur.execute("DELETE FROM admin_users WHERE username='test_admin'")
    cur.close()


@pytest.fixture
def seed_employee(db_engine):
    """Insert a test employee; clean up after the test."""
    from utils.auth import generate_password_hash
    cur = db_engine.cursor()
    cur.execute(
        "INSERT INTO employees (employee_id, name, email, password, force_pin_change) "
        "VALUES (%s,%s,%s,%s,0) ON CONFLICT (employee_id) DO NOTHING",
        ("TST001", "Test Employee", "emp@test.local", generate_password_hash("EmpPass@1")),
    )
    yield {"employee_id": "TST001", "password": "EmpPass@1", "name": "Test Employee"}
    cur.execute("DELETE FROM employees WHERE employee_id='TST001'")
    cur.execute("DELETE FROM api_tokens WHERE identity='TST001'")
    cur.close()
