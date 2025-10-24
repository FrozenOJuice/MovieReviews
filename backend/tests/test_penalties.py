"""
test_penalties.py – Unit and integration tests for penalties module.

Covers:
- Admin/mod creation of penalties
- Auto-expiry and computed fields
- User linkage/unlinking
- Resolution and deletion
- Access control
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from backend.main import app
from backend.penalties import schemas
from backend.penalties import utils

client = TestClient(app)


# ────────────────────────────────
# Fixtures and helpers
# ────────────────────────────────
@pytest.fixture
def auth_user():
    """
    Override FastAPI dependency to simulate logged-in users with roles.
    Uses FastAPI's dependency_overrides system instead of monkeypatch.
    """

    class MockUser:
        def __init__(self, user_id, username, role):
            self.user_id = user_id
            self.username = username
            self.email = f"{username}@example.com"
            self.role = role
            self.status = "active"
            self.movies_reviewed = []
            self.watch_later = []
            self.penalties = []

    def _set_user(role="administrator"):
        fake_user = MockUser(user_id="mock123", username=f"mock_{role}", role=role)

        # Override dependency for this role
        from backend.authentication.security import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        return fake_user

    yield _set_user

    # Clean up after test
    app.dependency_overrides.clear()


@pytest.fixture
def fake_penalty():
    """Return a sample penalty object."""
    return schemas.Penalty(
        user_id="u1",
        type="review_ban",
        severity="moderate",
        reason="Spam",
        issued_by="admin1",
        expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat(),
    )


# ────────────────────────────────
# Tests: Creation
# ────────────────────────────────
def test_issue_penalty(monkeypatch, auth_user):
    """POST /penalties → Admin can issue a new penalty."""
    auth_user("administrator")

    created_penalty = schemas.Penalty(
        user_id="u1",
        type="review_ban",
        severity="minor",
        reason="Toxic behavior",
        issued_by="admin123",
        expires_at=(datetime.utcnow() + timedelta(days=3)).isoformat(),
    )

    monkeypatch.setattr("backend.penalties.utils.add_penalty", lambda p: p)

    response = client.post(
        "/penalties/",
        json={
            "user_id": "u1",
            "type": "review_ban",
            "severity": "minor",
            "reason": "Toxic behavior"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u1"
    assert body["type"] == "review_ban"
    assert "expires_at" in body
    assert body["status"] == "active"


def test_issue_penalty_forbidden(monkeypatch, auth_user):
    """POST /penalties → Forbidden for regular users."""
    auth_user("member")

    response = client.post(
        "/penalties/",
        json={
            "user_id": "u1",
            "type": "review_ban",
            "reason": "Abuse"
        }
    )

    assert response.status_code == 403


# ────────────────────────────────
# Tests: Computed fields
# ────────────────────────────────
def test_time_remaining_and_seconds(fake_penalty):
    """Penalty schema computes human-readable and numeric remaining time."""
    penalty = fake_penalty
    remaining_text = penalty.time_remaining
    remaining_secs = penalty.time_remaining_seconds
    assert "remaining" in remaining_text or remaining_text == "Expired"
    assert isinstance(remaining_secs, int) or remaining_secs is None


def test_expired_penalty_status(monkeypatch):
    """Expired penalties should be marked 'expired'."""
    expired_penalty = schemas.Penalty(
        user_id="u1",
        type="review_ban",
        severity="moderate",
        reason="Old violation",
        issued_by="admin1",
        expires_at=(datetime.utcnow() - timedelta(days=1)).isoformat(),
    )

    monkeypatch.setattr("backend.penalties.utils._load_penalties", lambda: [expired_penalty.dict()])
    monkeypatch.setattr("backend.penalties.utils._save_penalties", lambda data: None)

    result = utils.get_penalties_for_user("u1")
    assert result[0].status == "expired"


# ────────────────────────────────
# Tests: Resolve & Unlink
# ────────────────────────────────
def test_resolve_penalty(monkeypatch, fake_penalty):
    """resolve_penalty() updates status and unlinks from user."""
    penalties = [fake_penalty.dict()]
    users = [{"user_id": "u1", "penalties": [fake_penalty.penalty_id]}]

    monkeypatch.setattr("backend.penalties.utils._load_penalties", lambda: penalties)
    monkeypatch.setattr("backend.penalties.utils._save_penalties", lambda data: data)
    monkeypatch.setattr("backend.authentication.utils.load_active_users", lambda: users)
    monkeypatch.setattr("backend.authentication.utils.save_active_users", lambda u: None)

    utils.resolve_penalty(fake_penalty.penalty_id, moderator_id="admin1", notes="Resolved")
    assert "resolved" in penalties[0]["status"]
    assert fake_penalty.penalty_id not in users[0]["penalties"]


# ────────────────────────────────
# Tests: Delete & Unlink
# ────────────────────────────────
def test_delete_penalty(monkeypatch, fake_penalty):
    """delete_penalty() removes from penalties.json and user list."""
    penalties = [fake_penalty.dict()]
    users = [{"user_id": "u1", "penalties": [fake_penalty.penalty_id]}]

    monkeypatch.setattr("backend.penalties.utils._load_penalties", lambda: penalties)
    monkeypatch.setattr("backend.penalties.utils._save_penalties", lambda data: None)
    monkeypatch.setattr("backend.authentication.utils.load_active_users", lambda: users)
    monkeypatch.setattr("backend.authentication.utils.save_active_users", lambda u: None)

    utils.delete_penalty(fake_penalty.penalty_id)
    assert fake_penalty.penalty_id not in users[0]["penalties"]


# ────────────────────────────────
# Tests: Restriction logic
# ────────────────────────────────
def test_check_active_penalty(monkeypatch, fake_penalty):
    """check_active_penalty() returns message for active restriction."""
    monkeypatch.setattr("backend.penalties.utils.get_penalties_for_user", lambda uid: [fake_penalty])
    message = utils.check_active_penalty("u1", ["review_ban"])
    assert "Action blocked" in message


def test_check_active_penalty_none(monkeypatch, fake_penalty):
    """check_active_penalty() returns None if no matching restriction."""
    fake_penalty.status = "resolved"
    monkeypatch.setattr("backend.penalties.utils.get_penalties_for_user", lambda uid: [fake_penalty])
    result = utils.check_active_penalty("u1", ["review_ban"])
    assert result is None


# ────────────────────────────────
# Tests: Access control
# ────────────────────────────────
def test_list_all_penalties_admin(monkeypatch, auth_user):
    """GET /penalties → Admin can view all penalties."""
    auth_user("administrator")
    fake = [schemas.Penalty(
        user_id="u1",
        type="review_ban",
        severity="minor",
        reason="Bad content",
        issued_by="admin",
    ).dict()]
    monkeypatch.setattr("backend.penalties.utils._load_penalties", lambda: fake)

    response = client.get("/penalties/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["user_id"] == "u1"


def test_list_all_penalties_forbidden(monkeypatch, auth_user):
    """GET /penalties → Forbidden for members."""
    auth_user("member")
    response = client.get("/penalties/")
    assert response.status_code == 403


# in backend: pytest -v tests/test_penalties.py