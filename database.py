import os
import re
import time
import logging
import mysql.connector
import mysql.connector.pooling
from dotenv import load_dotenv

load_dotenv()

_log = logging.getLogger("attendance")
# Logger is configured in app.py; database.py uses the same named logger so
# output is consistent without adding a second handler here.

_DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "employee_attendance"),
)

# ── Default tenant pool ──────────────────────────────────────────────────────
_pool = None

def _create_pool(retries=5, delay=3):
    global _pool
    for attempt in range(1, retries + 1):
        try:
            _pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="att_pool",
                pool_size=20,
                **_DB_CONFIG,
            )
            _log.info('"Connected to MySQL (attempt %d)"', attempt)
            return
        except mysql.connector.Error as e:
            _log.warning('"MySQL not ready (attempt %d/%d): %s"', attempt, retries, e)
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("[DB] Could not connect to MySQL after several retries. Is MySQL running?")


def get_db_connection():
    """Return a connection for the current tenant (or the default DB).

    Checks flask.g.tenant_db if Flask is active, then falls back to the DB_NAME
    env var.  Import of flask.g is done lazily to avoid circular imports.
    """
    global _pool

    # Determine target DB name
    tenant_db = None
    try:
        from flask import g as _flask_g
        tenant_db = getattr(_flask_g, "tenant_db", None)
    except RuntimeError:
        # Outside of a Flask application context — skip g lookup
        pass

    target_db = tenant_db or os.environ.get("DB_NAME", "employee_attendance")

    if _pool is None:
        _create_pool()

    try:
        conn = _pool.get_connection()
    except mysql.connector.Error:
        # Pool went stale — rebuild it once and retry
        _pool = None
        _create_pool(retries=3, delay=2)
        conn = _pool.get_connection()

    # If the target differs from the pool's default DB, switch databases
    default_db = _DB_CONFIG.get("database", "")
    if target_db and target_db != default_db:
        # Validate db name before using in SQL to prevent injection
        if not re.match(r'^[a-zA-Z0-9_]+$', target_db):
            raise ValueError(f"Invalid tenant database name: {target_db!r}")
        cur = conn.cursor()
        cur.execute(f"USE `{target_db}`")
        cur.close()

    return conn


# ── Master DB (tenant registry) ──────────────────────────────────────────────
_master_pool = None
_MASTER_DB_NAME = "att_master"

def _create_master_pool(retries=5, delay=3):
    global _master_pool
    master_cfg = dict(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=_MASTER_DB_NAME,
    )
    for attempt in range(1, retries + 1):
        try:
            _master_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="att_master_pool",
                pool_size=5,
                **master_cfg,
            )
            _log.info('"Connected to master DB att_master (attempt %d)"', attempt)
            return
        except mysql.connector.Error as e:
            _log.warning('"Master DB not ready (attempt %d/%d): %s"', attempt, retries, e)
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("[DB] Could not connect to att_master database.")


def get_master_db():
    """Return a connection to the att_master tenant-registry database."""
    global _master_pool
    if _master_pool is None:
        _create_master_pool()
    try:
        return _master_pool.get_connection()
    except mysql.connector.Error:
        _master_pool = None
        _create_master_pool(retries=3, delay=2)
        return _master_pool.get_connection()


# ── Tenant DB helper ─────────────────────────────────────────────────────────

def get_tenant_db(db_name: str):
    """Return a pooled connection switched to the given tenant database.

    The db_name is validated against ^[a-zA-Z0-9_]+$ before being used in SQL.
    """
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        raise ValueError(f"Invalid tenant database name: {db_name!r}")
    global _pool
    if _pool is None:
        _create_pool()
    try:
        conn = _pool.get_connection()
    except mysql.connector.Error:
        _pool = None
        _create_pool(retries=3, delay=2)
        conn = _pool.get_connection()
    cur = conn.cursor()
    cur.execute(f"USE `{db_name}`")
    cur.close()
    return conn


# ── Tenant database provisioning ─────────────────────────────────────────────

def create_tenant_database(db_name: str):
    """Create a new tenant database using a root connection (no pool).

    Validates db_name before use.
    """
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        raise ValueError(f"Invalid tenant database name: {db_name!r}")
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    cur.close()
    conn.close()
    _log.info('"Created tenant database: %s"', db_name)
