from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from backend.reviews import utils, schemas
from backend.authentication.security import get_current_user

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/{movie_id}", response_model=List[schemas.Review])
def list_reviews(
    movie_id: str,
    rating: Optional[int] = Query(None, description="Filter by rating (1–10)"),
    sort_by: str = Query("date", description="Sort by date, rating, helpful, total_votes"),
    order: str = Query("desc", description="Order: asc or desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user)
):
    """List reviews with optional filtering, sorting, and pagination."""
    return utils.filter_sort_reviews(
        movie_id=movie_id,
        rating=rating,
        sort_by=sort_by,
        order=order,
        skip=skip,
        limit=limit
    )


@router.get("/{movie_id}/{review_id}", response_model=schemas.Review)
def get_review(movie_id: str, review_id: str, current_user=Depends(get_current_user)):
    review = utils.get_review(movie_id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/{movie_id}", response_model=schemas.Review)
def add_review(movie_id: str, review_data: schemas.ReviewCreate, current_user=Depends(get_current_user)):
    """Add a new review for a movie — limited to 1 per user."""
    try:
        return utils.add_review(movie_id, review_data, current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{movie_id}/{review_id}", response_model=schemas.Review)
def edit_review(movie_id: str, review_id: str, updates: schemas.ReviewUpdate, current_user=Depends(get_current_user)):
    """Edit a review (only the author or an admin)."""
    review = utils.get_review(movie_id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Only owner or admin can edit
    if review["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this review")

    updated = utils.update_review(movie_id, review_id, updates)
    return updated


@router.delete("/{movie_id}/{review_id}")
def delete_review(movie_id: str, review_id: str, current_user=Depends(get_current_user)):
    """Delete a review (only the author or an admin)."""
    review = utils.get_review(movie_id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Only owner or admin can delete
    if review["user_id"] != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")

    deleted = utils.delete_review(movie_id, review_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted"}


@router.post("/{movie_id}/{review_id}/vote", response_model=schemas.Review)
def vote_review(movie_id: str, review_id: str, vote: schemas.Vote, current_user=Depends(get_current_user)):
    """Vote whether a review was helpful or not."""
    updated = utils.add_vote(movie_id, review_id, vote)
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")
    return updated
