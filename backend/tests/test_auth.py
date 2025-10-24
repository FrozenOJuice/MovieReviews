"""
Tests for authentication endpoints: register, login, logout, refresh, whoami, and password reset.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.authentication import utils, schemas, security
import json
import os

client = TestClient(app)

# 🧹 --- Test Setup & Helpers ---------------------------------------------------

@pytest.fixture(autouse=True)
def clear_user_data(tmp_path, monkeypatch):
    """Ensure temporary JSON files are used for each test."""
    users_dir = tmp_path / "data" / "users"
    users_dir.mkdir(parents=True)
    active = users_dir / "users_active.json"
    inactive = users_dir / "users_inactive.json"
    revoked = users_dir / "revoked_tokens.json"

    active.write_text("[]")
    inactive.write_text("[]")
    revoked.write_text("[]")

    monkeypatch.setattr(utils, "ACTIVE_FILE", str(active))
    monkeypatch.setattr(utils, "INACTIVE_FILE", str(inactive))
    monkeypatch.setattr(utils, "REVOKED_TOKENS_FILE", str(revoked))
    yield


# 🧩 --- Tests -----------------------------------------------------------------

def test_register_success():
    """POST /auth/register → Creates a new active user."""
    response = client.post("/auth/register", json={
        "username": "john_doe",
        "email": "john@example.com",
        "password": "Password123",
        "role": "member"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["status"] == "active"


def test_register_duplicate_username():
    """POST /auth/register → Fails if username already exists."""
    client.post("/auth/register", json={
        "username": "duplicate",
        "email": "first@example.com",
        "password": "Password123"
    })
    response = client.post("/auth/register", json={
        "username": "duplicate",
        "email": "second@example.com",
        "password": "Password123"
    })
    assert response.status_code == 400
    assert "Username" in response.json()["detail"]


def test_login_success():
    """POST /auth/login → Returns a valid access token for correct credentials."""
    client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "StrongPass1"
    })
    response = client.post(
        "/auth/login",
        data={"username": "alice", "password": "StrongPass1"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials():
    """POST /auth/login → Rejects invalid password."""
    client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "GoodPass1"
    })
    response = client.post(
        "/auth/login",
        data={"username": "bob", "password": "WrongPass"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401


def test_whoami_returns_user():
    """GET /auth/whoami → Returns token data for logged-in user."""
    client.post("/auth/register", json={
        "username": "carol",
        "email": "carol@example.com",
        "password": "SecurePass1"
    })
    login = client.post(
        "/auth/login",
        data={"username": "carol", "password": "SecurePass1"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    token = login.json()["access_token"]
    response = client.get("/auth/whoami", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "member"


def test_logout_revokes_token():
    """POST /auth/logout → Adds token to revoked list."""
    client.post("/auth/register", json={
        "username": "david",
        "email": "david@example.com",
        "password": "SecurePass1"
    })
    login = client.post(
        "/auth/login",
        data={"username": "david", "password": "SecurePass1"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    token = login.json()["access_token"]
    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    assert "revoked" in logout.json()["message"].lower()


def test_refresh_token_success():
    """POST /auth/refresh → Issues a new valid token."""
    client.post("/auth/register", json={
        "username": "emily",
        "email": "emily@example.com",
        "password": "StrongPass2"
    })
    login = client.post(
        "/auth/login",
        data={"username": "emily", "password": "StrongPass2"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    token = login.json()["access_token"]
    refresh = client.post("/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()


def test_password_reset_flow(monkeypatch):
    """POST /auth/password/request and /auth/password/reset → Resets password successfully."""
    client.post("/auth/register", json={
        "username": "fred",
        "email": "fred@example.com",
        "password": "ResetMe123"
    })

    # Request reset token
    request = client.post("/auth/password/request", params={"email": "fred@example.com"})
    assert request.status_code == 200
    token = request.json()["reset_token"]

    # Reset password using token
    reset = client.post("/auth/password/reset", params={"token": token, "new_password": "NewPass456"})
    assert reset.status_code == 200
    assert "successfully" in reset.json()["message"]

    # Confirm new password works
    login = client.post(
        "/auth/login",
        data={"username": "fred", "password": "NewPass456"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


# in backend: pytest -v tests/test_auth.py