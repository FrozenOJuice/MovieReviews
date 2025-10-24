import os
from typing import List, Dict
from backend.authentication.utils import load_all_users, _save_json
from backend.movies.utils import load_movies
from backend.reviews.utils import load_reviews

def get_watch_later_movies(user_id: str) -> List[Dict]:
    """Get detailed movie data for user's watch later list"""
    users = load_all_users()
    user = next((u for u in users if u["user_id"] == user_id), None)
    if not user:
        return []
    
    watch_later_ids = user.get("watch_later", [])
    all_movies = load_movies()
    
    return [movie for movie in all_movies if movie["movie_id"] in watch_later_ids]

def get_user_reviews(user_id: str) -> List[Dict]:
    """Get all reviews by a user across all movies"""
    all_reviews = []
    movies_dir = os.path.join(os.path.dirname(__file__), "..", "data", "movies")
    
    # Get all movie files
    import glob
    movie_files = glob.glob(os.path.join(movies_dir, "*.json"))
    
    for movie_file in movie_files:
        movie_id = os.path.basename(movie_file).replace('.json', '')
        reviews = load_reviews(movie_id)
        user_reviews = [r for r in reviews if r["user_id"] == user_id]
        all_reviews.extend(user_reviews)
    
    # Sort by date descending
    all_reviews.sort(key=lambda x: x.get("date", ""), reverse=True)
    return all_reviews

def get_current_timestamp() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()