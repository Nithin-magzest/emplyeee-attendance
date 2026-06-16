import os
import time
import mysql.connector
import mysql.connector.pooling
from dotenv import load_dotenv

load_dotenv()

_pool = None

_DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "employee_attendance"),
)

def _create_pool(retries=5, delay=3):
    global _pool
    for attempt in range(1, retries + 1):
        try:
            _pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="att_pool",
                pool_size=20,
                **_DB_CONFIG,
            )
            print(f"[DB] Connected to MySQL (attempt {attempt})")
            return
        except mysql.connector.Error as e:
            print(f"[DB] MySQL not ready (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("[DB] Could not connect to MySQL after several retries. Is MySQL running?")

def get_db_connection():
    global _pool
    if _pool is None:
        _create_pool()
    try:
        return _pool.get_connection()
    except mysql.connector.Error:
        # Pool went stale — rebuild it once and retry
        _pool = None
        _create_pool(retries=3, delay=2)
        return _pool.get_connection()
