# 🎬 Movies Router — Handles all movie browsing and watch-later features.
# 🔧 Updated for cleaner admin logic, improved type consistency, and better file handling.

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
from backend.authentication.security import get_current_user
from backend.movies import utils, schemas
import os, json, tempfile
from backend.penalties import utils as penalty_utils

router = APIRouter(prefix="/movies", tags=["Movies"])

@router.get("/download")
def download_movies(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Combine all individual movie JSONs into one downloadable file.
    Automatically deletes the temporary export file after sending.
    """
    movies = utils.load_movies()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp_file.name, "w") as f:
        json.dump(movies, f, indent=4)

    background_tasks.add_task(os.remove, tmp_file.name)

    return FileResponse(
        tmp_file.name,
        filename="movies.json",
        media_type="application/json"
    )


# ---------------- Watch-Later Routes ----------------
@router.get("/watch-later", response_model=schemas.WatchLaterResponse)
def get_watch_later(
    current_user: schemas.UserToken = Depends(get_current_user),
    user_id: Optional[str] = Query(None, description="Admin can specify another user ID")
):
    """
    Regular users → view their own watch-later list.
    Admins → can view any user's watch-later list by passing ?user_id=<target_id>.
    """
    target_id = current_user.user_id

    if user_id:
        if current_user.role != "administrator":
            raise HTTPException(status_code=403, detail="Not authorized to view other users' lists.")
        target_id = user_id

    movies = utils.get_watch_later(target_id)
    return {"user_id": target_id, "watch_later": movies}


@router.patch("/watch-later")
def modify_watch_later(
    update: schemas.WatchLaterUpdate,
    current_user: schemas.UserToken = Depends(get_current_user),
    user_id: Optional[str] = Query(None, description="Admin can modify another user’s list")
):
    """
    Regular users → can only modify their own watch-later.
    Admins → can modify another user's list using ?user_id=<target_id>.
    Restricted by penalties:
    - suspension
    """
    # 🔒 Check for suspension
    restriction = penalty_utils.check_active_penalty(current_user.user_id, ["suspension"])
    if restriction:
        raise HTTPException(status_code=403, detail=restriction)

    # Validate action
    if update.action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'add' or 'remove'.")

    # Check movie existence
    movie = utils.get_movie(update.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Determine target
    target_id = current_user.user_id
    if user_id:
        if current_user.role != "administrator":
            raise HTTPException(status_code=403, detail="Not authorized to modify other users' lists.")
        target_id = user_id

    utils.update_watch_later(target_id, update.movie_id, update.action)
    return {"message": f"Movie {update.action}ed to {('user '+target_id) if user_id else 'your'} watch-later list."}


@router.get("/", response_model=List[schemas.Movie])
def list_movies(
    params: schemas.MovieSearchParams = Depends(),
    current_user: schemas.UserToken = Depends(get_current_user)
):
    movies = utils.load_movies()
    movies = utils.filter_movies(movies, params)
    movies = utils.sort_movies(movies, params.sort_by, params.order)
    movies = utils.paginate_movies(movies, params.page, params.limit)
    return movies

# ✅ /movies/search alias → same functionality as /movies/
# Don't know if I even need this route
@router.get("/search", response_model=List[schemas.Movie])
def search_movies(
    params: schemas.MovieSearchParams = Depends(),
    current_user: schemas.UserToken = Depends(get_current_user)
):
    """Alias for /movies/ — same search, filter, and pagination logic."""
    return list_movies(params=params, current_user=current_user)

@router.get("/{movie_id}", response_model=schemas.Movie)
def get_movie(movie_id: str, current_user: schemas.UserToken = Depends(get_current_user)):
    movie = utils.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


# Suggestions
# 