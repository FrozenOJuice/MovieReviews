import os, json, tempfile, shutil
from typing import List, Dict, Optional
from datetime import datetime
from backend.reviews import schemas
from backend.authentication.utils import _convert_datetime_to_string, load_active_users, save_active_users

# Base directory for review JSON files
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reviews")


def _get_review_path(movie_id: str) -> str:
    os.makedirs(BASE_DIR, exist_ok=True)
    return os.path.join(BASE_DIR, f"{movie_id}_reviews.json")


def load_reviews(movie_id: str) -> List[Dict]:
    path = _get_review_path(movie_id)
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"[WARNING] Corrupted review file for movie {movie_id}. Resetting...")
        with open(path, "w") as f:
            json.dump([], f)
        return []


def save_reviews(movie_id: str, reviews: List[Dict]) -> None:
    """Safely write reviews to disk (atomic write)."""
    path = _get_review_path(movie_id)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    os.close(tmp_fd)

    try:
        with open(tmp_path, "w") as f:
            json.dump(_convert_datetime_to_string(reviews), f, indent=2)
        shutil.move(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def user_already_reviewed(movie_id: str, user_id: str) -> bool:
    """Return True if user already reviewed this movie (using movies_reviewed list)."""
    users = load_active_users()
    for user in users:
        if user["user_id"] == user_id:
            return movie_id in user.get("movies_reviewed", [])
    return False


def add_review(movie_id: str, review_data: schemas.ReviewCreate, user_id: str) -> schemas.Review:
    reviews = load_reviews(movie_id)

    # Restrict one review per user per movie
    if any(r["user_id"] == user_id for r in reviews):
        raise ValueError("User already has a review for this movie.")

    new_review = schemas.Review(
        movie_id=movie_id,
        user_id=user_id,
        title=review_data.title,
        rating=review_data.rating,
        text=review_data.text,
    ).dict()

    # ✅ Save the review
    reviews.append(new_review)
    save_reviews(movie_id, reviews)

    # ✅ Update user's movies_reviewed (store movie_id, not review_id)
    users = load_active_users()
    for user in users:
        if user["user_id"] == user_id:
            user.setdefault("movies_reviewed", [])
            if movie_id not in user["movies_reviewed"]:
                user["movies_reviewed"].append(movie_id)
            break
    save_active_users(users)

    return new_review


def get_review(movie_id: str, review_id: str) -> Optional[Dict]:
    reviews = load_reviews(movie_id)
    for r in reviews:
        if r["review_id"] == review_id:
            return r
    return None


def update_review(movie_id: str, review_id: str, updates: schemas.ReviewUpdate) -> Optional[Dict]:
    reviews = load_reviews(movie_id)
    for review in reviews:
        if review["review_id"] == review_id:
            for key, value in updates.dict(exclude_unset=True).items():
                review[key] = value
            review["date"] = datetime.utcnow().date().isoformat()
            save_reviews(movie_id, reviews)
            return review
    return None


def delete_review(movie_id: str, review_id: str) -> bool:
    reviews = load_reviews(movie_id)
    updated = [r for r in reviews if r["review_id"] != review_id]
    if len(updated) == len(reviews):
        return False
    save_reviews(movie_id, updated)
    return True


def add_vote(movie_id: str, review_id: str, vote: schemas.Vote) -> Optional[Dict]:
    reviews = load_reviews(movie_id)
    for review in reviews:
        if review["review_id"] == review_id:
            review["usefulness"]["total_votes"] += 1
            if vote.vote:
                review["usefulness"]["helpful"] += 1
            save_reviews(movie_id, reviews)
            return review
    return None


def filter_sort_reviews(
    movie_id: str,
    rating: Optional[int] = None,
    sort_by: str = "date",
    order: str = "desc",
    skip: int = 0,
    limit: int = 20,
) -> List[Dict]:
    """Filter, sort, and paginate reviews for a given movie."""
    reviews = load_reviews(movie_id)

    # Filter by rating
    if rating is not None:
        reviews = [r for r in reviews if r.get("rating") == rating]

    # Sorting
    reverse = order.lower() == "desc"
    if sort_by in {"date", "rating"}:
        reviews.sort(key=lambda r: r.get(sort_by), reverse=reverse)
    elif sort_by == "helpful":
        reviews.sort(key=lambda r: r["usefulness"]["helpful"], reverse=reverse)
    elif sort_by == "total_votes":
        reviews.sort(key=lambda r: r["usefulness"]["total_votes"], reverse=reverse)

    return reviews[skip: skip + limit]
