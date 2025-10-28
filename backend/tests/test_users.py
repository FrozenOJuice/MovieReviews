"""
Tests for /users routes:
- Self profile actions (/users/me, /users/me/status, etc.)
- Admin user management (CRUD on /users and /users/{user_id})
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.main import app
from backend.users import schemas
from backend.authentication.security import get_current_user

client = TestClient(app)



@pytest.fixture
def auth_user():
    """
    Override FastAPI's `get_current_user` dependency
    to simulate logged-in users with chosen roles.
    """

    def _set_user(role: str = "member", user_id: str = "test_user_id"):
        fake_user = schemas.UserToken(
            user_id=user_id,
            username=f"{role}_user",
            email=f"{role}@example.com",
            role=role,
        )

        # Apply the dependency override on the real app
        app.dependency_overrides[get_current_user] = lambda: fake_user
        return fake_user

    yield _set_user

    # Clean up after each test
    app.dependency_overrides.clear()





# ==========================================================
# 🧩 SELF ROUTES
# ==========================================================

def test_get_my_profile(monkeypatch, auth_user):
    """GET /users/me → returns current user's profile."""
    user = auth_user("member")

    fake_user = {
        "user_id": user.user_id,
        "username": "test_user",
        "email": "test@example.com",
        "role": "member",
        "status": "active",
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    monkeypatch.setattr("backend.users.utils.get_user_by_id", lambda uid: fake_user)

    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_update_my_profile(monkeypatch, auth_user):
    """PATCH /users/me → updates user's own profile."""
    user = auth_user("member")

    updated_user = {
        "user_id": user.user_id,
        "username": "newname",
        "email": "new@example.com",
        "role": "member",
        "status": "active",
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    monkeypatch.setattr("backend.users.utils.update_user", lambda uid, u: updated_user)

    payload = {"username": "newname", "email": "new@example.com"}
    response = client.patch("/users/me", json=payload)
    assert response.status_code == 200
    assert response.json()["username"] == "newname"


def test_change_my_password(monkeypatch, auth_user):
    """PATCH /users/me/password → user changes their password."""
    auth_user("member")

    called = {}

    def fake_change_password(uid, old, new):
        called["ok"] = True
        assert old == "oldpass"
        assert new == "newpass"

    monkeypatch.setattr("backend.users.utils.change_password", fake_change_password)

    payload = {"old_password": "oldpass", "new_password": "newpass"}
    response = client.patch("/users/me/password", json=payload)
    assert response.status_code == 200
    assert "ok" in called


def test_change_my_status(monkeypatch, auth_user):
    """PATCH /users/me/status → deactivates own account."""
    auth_user("member")

    monkeypatch.setattr(
        "backend.users.utils.update_user_status",
        lambda uid, s: {"message": f"User {uid} moved to {s}."},
    )

    payload = {"status": "inactive"}
    response = client.patch("/users/me/status", json=payload)
    assert response.status_code == 200
    assert "inactive" in response.json()["message"]


# ==========================================================
# 🧩 ADMIN ROUTES
# ==========================================================

def test_list_users_admin(monkeypatch, auth_user):
    """GET /users → Admin lists all users."""
    auth_user("administrator")

    fake_users = [
        {"user_id": "u1", "username": "user1", "email": "a@a.com", "role": "member", "status": "active",
         "movies_reviewed": [], "watch_later": [], "penalties": []}
    ]
    monkeypatch.setattr("backend.users.utils.load_active_users", lambda: fake_users)

    response = client.get("/users")
    assert response.status_code == 200
    assert response.json()[0]["username"] == "user1"


def test_list_users_forbidden(monkeypatch, auth_user):
    """GET /users → Regular user forbidden."""
    auth_user("member")
    response = client.get("/users")
    assert response.status_code == 403


def test_get_user_admin(monkeypatch, auth_user):
    """GET /users/{user_id} → Admin gets a specific user."""
    auth_user("administrator")
    fake_user = {
        "user_id": "u1",
        "username": "target",
        "email": "t@t.com",
        "role": "member",
        "status": "active",
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }
    monkeypatch.setattr("backend.users.utils.get_user_by_id", lambda uid: fake_user)

    response = client.get("/users/u1")
    assert response.status_code == 200
    assert response.json()["username"] == "target"


def test_get_user_forbidden(auth_user):
    """GET /users/{user_id} → Regular user forbidden."""
    auth_user("member")
    response = client.get("/users/u1")
    assert response.status_code == 403


def test_update_user_admin(monkeypatch, auth_user):
    """PATCH /users/{user_id} → Admin updates another user."""
    auth_user("administrator")

    updated_user = {
        "user_id": "u1",
        "username": "changed",
        "email": "x@x.com",
        "role": "critic",
        "status": "active",
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    monkeypatch.setattr("backend.users.utils.update_user", lambda uid, data: updated_user)

    payload = {"role": "critic"}
    response = client.patch("/users/u1", json=payload)
    assert response.status_code == 200
    assert response.json()["role"] == "critic"


def test_update_user_forbidden(auth_user):
    """PATCH /users/{user_id} → Regular user forbidden."""
    auth_user("member")
    response = client.patch("/users/u1", json={"role": "critic"})
    assert response.status_code == 403


def test_delete_user_admin(monkeypatch, auth_user):
    """DELETE /users/{user_id} → Admin deletes a user."""
    auth_user("administrator")

    monkeypatch.setattr("backend.users.utils.delete_user", lambda uid: None)

    response = client.delete("/users/u1")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_user_forbidden(auth_user):
    """DELETE /users/{user_id} → Regular user forbidden."""
    auth_user("member")
    response = client.delete("/users/u1")
    assert response.status_code == 403


def test_create_user_admin(monkeypatch, auth_user):
    """POST /users → Admin manually creates a new user."""
    auth_user("administrator")

    created = {
        "user_id": "u2",
        "username": "newuser",
        "email": "n@n.com",
        "role": "member",
        "status": "active",
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    monkeypatch.setattr("backend.users.utils.add_user", lambda user: created)

    payload = {"username": "newuser", "email": "n@n.com", "password": "1234", "role": "member"}
    response = client.post("/users", json=payload)
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"


def test_create_user_forbidden(auth_user):
    """POST /users → Regular user forbidden."""
    auth_user("member")
    payload = {"username": "abc", "email": "a@a.com", "password": "123"}
    response = client.post("/users", json=payload)
    assert response.status_code == 403


# in backend: pytest -v tests/test_users.py