"""Attendance calculation helpers."""
import datetime
import calendar
from database import get_db_connection
import utils.config as cfg


def _td_to_time(val):
    if val is None:
        return None
    if isinstance(val, datetime.time):
        return val
    total = int(val.total_seconds())
    h, rem = divmod(total, 3600)
    m, s   = divmod(rem, 60)
    return datetime.time(h % 24, m, s)


def get_employee_shift(emp_id, cursor):
    cursor.execute(
        "SELECT s.start_time, s.half_time, s.end_time, s.name "
        "FROM employees e JOIN shifts s ON e.shift_id = s.id "
        "WHERE e.employee_id = %s",
        (emp_id,)
    )
    row = cursor.fetchone()
    if row:
        return _td_to_time(row[0]), _td_to_time(row[1]), _td_to_time(row[2]), row[3]
    return cfg.SHIFT_START, cfg.SHIFT_HALF, cfg.SHIFT_END, "Default"


def get_attendance_type(login_status, logout_status):
    if not login_status:
        return "Absent"
    if not logout_status:
        return "Half Day" if login_status == "Half Day Login" else "Present"
    if login_status == "Half Day Login":
        return "Half Day"
    if logout_status in ("Half Day Logout", "Early Logout"):
        return "Half Day"
    if login_status == "Late Login":
        return "Late - Full Day"
    return "Full Day"


def classify_by_worked_minutes(login_status, total_minutes, s_start, s_end):
    today_d    = datetime.date.today()
    shift_mins = max(1, int((
        datetime.datetime.combine(today_d, s_end) -
        datetime.datetime.combine(today_d, s_start)
    ).total_seconds() / 60))
    if total_minutes >= shift_mins * 0.75:
        return "Late - Full Day" if login_status == "Late Login" else "Full Day"
    return "Half Day"


def calculate_deduction(salary_per_day, attendance_type):
    spd = float(salary_per_day)
    if attendance_type == "Full Day":
        return 0.0
    if attendance_type == "Approved Leave":
        return spd if cfg.LEAVE_PAY == "absent" else 0.0
    if attendance_type == "Holiday":
        return spd if cfg.HOLIDAY_PAY == "unpaid" else 0.0
    if attendance_type == "Late - Full Day":
        return round(spd * cfg.LATE_DEDUCTION_RATE, 2)
    if attendance_type in ("Half Day", "Present"):
        return round(spd * cfg.HALF_DAY_RATE, 2)
    if attendance_type == "Absent":
        return spd
    return 0.0


def infer_type_legacy(status, login_time, logout_time):
    if not login_time:
        return "Absent"
    if not logout_time:
        return "Half Day" if status == "Half Day Login" else "Present"
    if status in ("Half Day Logout", "Early Logout"):
        return "Half Day"
    return "Full Day"


def detect_overtime(employee_id, date, logout_time):
    try:
        db = get_db_connection(); cursor = db.cursor(buffered=True)
        cursor.execute(
            "SELECT s.end_time FROM employees e JOIN shifts s ON e.shift_id=s.id "
            "WHERE e.employee_id=%s",
            (employee_id,)
        )
        row      = cursor.fetchone()
        shift_end = _td_to_time(row[0]) if row else cfg.SHIFT_END
        logout_t  = _td_to_time(logout_time) if not isinstance(logout_time, datetime.time) else logout_time
        if logout_t is None or shift_end is None:
            cursor.close(); db.close(); return
        end_mins = shift_end.hour * 60 + shift_end.minute
        out_mins = logout_t.hour * 60 + logout_t.minute
        ot_mins  = out_mins - end_mins
        if ot_mins < 30:
            cursor.close(); db.close(); return
        cursor.execute(
            "SELECT COALESCE(salary_per_day,0) FROM salary_config WHERE employee_id=%s",
            (employee_id,)
        )
        sc  = cursor.fetchone()
        spd = float(sc[0]) if sc else 0.0
        ot_pay = round((spd / 8 / 60) * ot_mins, 2)
        cursor.execute("""
            INSERT INTO overtime_records
                (employee_id, date, shift_end, actual_logout, ot_minutes, ot_pay, status)
            VALUES (%s,%s,%s,%s,%s,%s,'Pending')
            ON CONFLICT (employee_id, date) DO UPDATE SET
                actual_logout=EXCLUDED.actual_logout,
                ot_minutes=EXCLUDED.ot_minutes,
                ot_pay=EXCLUDED.ot_pay
        """, (employee_id, date, shift_end, logout_t, ot_mins, ot_pay))
        db.commit(); cursor.close(); db.close()
    except Exception:
        pass


def get_working_days(year, month):
    _, last_day = calendar.monthrange(year, month)
    return [
        datetime.date(year, month, d)
        for d in range(1, last_day + 1)
        if datetime.date(year, month, d).weekday() != 6
    ]


def fetch_holidays_set(year, month):
    _, last_day = calendar.monthrange(year, month)
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT date FROM holidays WHERE date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, last_day))
    )
    holidays = {row[0] for row in cursor.fetchall()}
    cursor.close(); db.close()
    return holidays


def get_billable_past_days(year, month):
    today = datetime.date.today()
    return [d for d in get_working_days(year, month) if d <= today]


def fetch_leave_map(year, month):
    _, last_day = calendar.monthrange(year, month)
    db = get_db_connection(); cursor = db.cursor(buffered=True)
    cursor.execute(
        "SELECT employee_id, leave_date FROM leave_requests "
        "WHERE status='Approved' AND leave_date BETWEEN %s AND %s",
        (datetime.date(year, month, 1), datetime.date(year, month, last_day))
    )
    result = {}
    for emp_id, leave_date in cursor.fetchall():
        result.setdefault(emp_id, set()).add(leave_date)
    cursor.close(); db.close()
    return result
