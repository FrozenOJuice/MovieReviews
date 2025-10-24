"""
router.py – FastAPI endpoints for managing and viewing user penalties.

Roles:
- Admins/Moderators → can create, view, and resolve penalties.
- Users → can view their own penalties.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from backend.penalties import utils, schemas
from backend.authentication.security import get_current_user


router = APIRouter(prefix="/penalties", tags=["Penalties"])


# ────────────────────────────────
# GET /penalties
# ────────────────────────────────
@router.get("/", response_model=List[schemas.Penalty])
def list_all_penalties(current_user=Depends(get_current_user)):
    """Admins/moderators: view all penalties in the system."""
    if current_user.role not in ["administrator", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    data = [schemas.Penalty(**p) for p in utils._load_penalties()]
    return data


# ────────────────────────────────
# GET /penalties/me
# ────────────────────────────────
@router.get("/me", response_model=List[schemas.Penalty])
def get_my_penalties(current_user=Depends(get_current_user)):
    """Return penalties for the authenticated user."""
    return utils.get_penalties_for_user(current_user.user_id)


# ────────────────────────────────
# GET /penalties/{user_id}
# ────────────────────────────────
@router.get("/{user_id}", response_model=List[schemas.Penalty])
def get_user_penalties(user_id: str, current_user=Depends(get_current_user)):
    """Admins/moderators can view penalties for any user."""
    if current_user.role not in ["administrator", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return utils.get_penalties_for_user(user_id)


# ────────────────────────────────
# POST /penalties
# ────────────────────────────────
@router.post("/", response_model=schemas.Penalty)
def issue_penalty(
    payload: schemas.PenaltyCreate,
    current_user=Depends(get_current_user),
):
    """Admins/moderators: issue a new penalty."""
    if current_user.role not in ["administrator", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    expires_at = schemas.calculate_expiry(payload.type, payload.severity, payload.duration_days)

    full_penalty = schemas.Penalty(
        **payload.dict(exclude={"duration_days"}),
        issued_by=current_user.user_id,
        expires_at=expires_at,
    )

    saved = utils.add_penalty(full_penalty)
    return saved


# ────────────────────────────────
# PATCH /penalties/{penalty_id}
# ────────────────────────────────
@router.patch("/{penalty_id}")
def resolve_penalty(
    penalty_id: str,
    notes: Optional[str] = Query(None, description="Notes for resolution"),
    current_user=Depends(get_current_user),
):
    """Resolve or lift a penalty (admin/mod only)."""
    if current_user.role not in ["administrator", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    utils.resolve_penalty(penalty_id, moderator_id=current_user.user_id, notes=notes)
    return {"message": f"Penalty {penalty_id} resolved successfully."}


# ────────────────────────────────
# DELETE /penalties/{penalty_id}
# ────────────────────────────────
@router.delete("/{penalty_id}")
def delete_penalty(
    penalty_id: str,
    current_user=Depends(get_current_user),
):
    """Admins can permanently delete a penalty record."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Admins only")

    data = utils._load_penalties()
    updated = [p for p in data if p["penalty_id"] != penalty_id]
    if len(updated) == len(data):
        raise HTTPException(status_code=404, detail="Penalty not found")

    utils._save_penalties(updated)
    return {"message": f"Penalty {penalty_id} deleted successfully."}
