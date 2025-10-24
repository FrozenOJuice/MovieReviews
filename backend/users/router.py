from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from backend.authentication.security import get_current_user, require_admin
from backend.authentication import utils as auth_utils
from backend.authentication import schemas as auth_schemas
from backend.users import schemas, utils
import uuid

router = APIRouter(prefix="/users", tags=["Users"])

# User Dashboard
@router.get("/dashboard", response_model=schemas.UserDashboard)
async def get_dashboard(current_user: auth_schemas.TokenData = Depends(get_current_user)):
    """Get user-specific dashboard data"""
    user_data = auth_utils.get_user_by_id(current_user.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's watch later movies
    watch_later_movies = utils.get_watch_later_movies(current_user.user_id)
    
    # Get user's reviews
    user_reviews = utils.get_user_reviews(current_user.user_id)
    
    return {
        "user": user_data,
        "watch_later": watch_later_movies,
        "recent_reviews": user_reviews[:5],  # Last 5 reviews
        "penalties": user_data.get("penalties", []),
        "stats": {
            "reviews_count": len(user_reviews),
            "watch_later_count": len(watch_later_movies),
            "penalties_count": len(user_data.get("penalties", []))
        }
    }

# Admin: Get all users
@router.get("/", response_model=List[schemas.UserAdminResponse])
async def get_all_users(
    current_user: auth_schemas.TokenData = Depends(require_admin),
    status: Optional[auth_schemas.UserStatus] = Query(None),
    role: Optional[auth_schemas.UserRole] = Query(None)
):
    """Admin: Get all users with filtering"""
    users = auth_utils.load_all_users()
    
    if status:
        users = [u for u in users if u["status"] == status.value]
    if role:
        users = [u for u in users if u["role"] == role.value]
    
    return users

# Admin: Update user status
@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_update: schemas.UserStatusUpdate,
    current_user: auth_schemas.TokenData = Depends(require_admin)
):
    """Admin: Activate/deactivate user account"""
    success = auth_utils.update_user_status(user_id, status_update.status)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User status updated to {status_update.status.value}"}

# Admin: Apply penalty
@router.post("/{user_id}/penalties")
async def apply_penalty(
    user_id: str,
    penalty: schemas.PenaltyCreate,
    current_user: auth_schemas.TokenData = Depends(require_admin)
):
    """Admin: Apply penalty to user"""
    user = auth_utils.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_penalty = {
        "penalty_id": str(uuid.uuid4()),
        "type": penalty.type,
        "reason": penalty.reason,
        "applied_by": current_user.user_id,
        "applied_at": utils.get_current_timestamp(),
        "expires_at": penalty.expires_at,
        "status": "active"
    }
    
    if "penalties" not in user:
        user["penalties"] = []
    user["penalties"].append(new_penalty)
    
    # Update user in storage
    auth_utils.update_user_status(user_id, user["status"])  # This will save the user
    
    return {"message": "Penalty applied successfully", "penalty": new_penalty}

# Admin: Remove penalty
@router.delete("/{user_id}/penalties/{penalty_id}")
async def remove_penalty(
    user_id: str,
    penalty_id: str,
    current_user: auth_schemas.TokenData = Depends(require_admin)
):
    """Admin: Remove penalty from user"""
    user = auth_utils.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    penalties = user.get("penalties", [])
    initial_count = len(penalties)
    user["penalties"] = [p for p in penalties if p["penalty_id"] != penalty_id]
    
    if len(user["penalties"]) == initial_count:
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    # Update user in storage
    auth_utils.update_user_status(user_id, user["status"])
    
    return {"message": "Penalty removed successfully"}