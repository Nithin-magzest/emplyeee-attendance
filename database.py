import os
from dotenv import load_dotenv
import mysql.connector.pooling

load_dotenv()

_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="att_pool",
    pool_size=5,
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "employee_attendance"),
)

def get_db_connection():
    return _pool.get_connection()
