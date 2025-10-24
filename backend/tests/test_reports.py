"""
Tests for the Reports module:
- Submitting, viewing, updating, and deleting reports.
- RBAC enforcement for different roles.
- Summary endpoint for moderators/admins.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.reports import schemas
from types import SimpleNamespace

client = TestClient(app)


# --- Fixtures ---
@pytest.fixture
def fake_report():
    """A sample report object used in tests."""
    return {
        "report_id": "rep1",
        "reporter_id": "user123",
        "reported_id": "user456",
        "type": "user",
        "reason": "harassment",
        "status": "pending",
        "created_at": "2025-10-23T00:00:00Z",
        "resolved_at": None,
        "moderator_id": None,
        "moderator_notes": None,
    }


@pytest.fixture
def auth_user():
    """
    Use FastAPI's dependency override system to mock get_current_user() with attribute access.
    """
    from types import SimpleNamespace

    def _set_user(role: str):
        from backend.authentication.security import get_current_user
        from backend.main import app

        fake_user = SimpleNamespace(
            user_id="mock_user_id",
            username="mockuser",
            role=role,
        )

        app.dependency_overrides[get_current_user] = lambda: fake_user

    yield _set_user

    from backend.main import app
    app.dependency_overrides = {}


# --- Tests ---

def test_submit_report_success(monkeypatch, auth_user):
    """POST /reports → Member/Critic can submit a report."""
    auth_user("member")

    # Mock report creation utility
    fake_created = schemas.Report(
        report_id="rep123",
        reporter_id="mock_user_id",
        reported_id="user789",
        type=schemas.ReportType.user,
        reason="spam",
        status=schemas.ReportStatus.pending,
        created_at="2025-10-23T00:00:00Z",
        resolved_at=None,
        moderator_id=None,
        moderator_notes=None,
    )

    monkeypatch.setattr("backend.reports.utils.create_report", lambda **kwargs: fake_created)

    payload = {"reported_id": "user789", "type": "user", "reason": "spam"}
    response = client.post("/reports/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == "rep123"
    assert data["status"] == "pending"
    assert data["reporter_id"] == "mock_user_id"


def test_submit_report_forbidden(auth_user):
    """POST /reports → Non-member/critic users are forbidden."""
    auth_user("guest")
    response = client.post("/reports/", json={"reported_id": "u1", "type": "user", "reason": "spam"})
    assert response.status_code == 403


def test_get_all_reports(monkeypatch, auth_user, fake_report):
    """GET /reports → Moderator/Admin can retrieve all reports."""
    auth_user("moderator")
    monkeypatch.setattr("backend.reports.utils.load_reports", lambda: [schemas.Report(**fake_report)])
    response = client.get("/reports/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["report_id"] == "rep1"


def test_get_all_reports_forbidden(auth_user):
    """GET /reports → Regular member cannot retrieve all reports."""
    auth_user("member")
    response = client.get("/reports/")
    assert response.status_code == 403


def test_get_report(monkeypatch, auth_user, fake_report):
    """GET /reports/{report_id} → Moderator/Admin can view a specific report."""
    auth_user("administrator")
    monkeypatch.setattr("backend.reports.utils.get_report", lambda rid: schemas.Report(**fake_report))
    response = client.get("/reports/rep1")
    assert response.status_code == 200
    assert response.json()["report_id"] == "rep1"


def test_get_report_not_found(monkeypatch, auth_user):
    """GET /reports/{report_id} → Returns 404 if not found."""
    auth_user("moderator")
    monkeypatch.setattr("backend.reports.utils.get_report", lambda rid: None)
    response = client.get("/reports/invalid123")
    assert response.status_code == 404


def test_update_report_success(monkeypatch, auth_user, fake_report):
    """PATCH /reports/{report_id} → Moderator/Admin can update report status."""
    auth_user("moderator")

    update_data = schemas.ReportUpdate(status=schemas.ReportStatus.resolved, moderator_notes="Handled")
    updated_report = schemas.Report(**{**fake_report, "status": "resolved", "moderator_notes": "Handled"})

    monkeypatch.setattr(
        "backend.reports.utils.update_report_status",
        lambda rid, update, moderator_id: updated_report,
    )

    response = client.patch("/reports/rep1", json=update_data.dict())
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["moderator_notes"] == "Handled"


def test_update_report_forbidden(auth_user):
    """PATCH /reports/{report_id} → Regular members cannot update."""
    auth_user("member")
    response = client.patch("/reports/rep1", json={"status": "resolved"})
    assert response.status_code == 403


def test_delete_report_success(monkeypatch, auth_user):
    """DELETE /reports/{report_id} → Admin can delete a report."""
    auth_user("administrator")
    monkeypatch.setattr("backend.reports.utils.delete_report", lambda rid: True)
    response = client.delete("/reports/rep1")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_report_forbidden(auth_user):
    """DELETE /reports/{report_id} → Only admin can delete."""
    auth_user("moderator")
    response = client.delete("/reports/rep1")
    assert response.status_code == 403


def test_delete_report_not_found(monkeypatch, auth_user):
    """DELETE /reports/{report_id} → Returns 404 if not found."""
    auth_user("administrator")
    monkeypatch.setattr("backend.reports.utils.delete_report", lambda rid: False)
    response = client.delete("/reports/rep_missing")
    assert response.status_code == 404


def test_summary_endpoint(monkeypatch, auth_user):
    """GET /reports/summary → Moderator/Admin can view dashboard summary."""
    auth_user("moderator")
    fake_summary = schemas.ReportSummary(
        total_reports=10, pending=5, under_review=2, resolved=2, dismissed=1
    )
    monkeypatch.setattr("backend.reports.utils.get_summary", lambda: fake_summary)
    response = client.get("/reports/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_reports"] == 10
    assert data["pending"] == 5


def test_summary_forbidden(auth_user):
    """GET /reports/summary → Regular users cannot access."""
    auth_user("member")
    response = client.get("/reports/summary")
    assert response.status_code == 403



# in backend: pytest -v tests/test_reports.py