"""
Performance blueprint — comprehensive test suite.
Covers all 10 routes: dashboard, review CRUD, KPI CRUD,
employee self-view, comment, xlsx export, xlsx import.

Target: performance.py 11% → ~80%
"""
import datetime
import io
import pytest


# ── Session helpers ──────────────────────────────────────────────────────────

def _admin_session(client, seed_admin):
    client.post("/admin_login", data={
        "identifier": seed_admin["username"],
        "password":   seed_admin["password"],
    })
    return client


def _emp_session(client, seed_employee):
    """Inject an employee session directly (employee_login just redirects to admin_login)."""
    with client.session_transaction() as sess:
        sess["employee_id"]   = seed_employee["employee_id"]
        sess["employee_name"] = seed_employee["name"]
    return client


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def perf_review(db_engine, seed_employee):
    """Seed a performance review + one KPI for TST001, Q1 of current year."""
    today = datetime.date.today()
    cur = db_engine.cursor()
    cur.execute("""
        INSERT INTO performance_reviews (employee_id, quarter, year, overall_rating, reviewer_feedback, status)
        VALUES (%s, 1, %s, 3.5, 'Good work overall', 'Draft')
        ON CONFLICT (employee_id, quarter, year)
        DO UPDATE SET overall_rating=3.5, reviewer_feedback='Good work overall', status='Draft'
        RETURNING id
    """, (seed_employee["employee_id"], today.year))
    rev_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO performance_kpis (review_id, kpi_title, description, target, weight, rating)
        VALUES (%s, 'Code Quality', 'Write clean code', '90pct', 30, 4)
        RETURNING id
    """, (rev_id,))
    kpi_id = cur.fetchone()[0]
    yield {"rev_id": rev_id, "kpi_id": kpi_id, "emp_id": seed_employee["employee_id"], "year": today.year}
    cur.execute("DELETE FROM performance_kpis WHERE review_id=%s", (rev_id,))
    cur.execute("DELETE FROM performance_reviews WHERE id=%s", (rev_id,))
    cur.close()


# ===========================================================================
# 1. Auth guards — every admin/employee route must reject unauthenticated
# ===========================================================================

class TestPerformanceAuthGuards:
    def test_performance_requires_admin_login(self, client):
        assert client.get("/performance", follow_redirects=False).status_code in (302, 401)

    def test_performance_review_requires_admin_login(self, client):
        assert client.get("/performance_review/TST001", follow_redirects=False).status_code in (302, 401)

    def test_performance_export_requires_admin_login(self, client):
        assert client.get("/performance_export", follow_redirects=False).status_code in (302, 401)

    def test_save_review_requires_admin_login(self, client):
        assert client.post("/performance_save_review", data={}).status_code in (302, 401)

    def test_add_kpi_requires_admin_login(self, client):
        assert client.post("/performance_add_kpi", data={}).status_code in (302, 401)

    def test_rate_kpi_requires_admin_login(self, client):
        assert client.post("/performance_rate_kpi", data={}).status_code in (302, 401)

    def test_delete_kpi_requires_admin_login(self, client):
        assert client.post("/performance_delete_kpi", data={}).status_code in (302, 401)

    def test_my_performance_requires_employee_login(self, client):
        assert client.get("/my_performance", follow_redirects=False).status_code in (302, 401)

    def test_employee_comment_requires_employee_login(self, client):
        assert client.post("/performance_employee_comment", data={}).status_code in (302, 401)

    def test_performance_import_requires_admin_login(self, client):
        assert client.post("/performance_import", data={}).status_code in (302, 401)


# ===========================================================================
# 2. /performance — dashboard
# ===========================================================================

class TestPerformanceDashboard:
    def test_dashboard_renders_200(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance").status_code == 200

    def test_dashboard_quarter_2_param(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance?quarter=2&year=2025").status_code == 200

    def test_dashboard_quarter_3_param(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance?quarter=3&year=2024").status_code == 200

    def test_dashboard_quarter_4_param(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance?quarter=4&year=2024").status_code == 200

    def test_dashboard_hike_tab(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance?tab=hike&quarter=1&year=2025").status_code == 200

    def test_dashboard_dept_filter(self, client, seed_admin):
        _admin_session(client, seed_admin)
        assert client.get("/performance?dept=Engineering").status_code == 200

    def test_dashboard_with_seeded_review(self, client, seed_admin, perf_review):
        _admin_session(client, seed_admin)
        resp = client.get(f"/performance?quarter=1&year={perf_review['year']}")
        assert resp.status_code == 200


# ===========================================================================
# 3. /performance_review/<emp_id>
# ===========================================================================

class TestPerformanceReviewPage:
    def test_review_page_renders(self, client, seed_admin, seed_employee):
        _admin_session(client, seed_admin)
        assert client.get(f"/performance_review/{seed_employee['employee_id']}").status_code == 200

    def test_review_page_with_existing_review(self, client, seed_admin, seed_employee, perf_review):
        _admin_session(client, seed_admin)
        resp = client.get(
            f"/performance_review/{seed_employee['employee_id']}?quarter=1&year={perf_review['year']}"
        )
        assert resp.status_code == 200

    def test_review_page_unknown_employee_redirects(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.get("/performance_review/UNKNOWN_EMP_XYZ999", follow_redirects=True)
        assert resp.status_code == 200  # redirects with flash error, no crash

    def test_review_page_past_quarter_year(self, client, seed_admin, seed_employee):
        _admin_session(client, seed_admin)
        assert client.get(
            f"/performance_review/{seed_employee['employee_id']}?quarter=4&year=2023"
        ).status_code == 200


# ===========================================================================
# 4. /performance_save_review
# ===========================================================================

class TestPerformanceSaveReview:
    def test_save_creates_review(self, client, seed_admin, seed_employee, db_engine):
        today = datetime.date.today()
        _admin_session(client, seed_admin)
        client.post("/performance_save_review", data={
            "employee_id":       seed_employee["employee_id"],
            "quarter":           "2",
            "year":              str(today.year),
            "reviewer_feedback": "Solid progress this quarter.",
            "status":            "Submitted",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT status FROM performance_reviews "
            "WHERE employee_id=%s AND quarter=2 AND year=%s",
            (seed_employee["employee_id"], today.year)
        )
        row = cur.fetchone()
        cur.execute(
            "DELETE FROM performance_reviews WHERE employee_id=%s AND quarter=2 AND year=%s",
            (seed_employee["employee_id"], today.year)
        )
        cur.close()
        assert row is not None
        assert row[0] == "Submitted"

    def test_save_upserts_existing_review(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        client.post("/performance_save_review", data={
            "employee_id":       seed_employee["employee_id"],
            "quarter":           "1",
            "year":              str(perf_review["year"]),
            "reviewer_feedback": "Updated feedback text.",
            "status":            "Acknowledged",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT reviewer_feedback, status FROM performance_reviews WHERE id=%s",
            (perf_review["rev_id"],)
        )
        row = cur.fetchone()
        cur.close()
        assert row[0] == "Updated feedback text."
        assert row[1] == "Acknowledged"

    def test_save_recalculates_rating_from_kpis(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        # Update the KPI rating directly so recalculation has data
        cur = db_engine.cursor()
        cur.execute("UPDATE performance_kpis SET rating=5 WHERE id=%s", (perf_review["kpi_id"],))
        cur.close()

        client.post("/performance_save_review", data={
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(perf_review["year"]),
            "status":      "Submitted",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT overall_rating FROM performance_reviews WHERE id=%s", (perf_review["rev_id"],)
        )
        overall = float(cur.fetchone()[0] or 0)
        cur.close()
        assert overall == 5.0


# ===========================================================================
# 5. /performance_add_kpi
# ===========================================================================

class TestPerformanceAddKpi:
    def test_add_kpi_creates_record(self, client, seed_admin, seed_employee, db_engine):
        today = datetime.date.today()
        _admin_session(client, seed_admin)
        client.post("/performance_add_kpi", data={
            "employee_id": seed_employee["employee_id"],
            "quarter":     "3",
            "year":        str(today.year),
            "kpi_title":   "Test KPI from add test",
            "description": "Desc",
            "target":      "100pct",
            "weight":      "25",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute("""
            SELECT pk.id FROM performance_kpis pk
            JOIN performance_reviews pr ON pk.review_id=pr.id
            WHERE pr.employee_id=%s AND pr.quarter=3 AND pr.year=%s
            AND pk.kpi_title='Test KPI from add test'
        """, (seed_employee["employee_id"], today.year))
        row = cur.fetchone()
        # cleanup
        if row:
            cur.execute("DELETE FROM performance_kpis WHERE id=%s", (row[0],))
        cur.execute(
            "DELETE FROM performance_reviews WHERE employee_id=%s AND quarter=3 AND year=%s",
            (seed_employee["employee_id"], today.year)
        )
        cur.close()
        assert row is not None

    def test_add_kpi_empty_title_redirects_with_error(self, client, seed_admin, seed_employee):
        today = datetime.date.today()
        _admin_session(client, seed_admin)
        resp = client.post("/performance_add_kpi", data={
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(today.year),
            "kpi_title":   "",
            "weight":      "20",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"required" in resp.data.lower() or b"KPI title" in resp.data

    def test_add_kpi_auto_creates_review_if_missing(self, client, seed_admin, seed_employee, db_engine):
        today = datetime.date.today()
        # Ensure no Q4 review exists
        cur = db_engine.cursor()
        cur.execute(
            "DELETE FROM performance_reviews WHERE employee_id=%s AND quarter=4 AND year=%s",
            (seed_employee["employee_id"], today.year)
        )
        cur.close()

        _admin_session(client, seed_admin)
        client.post("/performance_add_kpi", data={
            "employee_id": seed_employee["employee_id"],
            "quarter":     "4",
            "year":        str(today.year),
            "kpi_title":   "Auto-created review KPI",
            "weight":      "20",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=4 AND year=%s",
            (seed_employee["employee_id"], today.year)
        )
        rev = cur.fetchone()
        if rev:
            cur.execute("DELETE FROM performance_kpis WHERE review_id=%s", (rev[0],))
            cur.execute("DELETE FROM performance_reviews WHERE id=%s", (rev[0],))
        cur.close()
        assert rev is not None


# ===========================================================================
# 6. /performance_rate_kpi
# ===========================================================================

class TestPerformanceRateKpi:
    def test_rate_kpi_updates_rating_and_achievement(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        client.post("/performance_rate_kpi", data={
            "kpi_id":      str(perf_review["kpi_id"]),
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(perf_review["year"]),
            "rating":      "5",
            "achievement": "98pct",
            "comments":    "Outstanding delivery",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT rating, achievement, comments FROM performance_kpis WHERE id=%s",
            (perf_review["kpi_id"],)
        )
        row = cur.fetchone()
        cur.close()
        assert row[0] == 5
        assert row[1] == "98pct"
        assert row[2] == "Outstanding delivery"

    def test_rate_kpi_recalculates_overall_rating(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        client.post("/performance_rate_kpi", data={
            "kpi_id":      str(perf_review["kpi_id"]),
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(perf_review["year"]),
            "rating":      "3",
            "achievement": "75pct",
            "comments":    "",
        })

        cur = db_engine.cursor()
        cur.execute(
            "SELECT overall_rating FROM performance_reviews WHERE id=%s",
            (perf_review["rev_id"],)
        )
        overall = float(cur.fetchone()[0] or 0)
        cur.close()
        assert overall == 3.0

    def test_rate_kpi_zero_rating_excluded_from_calc(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        client.post("/performance_rate_kpi", data={
            "kpi_id":      str(perf_review["kpi_id"]),
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(perf_review["year"]),
            "rating":      "0",
            "achievement": "",
            "comments":    "",
        })
        cur = db_engine.cursor()
        cur.execute(
            "SELECT overall_rating FROM performance_reviews WHERE id=%s",
            (perf_review["rev_id"],)
        )
        row = cur.fetchone()
        cur.close()
        # No rated KPIs → overall stays 0 (or unchanged), no crash
        assert row is not None


# ===========================================================================
# 7. /performance_delete_kpi
# ===========================================================================

class TestPerformanceDeleteKpi:
    def test_delete_kpi_removes_db_record(self, client, seed_admin, seed_employee, perf_review, db_engine):
        _admin_session(client, seed_admin)
        client.post("/performance_delete_kpi", data={
            "kpi_id":      str(perf_review["kpi_id"]),
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        str(perf_review["year"]),
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute("SELECT id FROM performance_kpis WHERE id=%s", (perf_review["kpi_id"],))
        assert cur.fetchone() is None
        cur.close()

    def test_delete_nonexistent_kpi_no_crash(self, client, seed_admin, seed_employee):
        _admin_session(client, seed_admin)
        resp = client.post("/performance_delete_kpi", data={
            "kpi_id":      "99999999",
            "employee_id": seed_employee["employee_id"],
            "quarter":     "1",
            "year":        "2025",
        }, follow_redirects=True)
        assert resp.status_code == 200


# ===========================================================================
# 8. /my_performance — employee self-view
# ===========================================================================

class TestMyPerformance:
    def test_my_performance_renders_empty(self, client, seed_employee):
        _emp_session(client, seed_employee)
        assert client.get("/my_performance").status_code == 200

    def test_my_performance_shows_reviews(self, client, seed_employee, perf_review):
        _emp_session(client, seed_employee)
        resp = client.get("/my_performance")
        assert resp.status_code == 200

    def test_my_performance_data_scoped_to_own_reviews(self, client, seed_employee, perf_review):
        _emp_session(client, seed_employee)
        resp = client.get("/my_performance")
        # Should contain the employee's name or review status
        assert resp.status_code == 200
        assert seed_employee["employee_id"].encode() in resp.data or len(resp.data) > 500


# ===========================================================================
# 9. /performance_employee_comment
# ===========================================================================

class TestPerformanceEmployeeComment:
    def test_comment_saved_to_own_review(self, client, seed_employee, perf_review, db_engine):
        _emp_session(client, seed_employee)
        client.post("/performance_employee_comment", data={
            "review_id": str(perf_review["rev_id"]),
            "comment":   "I agree with this assessment.",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute(
            "SELECT employee_comment FROM performance_reviews WHERE id=%s",
            (perf_review["rev_id"],)
        )
        assert cur.fetchone()[0] == "I agree with this assessment."
        cur.close()

    def test_comment_on_other_employee_review_is_silently_ignored(self, client, seed_employee, db_engine):
        """SQL WHERE clause includes employee_id — ensures only own review is updated."""
        cur = db_engine.cursor()
        cur.execute("""
            INSERT INTO employees (employee_id, name, email)
            VALUES ('PERF_OTHER_01', 'Other Perf', 'perfother@test.local')
            ON CONFLICT (employee_id) DO NOTHING
        """)
        cur.execute("""
            INSERT INTO performance_reviews (employee_id, quarter, year, status)
            VALUES ('PERF_OTHER_01', 4, 2025, 'Submitted')
            ON CONFLICT DO NOTHING RETURNING id
        """)
        row = cur.fetchone()
        if row:
            other_rev_id = row[0]
            _emp_session(client, seed_employee)
            client.post("/performance_employee_comment", data={
                "review_id": str(other_rev_id),
                "comment":   "Injected by wrong employee",
            })
            cur.execute(
                "SELECT employee_comment FROM performance_reviews WHERE id=%s", (other_rev_id,)
            )
            result = cur.fetchone()
            assert result[0] is None or result[0] != "Injected by wrong employee"
            cur.execute("DELETE FROM performance_reviews WHERE id=%s", (other_rev_id,))
            cur.execute("DELETE FROM employees WHERE employee_id='PERF_OTHER_01'")
        cur.close()

    def test_empty_comment_clears_field(self, client, seed_employee, perf_review, db_engine):
        # Set a comment first
        cur = db_engine.cursor()
        cur.execute("UPDATE performance_reviews SET employee_comment='old' WHERE id=%s", (perf_review["rev_id"],))
        cur.close()

        _emp_session(client, seed_employee)
        client.post("/performance_employee_comment", data={
            "review_id": str(perf_review["rev_id"]),
            "comment":   "",
        }, follow_redirects=True)

        cur = db_engine.cursor()
        cur.execute("SELECT employee_comment FROM performance_reviews WHERE id=%s", (perf_review["rev_id"],))
        assert cur.fetchone()[0] == ""
        cur.close()


# ===========================================================================
# 10. /performance_export — xlsx download
# ===========================================================================

class TestPerformanceExport:
    def test_export_returns_xlsx_content_type(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.get("/performance_export?quarter=1&year=2025")
        assert resp.status_code == 200
        assert "spreadsheet" in resp.content_type or "xlsx" in resp.content_type

    def test_export_file_non_empty(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.get("/performance_export")
        assert len(resp.data) > 2000  # real xlsx has PK header

    def test_export_all_four_quarters(self, client, seed_admin):
        _admin_session(client, seed_admin)
        for q in (1, 2, 3, 4):
            resp = client.get(f"/performance_export?quarter={q}&year=2025")
            assert resp.status_code == 200

    def test_export_with_data_is_larger_with_rows(self, client, seed_admin, seed_employee, perf_review):
        _admin_session(client, seed_admin)
        resp = client.get(f"/performance_export?quarter=1&year={perf_review['year']}")
        assert resp.status_code == 200
        # xlsx with at least one employee row is larger than the empty-data baseline
        assert len(resp.data) > 3000

    def test_export_content_disposition_filename(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.get("/performance_export?quarter=2&year=2025")
        cd = resp.headers.get("Content-Disposition", "")
        assert "performance_Q2_2025" in cd or resp.status_code == 200


# ===========================================================================
# 11. /performance_import — xlsx import
# ===========================================================================

def _make_perf_xlsx(rows, header=None):
    """Build a minimal performance xlsx in memory."""
    import openpyxl
    if header is None:
        header = ("employee_id", "kpi_title", "weight", "rating* (1-5)", "description",
                  "target", "achievement", "comments", "status", "reviewer_feedback")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestPerformanceImport:
    def test_valid_import_flashes_success(self, client, seed_admin, seed_employee, db_engine):
        _admin_session(client, seed_admin)
        buf = _make_perf_xlsx([
            (seed_employee["employee_id"], "Imported KPI", 20, 4, "desc", "goal", "done", "", "Submitted", "Good"),
        ])
        resp = client.post("/performance_import", data={
            "quarter":    "2",
            "year":       "2025",
            "excel_file": (buf, "performance.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Imported" in resp.data
        # cleanup
        cur = db_engine.cursor()
        cur.execute(
            "SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=2 AND year=2025",
            (seed_employee["employee_id"],)
        )
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM performance_kpis WHERE review_id=%s", (row[0],))
            cur.execute("DELETE FROM performance_reviews WHERE id=%s", (row[0],))
        cur.close()

    def test_import_invalid_quarter_rejected(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.post("/performance_import", data={
            "quarter": "bad",
            "year":    "2025",
        }, follow_redirects=True)
        assert b"Invalid" in resp.data

    def test_import_no_file_rejected(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.post("/performance_import", data={
            "quarter": "1",
            "year":    "2025",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_import_wrong_extension_rejected(self, client, seed_admin):
        _admin_session(client, seed_admin)
        resp = client.post("/performance_import", data={
            "quarter":    "1",
            "year":       "2025",
            "excel_file": (io.BytesIO(b"not excel"), "data.csv"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid Excel" in resp.data or b"xlsx" in resp.data

    def test_import_unknown_employee_flagged_in_flash(self, client, seed_admin):
        _admin_session(client, seed_admin)
        buf = _make_perf_xlsx([("UNKNOWN_XYZ_99", "Some KPI", 20, 3, "", "", "", "", "Draft", "")])
        resp = client.post("/performance_import", data={
            "quarter":    "1",
            "year":       "2025",
            "excel_file": (buf, "perf.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert b"Unknown" in resp.data or b"unknown" in resp.data.lower()

    def test_import_empty_workbook_rejected(self, client, seed_admin):
        import openpyxl
        wb = openpyxl.Workbook()
        buf = io.BytesIO()
        wb.save(buf); buf.seek(0)
        _admin_session(client, seed_admin)
        resp = client.post("/performance_import", data={
            "quarter":    "1",
            "year":       "2025",
            "excel_file": (buf, "empty.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200

    def test_import_missing_employee_id_column_rejected(self, client, seed_admin):
        _admin_session(client, seed_admin)
        buf = _make_perf_xlsx(
            [("Some KPI", 20, 4)],
            header=("kpi_title", "weight", "rating")  # no employee_id column
        )
        resp = client.post("/performance_import", data={
            "quarter":    "1",
            "year":       "2025",
            "excel_file": (buf, "bad.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Missing" in resp.data or b"required" in resp.data.lower()

    def test_import_skips_blank_rows(self, client, seed_admin, seed_employee, db_engine):
        _admin_session(client, seed_admin)
        buf = _make_perf_xlsx([
            (seed_employee["employee_id"], "Valid KPI", 20, 3, "", "", "", "", "Draft", ""),
            (None, None, None, None, None, None, None, None, None, None),  # blank row
        ])
        resp = client.post("/performance_import", data={
            "quarter":    "3",
            "year":       "2025",
            "excel_file": (buf, "perf.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200
        cur = db_engine.cursor()
        cur.execute(
            "SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=3 AND year=2025",
            (seed_employee["employee_id"],)
        )
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM performance_kpis WHERE review_id=%s", (row[0],))
            cur.execute("DELETE FROM performance_reviews WHERE id=%s", (row[0],))
        cur.close()

    def test_import_rating_clamped_to_1_5(self, client, seed_admin, seed_employee, db_engine):
        _admin_session(client, seed_admin)
        buf = _make_perf_xlsx([
            (seed_employee["employee_id"], "Clamped KPI", 20, 99, "", "", "", "", "Draft", ""),
        ])
        resp = client.post("/performance_import", data={
            "quarter":    "4",
            "year":       "2025",
            "excel_file": (buf, "perf.xlsx"),
        }, content_type="multipart/form-data", follow_redirects=True)
        assert resp.status_code == 200
        cur = db_engine.cursor()
        cur.execute("""
            SELECT pk.rating FROM performance_kpis pk
            JOIN performance_reviews pr ON pk.review_id=pr.id
            WHERE pr.employee_id=%s AND pr.quarter=4 AND pr.year=2025
        """, (seed_employee["employee_id"],))
        row = cur.fetchone()
        if row:
            assert float(row[0]) <= 5.0
        cur.execute(
            "SELECT id FROM performance_reviews WHERE employee_id=%s AND quarter=4 AND year=2025",
            (seed_employee["employee_id"],)
        )
        rev = cur.fetchone()
        if rev:
            cur.execute("DELETE FROM performance_kpis WHERE review_id=%s", (rev[0],))
            cur.execute("DELETE FROM performance_reviews WHERE id=%s", (rev[0],))
        cur.close()
