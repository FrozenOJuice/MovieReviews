from pydantic import BaseModel
from typing import List, Optional


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
    sort_by: Optional[str] = "imdb_rating"  # default
    order: Optional[str] = "desc"
    page: Optional[int] = 1
    limit: Optional[int] = 20


class WatchLaterUpdate(BaseModel):
    movie_id: str
    action: str  # "add" or "remove"
