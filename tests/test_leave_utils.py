"""Tests for utils/leave_utils.py — pure helper functions extracted from
app.py for the leave/holiday/overtime blueprint."""
import datetime
import pytest
from utils.leave_utils import assign_leave_balances_for_employee, get_indian_holidays


@pytest.fixture
def leave_type(db_engine):
    """Insert an active leave type; clean up after the test."""
    cur = db_engine.cursor()
    cur.execute(
        "INSERT INTO leave_types (name, annual_quota, is_active) VALUES (%s, %s, 1) RETURNING id",
        ("Test Leave Type", 15),
    )
    lt_id = cur.fetchone()[0]
    db_engine.commit()
    yield {"id": lt_id, "quota": 15}
    cur.execute("DELETE FROM leave_balances WHERE leave_type_id=%s", (lt_id,))
    cur.execute("DELETE FROM leave_types WHERE id=%s", (lt_id,))
    db_engine.commit()
    cur.close()


class TestAssignLeaveBalancesForEmployee:
    def test_creates_balance_row_for_active_type(self, db_engine, leave_type, seed_employee):
        cur = db_engine.cursor()
        assign_leave_balances_for_employee(cur, seed_employee["employee_id"], year=2026)
        db_engine.commit()

        cur.execute(
            "SELECT total_days, used_days FROM leave_balances "
            "WHERE employee_id=%s AND leave_type_id=%s AND year=%s",
            (seed_employee["employee_id"], leave_type["id"], 2026),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None
        assert row[0] == leave_type["quota"]
        assert float(row[1]) == 0

    def test_defaults_to_current_year_when_omitted(self, db_engine, leave_type, seed_employee):
        cur = db_engine.cursor()
        assign_leave_balances_for_employee(cur, seed_employee["employee_id"])
        db_engine.commit()

        this_year = datetime.date.today().year
        cur.execute(
            "SELECT id FROM leave_balances WHERE employee_id=%s AND leave_type_id=%s AND year=%s",
            (seed_employee["employee_id"], leave_type["id"], this_year),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None

    def test_skips_inactive_leave_types(self, db_engine, seed_employee):
        cur = db_engine.cursor()
        cur.execute(
            "INSERT INTO leave_types (name, annual_quota, is_active) VALUES (%s, %s, 0) RETURNING id",
            ("Inactive Type", 10),
        )
        inactive_id = cur.fetchone()[0]
        db_engine.commit()

        assign_leave_balances_for_employee(cur, seed_employee["employee_id"], year=2026)
        db_engine.commit()

        cur.execute(
            "SELECT id FROM leave_balances WHERE employee_id=%s AND leave_type_id=%s AND year=2026",
            (seed_employee["employee_id"], inactive_id),
        )
        row = cur.fetchone()
        cur.execute("DELETE FROM leave_types WHERE id=%s", (inactive_id,))
        db_engine.commit()
        cur.close()
        assert row is None

    def test_reassigning_does_not_reset_used_days(self, db_engine, leave_type, seed_employee):
        """ON CONFLICT DO UPDATE must only overwrite total_days when nothing
        has been used yet — re-running assignment shouldn't wipe usage."""
        cur = db_engine.cursor()
        assign_leave_balances_for_employee(cur, seed_employee["employee_id"], year=2026)
        db_engine.commit()

        cur.execute(
            "UPDATE leave_balances SET used_days=3 WHERE employee_id=%s AND leave_type_id=%s AND year=2026",
            (seed_employee["employee_id"], leave_type["id"]),
        )
        db_engine.commit()

        # Re-run with a different quota to prove total_days is left alone
        # once used_days is nonzero (the CASE WHEN guard in the query).
        cur.execute("UPDATE leave_types SET annual_quota=99 WHERE id=%s", (leave_type["id"],))
        db_engine.commit()
        assign_leave_balances_for_employee(cur, seed_employee["employee_id"], year=2026)
        db_engine.commit()

        cur.execute(
            "SELECT total_days, used_days FROM leave_balances "
            "WHERE employee_id=%s AND leave_type_id=%s AND year=2026",
            (seed_employee["employee_id"], leave_type["id"]),
        )
        row = cur.fetchone()
        cur.close()
        assert float(row[1]) == 3
        assert row[0] == leave_type["quota"]  # unchanged, not bumped to 99


class TestGetIndianHolidays:
    def test_returns_sorted_by_date(self):
        holidays = get_indian_holidays(2026)
        dates = [d for d, _name in holidays]
        assert dates == sorted(dates)

    def test_includes_fixed_holidays(self):
        holidays = get_indian_holidays(2026)
        names = {name for _d, name in holidays}
        assert "Republic Day" in names
        assert "Independence Day" in names
        assert "Christmas Day" in names

    def test_fixed_holiday_dates_are_correct(self):
        holidays = dict((name, d) for d, name in get_indian_holidays(2026))
        assert holidays["Republic Day"] == datetime.date(2026, 1, 26)
        assert holidays["Independence Day"] == datetime.date(2026, 8, 15)

    def test_includes_variable_holidays_for_known_year(self):
        holidays = get_indian_holidays(2026)
        names = {name for _d, name in holidays}
        assert "Holi" in names
        assert "Diwali (Lakshmi Puja)" in names

    def test_unknown_year_still_returns_fixed_holidays_only(self):
        holidays = get_indian_holidays(1999)
        names = {name for _d, name in holidays}
        assert "Republic Day" in names
        assert "Holi" not in names  # only in the variable_by_year table for 2025-2027

    def test_all_dates_fall_within_requested_year(self):
        for year in (2025, 2026, 2027):
            for d, _name in get_indian_holidays(year):
                assert d.year == year
