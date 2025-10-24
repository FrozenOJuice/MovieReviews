# 🎬 Movies Schemas — Pydantic models for validation, filtering, and watch-later management.
# ✅ Added WatchLaterResponse model for cleaner documentation and typing.

from pydantic import BaseModel
from typing import List, Optional, Literal


class Movie(BaseModel):
    movie_id: str
    title: str
    imdb_rating: Optional[float] = None
    meta_score: Optional[int] = None
    genres: List[str]
    directors: List[str]
    release_date: Optional[str] = None
    duration: Optional[int] = None
    description: Optional[str] = None
    main_stars: List[str]
    total_user_reviews: Optional[int] = None
    total_critic_reviews: Optional[int] = None
    total_rating_count: Optional[int] = None
    source_folder: Optional[str] = None


class MovieSearchParams(BaseModel):
    query: Optional[str] = None
    genre: Optional[str] = None
    director: Optional[str] = None
    star: Optional[str] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    sort_by: Optional[str] = "imdb_rating"
    order: Optional[str] = "desc"
    page: Optional[int] = 1
    limit: Optional[int] = 20


class WatchLaterUpdate(BaseModel):
    movie_id: str
    action: Literal["add", "remove"]


# ✅ NEW: response schema for /watch-later routes
class WatchLaterResponse(BaseModel):
    user_id: str
    watch_later: List[Movie]


# ✅ Helper schema for authenticated users (used in router typing)
class UserToken(BaseModel):
    user_id: str
    username: str
    role: str
