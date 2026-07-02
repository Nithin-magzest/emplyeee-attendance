"""Tests for salary/attendance calculations: deductions, classification, working days."""
import datetime
import pytest


# ── Attendance classification (classify_by_worked_minutes) ───────────────────
# Signature: classify_by_worked_minutes(login_status, total_minutes, s_start, s_end)
# Returns "Full Day", "Late - Full Day", or "Half Day"
# Logic: if total_minutes >= (shift_length_mins * 0.75) → Full Day / Late - Full Day; else Half Day

class TestClassifyByWorkedMinutes:
    S_START = datetime.time(9, 0)
    S_END   = datetime.time(18, 0)   # 540-minute shift

    def _classify(self, login_status, total_minutes):
        from utils.attendance_utils import classify_by_worked_minutes
        return classify_by_worked_minutes(login_status, total_minutes, self.S_START, self.S_END)

    def test_full_day_on_normal_login(self):
        assert self._classify("Normal", 480) == "Full Day"

    def test_late_full_day_on_late_login(self):
        assert self._classify("Late Login", 480) == "Late - Full Day"

    def test_half_day_when_below_75_percent(self):
        # 75% of 540 min = 405 min; 400 < 405 → Half Day
        result = self._classify("Normal", 400)
        assert result == "Half Day"

    def test_full_day_at_exactly_75_percent(self):
        # 540 * 0.75 = 405 min
        result = self._classify("Normal", 405)
        assert result == "Full Day"

    def test_full_day_above_threshold(self):
        result = self._classify("Normal", 540)
        assert result == "Full Day"

    def test_zero_minutes_is_half_day(self):
        result = self._classify("Normal", 0)
        assert result == "Half Day"


# ── Deduction calculation ─────────────────────────────────────────────────────
# Signature: calculate_deduction(salary_per_day, attendance_type)
# Rates from utils.config (monkeypatched per test)

class TestCalculateDeduction:
    @pytest.fixture(autouse=True)
    def _patch_config(self, monkeypatch):
        import utils.config as cfg
        monkeypatch.setattr(cfg, "LATE_DEDUCTION_RATE", 0.10)
        monkeypatch.setattr(cfg, "HALF_DAY_RATE",       0.50)
        monkeypatch.setattr(cfg, "HOLIDAY_PAY",         "paid")
        monkeypatch.setattr(cfg, "LEAVE_PAY",           "exclude")

    def _ded(self, att_type, daily=1000.0):
        from utils.attendance_utils import calculate_deduction
        return calculate_deduction(daily, att_type)

    def test_full_day_no_deduction(self):
        assert self._ded("Full Day") == 0.0

    def test_half_day_50_percent(self):
        assert abs(self._ded("Half Day") - 500.0) < 0.01

    def test_absent_full_day_deduction(self):
        assert abs(self._ded("Absent") - 1000.0) < 0.01

    def test_late_full_day_10_percent(self):
        assert abs(self._ded("Late - Full Day") - 100.0) < 0.01

    def test_paid_holiday_no_deduction(self):
        # HOLIDAY_PAY = "paid" → no deduction
        assert self._ded("Holiday") == 0.0

    def test_unpaid_holiday_full_deduction(self, monkeypatch):
        import utils.config as cfg
        monkeypatch.setattr(cfg, "HOLIDAY_PAY", "unpaid")
        assert abs(self._ded("Holiday") - 1000.0) < 0.01

    def test_leave_excluded_no_deduction(self):
        # LEAVE_PAY = "exclude" → no deduction
        assert self._ded("Approved Leave") == 0.0

    def test_leave_absent_full_deduction(self, monkeypatch):
        import utils.config as cfg
        monkeypatch.setattr(cfg, "LEAVE_PAY", "absent")
        assert abs(self._ded("Approved Leave") - 1000.0) < 0.01

    def test_deduction_never_negative(self):
        from utils.attendance_utils import calculate_deduction
        for att_type in ("Full Day", "Absent", "Half Day", "Late - Full Day",
                         "Holiday", "Approved Leave"):
            assert calculate_deduction(800.0, att_type) >= 0.0

    def test_deduction_never_exceeds_daily_salary(self):
        from utils.attendance_utils import calculate_deduction
        for att_type in ("Full Day", "Absent", "Half Day", "Late - Full Day",
                         "Holiday", "Approved Leave"):
            assert calculate_deduction(800.0, att_type) <= 800.0

    def test_zero_daily_salary_zero_deduction(self):
        from utils.attendance_utils import calculate_deduction
        for att_type in ("Full Day", "Absent", "Half Day"):
            assert calculate_deduction(0.0, att_type) == 0.0


# ── get_working_days ──────────────────────────────────────────────────────────
# Signature: get_working_days(year, month) → list[datetime.date]
# Excludes Sundays (weekday() == 6); does NOT exclude Saturdays by default

class TestGetWorkingDays:
    def test_returns_list_of_dates(self):
        from utils.attendance_utils import get_working_days
        days = get_working_days(2025, 1)
        assert isinstance(days, list)
        assert all(isinstance(d, datetime.date) for d in days)

    def test_no_sundays_in_result(self):
        from utils.attendance_utils import get_working_days
        days = get_working_days(2025, 1)
        assert not any(d.weekday() == 6 for d in days), "Sundays must be excluded"

    def test_january_2025_day_count(self):
        from utils.attendance_utils import get_working_days
        # Jan 2025: 31 days, 5 Sundays → 26 working days
        days = get_working_days(2025, 1)
        assert len(days) == 26

    def test_february_2025_day_count(self):
        from utils.attendance_utils import get_working_days
        # Feb 2025: 28 days, 4 Sundays → 24 working days
        days = get_working_days(2025, 2)
        assert len(days) == 24

    def test_all_days_within_month(self):
        from utils.attendance_utils import get_working_days
        days = get_working_days(2025, 3)
        assert all(d.month == 3 and d.year == 2025 for d in days)


# ── get_attendance_type ───────────────────────────────────────────────────────
# Signature: get_attendance_type(login_status, logout_status) → str

class TestGetAttendanceType:
    def _at(self, login, logout):
        from utils.attendance_utils import get_attendance_type
        return get_attendance_type(login, logout)

    def test_absent_when_no_login(self):
        assert self._at(None, None) == "Absent"
        assert self._at("", None) == "Absent"

    def test_present_normal_day(self):
        result = self._at("Normal Login", "Normal Logout")
        assert result == "Full Day"

    def test_half_day_login(self):
        result = self._at("Half Day Login", "Normal Logout")
        assert result == "Half Day"

    def test_half_day_logout(self):
        result = self._at("Normal Login", "Half Day Logout")
        assert result == "Half Day"

    def test_late_login_full_day(self):
        result = self._at("Late Login", "Normal Logout")
        assert result == "Late - Full Day"

    def test_no_logout_after_normal_login(self):
        # No logout recorded → Present (not yet checked out)
        result = self._at("Normal Login", None)
        assert result == "Present"

    def test_no_logout_after_half_day_login(self):
        result = self._at("Half Day Login", None)
        assert result == "Half Day"
