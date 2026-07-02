"""
Pytest configuration and fixtures.

Tests run against a real test MySQL database (att_test) to avoid mock/prod
divergence. Requires DB_* env vars pointing to a local MySQL instance.
Set them in .env.test or export before running:

    DB_HOST=localhost DB_USER=root DB_PASS=secret pytest tests/
"""
import os
import pytest

# Point at a dedicated test database so tests never touch production data
os.environ.setdefault("DB_NAME",  "att_test")
os.environ.setdefault("DB_HOST",  "localhost")
os.environ.setdefault("APP_ENV",  "development")   # avoids HTTPS-only cookies
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

# These must be set before importing app so the modules pick them up
import app as _app_module  # noqa: F401 — registers routes + runs init_db logic
from extensions import app as flask_app


@pytest.fixture(scope="session")
def db_engine():
    """Return a raw mysql connection to the test database for fixture setup."""
    import mysql.connector
    conn = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ.get("DB_PASS", ""),
        database=os.environ["DB_NAME"],
        autocommit=True,
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _init_test_db(db_engine):
    """Run init_db() once per test session to set up schema in att_test."""
    with flask_app.app_context():
        from app import init_db
        init_db()


@pytest.fixture
def client():
    flask_app.config["TESTING"]               = True
    flask_app.config["WTF_CSRF_ENABLED"]      = False
    flask_app.config["SESSION_COOKIE_SECURE"] = False
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def seed_admin(db_engine):
    """Insert a test admin user; clean up after the test."""
    from utils.auth import generate_password_hash
    cur = db_engine.cursor()
    cur.execute(
        "INSERT IGNORE INTO admin_users (username, password, email) VALUES (%s,%s,%s)",
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
        "INSERT IGNORE INTO employees (employee_id, name, email, password, force_pin_change) "
        "VALUES (%s,%s,%s,%s,0)",
        ("TST001", "Test Employee", "emp@test.local", generate_password_hash("EmpPass@1")),
    )
    yield {"employee_id": "TST001", "password": "EmpPass@1", "name": "Test Employee"}
    cur.execute("DELETE FROM employees WHERE employee_id='TST001'")
    cur.execute("DELETE FROM api_tokens WHERE identity='TST001'")
    cur.close()
