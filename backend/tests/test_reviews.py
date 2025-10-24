"""
Tests for the Reviews module — ensuring correct CRUD, voting, and role permissions.
Covers:
- Listing and fetching reviews (any logged-in user)
- Adding (only once per movie per user, blocked if penalized)
- Editing (own or admin)
- Deleting (own, moderator, or administrator)
- Voting (not on own review, increments counts)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.movies import schemas
from backend.authentication.security import get_current_user

client = TestClient(app)

# ---------------------------------------------------------------------
# 🧩 FIXTURES
# ---------------------------------------------------------------------
@pytest.fixture
def auth_user():
    """
    Override FastAPI's get_current_user dependency at the app level.
    Usage: auth_user("member") or auth_user("administrator")
    """
    def _set_user(role="member", user_id="u1", username="testuser"):
        def override_dep():
            return schemas.UserToken(user_id=user_id, username=username, role=role)
        # ✅ Official override — works regardless of import timing/references
        app.dependency_overrides[get_current_user] = override_dep
    yield _set_user
    # ✅ Important: remove overrides so tests don't leak state
    app.dependency_overrides.clear()

# -------------------------------------------------------------------
# LIST + GET
# -------------------------------------------------------------------

def test_list_reviews(monkeypatch, auth_user):
    """GET /reviews/{movie_id} → lists reviews (logged in)."""
    auth_user("member")
    fake_reviews = [
        {"review_id": "r1", "movie_id": "m1", "user_id": "u1", "title": "Good", "rating": 8,
         "date": "2025-01-01", "text": "Nice!", "usefulness": {"helpful": 2, "total_votes": 3}}
    ]
    monkeypatch.setattr("backend.reviews.utils.filter_sort_reviews", lambda **kwargs: fake_reviews)
    response = client.get("/reviews/m1")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Good"


def test_get_review_found(monkeypatch, auth_user):
    """GET /reviews/{movie_id}/{review_id} → returns one review."""
    auth_user("member")
    fake_review = {
        "review_id": "r1", "movie_id": "m1", "user_id": "u1",
        "title": "Good", "rating": 8, "date": "2025-01-01",
        "text": "Nice!", "usefulness": {"helpful": 2, "total_votes": 3}
    }
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    response = client.get("/reviews/m1/r1")
    assert response.status_code == 200
    assert response.json()["review_id"] == "r1"


def test_get_review_not_found(monkeypatch, auth_user):
    """GET /reviews/{movie_id}/{review_id} → 404 if missing."""
    auth_user("member")
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: None)
    response = client.get("/reviews/m1/r404")
    assert response.status_code == 404

# -------------------------------------------------------------------
# ADD
# -------------------------------------------------------------------

def test_add_review_success(monkeypatch, auth_user):
    """POST /reviews/{movie_id} → adds one review per movie per user."""
    auth_user("member")
    data = {"title": "Amazing", "rating": 9, "text": "Loved it!"}

    def fake_add(movie_id, review_data, user_id):
        return {
            "review_id": "r9", "movie_id": movie_id, "user_id": user_id,
            "title": review_data.title, "rating": review_data.rating,
            "date": "2025-01-01", "text": review_data.text,
            "usefulness": {"helpful": 0, "total_votes": 0}
        }

    monkeypatch.setattr("backend.reviews.utils.add_review", fake_add)
    response = client.post("/reviews/m1", json=data)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Amazing"
    assert body["rating"] == 9


def test_add_review_duplicate(monkeypatch, auth_user):
    """POST /reviews/{movie_id} → 400 if user already reviewed."""
    auth_user("member")

    def fake_add(movie_id, review_data, user_id):
        raise ValueError("User already has a review for this movie.")

    monkeypatch.setattr("backend.reviews.utils.add_review", fake_add)
    response = client.post("/reviews/m1", json={"title": "Hi", "rating": 5, "text": "x"})
    assert response.status_code == 400
    assert "already has a review" in response.text

# -------------------------------------------------------------------
# EDIT
# -------------------------------------------------------------------

def test_edit_review_self(monkeypatch, auth_user):
    """PATCH /reviews/{movie_id}/{review_id} → user can edit their own review."""
    user = auth_user("member")

    auth_user("member", user_id="u123")
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "u123"}  # ✅ same id
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    monkeypatch.setattr("backend.reviews.utils.update_review", lambda m, r, u: {
    **fake_review,
    "title": "Updated",
    "rating": 8,
    "date": "2025-01-01",
    "text": "Updated text",
    "usefulness": {"helpful": 1, "total_votes": 2}
})

    response = client.patch("/reviews/m1/r1", json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


def test_edit_review_forbidden(monkeypatch, auth_user):
    """PATCH /reviews/{movie_id}/{review_id} → cannot edit others unless admin."""
    auth_user("member")
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "someone_else"}
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    response = client.patch("/reviews/m1/r1", json={"title": "Hack"})
    assert response.status_code == 403


def test_edit_review_admin(monkeypatch, auth_user):
    """Admin can edit any review."""
    auth_user("administrator")
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "u1"}
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    monkeypatch.setattr("backend.reviews.utils.update_review", lambda m, r, u: {
    **fake_review,
    "title": "AdminEdit",
    "rating": 9,
    "date": "2025-01-01",
    "text": "Updated text",
    "usefulness": {"helpful": 2, "total_votes": 3}
})
    response = client.patch("/reviews/m1/r1", json={"title": "AdminEdit"})
    assert response.status_code == 200
    assert response.json()["title"] == "AdminEdit"

# -------------------------------------------------------------------
# DELETE
# -------------------------------------------------------------------

def test_delete_review_self(monkeypatch, auth_user):
    """DELETE /reviews/{movie_id}/{review_id} → user can delete own."""
    auth_user("member", user_id="u123")
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "u123"}  # ✅ same id
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    monkeypatch.setattr("backend.reviews.utils.delete_review", lambda m, r: True)
    response = client.delete("/reviews/m1/r1")
    assert response.status_code == 200
    assert "deleted" in response.text.lower()


@pytest.mark.parametrize("role", ["administrator", "moderator"])
def test_delete_review_privileged(monkeypatch, auth_user, role):
    """DELETE /reviews/{movie_id}/{review_id} → mods and admins can delete any."""
    auth_user(role)
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "u1"}
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    monkeypatch.setattr("backend.reviews.utils.delete_review", lambda m, r: True)
    response = client.delete("/reviews/m1/r1")
    assert response.status_code == 200


def test_delete_review_forbidden(monkeypatch, auth_user):
    """DELETE /reviews/{movie_id}/{review_id} → forbidden for other users."""
    auth_user("member")
    fake_review = {"review_id": "r1", "movie_id": "m1", "user_id": "another"}
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: fake_review)
    response = client.delete("/reviews/m1/r1")
    assert response.status_code == 403


def test_delete_review_not_found(monkeypatch, auth_user):
    """DELETE /reviews/{movie_id}/{review_id} → 404 if missing."""
    auth_user("administrator")
    monkeypatch.setattr("backend.reviews.utils.get_review", lambda m, r: None)
    response = client.delete("/reviews/m1/r404")
    assert response.status_code == 404

# -------------------------------------------------------------------
# VOTE
# -------------------------------------------------------------------

def test_vote_review_success(monkeypatch, auth_user):
    """POST /reviews/{movie_id}/{review_id}/vote → increments helpful counts."""
    auth_user("member")
    updated = {
    "review_id": "r1",
    "movie_id": "m1",
    "user_id": "u1",
    "title": "Good",
    "rating": 8,
    "date": "2025-01-01",
    "text": "Nice!",
    "usefulness": {"helpful": 1, "total_votes": 1},
}
    monkeypatch.setattr("backend.reviews.utils.add_vote", lambda m, r, v: updated)
    response = client.post("/reviews/m1/r1/vote", json={"vote": True})
    assert response.status_code == 200
    assert response.json()["usefulness"]["helpful"] == 1


def test_vote_review_not_found(monkeypatch, auth_user):
    """POST /reviews/{movie_id}/{review_id}/vote → 404 if review not found."""
    auth_user("member")
    monkeypatch.setattr("backend.reviews.utils.add_vote", lambda m, r, v: None)
    response = client.post("/reviews/m1/r404/vote", json={"vote": True})
    assert response.status_code == 404






# in backend: pytest -v tests/test_reviews.py