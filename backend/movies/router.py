from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
from backend.authentication.security import get_current_user
from backend.movies import utils, schemas
import os, json

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

    export_path = os.path.join(utils.MOVIES_DIR, "_all_movies.json")

    # Write export file
    with open(export_path, "w") as f:
        json.dump(movies, f, indent=4)

    # Schedule deletion after response is sent
    background_tasks.add_task(os.remove, export_path)

    return FileResponse(
        export_path,
        filename="movies.json",
        media_type="application/json",
        background=background_tasks
    )

# ---------------- Watch-Later Routes ----------------
@router.get("/watch-later")
def get_watch_later(
    current_user: dict = Depends(get_current_user),
    user_id: Optional[str] = Query(None, description="Admin can specify another user ID")
):
    """
    Regular users → view their own watch-later list.
    Admins → can view any user's watch-later list by passing ?user_id=<target_id>.
    """
    target_id = current_user.user_id

    # Admin override
    if user_id:
        if current_user.role != "administrator":
            raise HTTPException(status_code=403, detail="Not authorized to view other users' lists.")
        target_id = user_id

    movies = utils.get_watch_later(target_id)
    return {"user_id": target_id, "watch_later": movies}


@router.patch("/watch-later")
def modify_watch_later(
    update: schemas.WatchLaterUpdate,
    current_user: dict = Depends(get_current_user),
    user_id: Optional[str] = Query(None, description="Admin can modify another user’s list")
):
    """
    Regular users → can only modify their own watch-later.
    Admins → can modify another user's list using ?user_id=<target_id>.
    """
    if update.action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'add' or 'remove'.")

    movie = utils.get_movie(update.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    target_id = current_user.user_id

    # Admin override
    if user_id:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Not authorized to modify other users' lists.")
        target_id = user_id

    utils.update_watch_later(target_id, update.movie_id, update.action)
    return {"message": f"Movie {update.action}ed to {('user '+target_id) if user_id else 'your'} watch-later list."}




@router.get("/", response_model=List[schemas.Movie])
def list_movies(
    params: schemas.MovieSearchParams = Depends(),
    current_user: dict = Depends(get_current_user)
):
    movies = utils.load_movies()

    movies = utils.filter_movies(movies, params)
    movies = utils.sort_movies(movies, params.sort_by, params.order)
    movies = utils.paginate_movies(movies, params.page, params.limit)
    return movies


@router.get("/{movie_id}", response_model=schemas.Movie)
def get_movie(movie_id: str, current_user: dict = Depends(get_current_user)):
    movie = utils.get_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie





