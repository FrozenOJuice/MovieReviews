"""
Handles user profile management and administrative user control.

Includes:
- Self-profile routes (/users/me)
- Admin-level CRUD routes (/users/, /users/{user_id})
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.authentication.security import get_current_user
from backend.users import utils, schemas

router = APIRouter(prefix="/users", tags=["Users"])


# =========================
# 🔹 SELF ROUTES
# =========================

@router.get("/me", response_model=schemas.UserPublic)
def get_my_profile(current_user: schemas.UserToken = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    user = utils.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/me", response_model=schemas.UserPublic)
def update_my_profile(
    update: schemas.UserSelfUpdate,
    current_user: schemas.UserToken = Depends(get_current_user),
):
    """Allow user to update their own profile (email, username)."""
    return utils.update_user(current_user.user_id, update.dict(exclude_unset=True))


@router.patch("/me/password")
def change_my_password(
    update: schemas.PasswordChange,
    current_user: schemas.UserToken = Depends(get_current_user),
):
    """Allow user to change their own password."""
    utils.change_password(current_user.user_id, update.old_password, update.new_password)
    return {"message": "Password updated successfully."}


@router.patch("/me/status")
def change_my_status(
    update: schemas.StatusUpdate,
    current_user: schemas.UserToken = Depends(get_current_user),
):
    """Allow users to activate or deactivate their own account."""
    # ✅ Only allow 'active' or 'inactive'
    if update.status not in ["active", "inactive"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be 'active' or 'inactive'."
        )

    return utils.update_user_status(current_user.user_id, update.status)


# =========================
# 🔹 ADMIN ROUTES
# =========================

@router.get("/", response_model=list[schemas.UserPublic])
def list_users(current_user: schemas.UserToken = Depends(get_current_user)):
    """Admin: list all active users."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized.")
    return utils.load_active_users()


@router.get("/{user_id}", response_model=schemas.UserPublic)
def get_user(user_id: str, current_user: schemas.UserToken = Depends(get_current_user)):
    """Admin: get a specific user by ID."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized.")
    user = utils.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/{user_id}", response_model=schemas.UserPublic)
def update_user_admin(
    user_id: str,
    update: schemas.UserAdminUpdate,
    current_user: schemas.UserToken = Depends(get_current_user),
):
    """Admin: update another user's info (role, status, email, etc.)."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized.")
    return utils.update_user(user_id, update.dict(exclude_unset=True))


@router.delete("/{user_id}")
def delete_user(
    user_id: str, current_user: schemas.UserToken = Depends(get_current_user)
):
    """Admin: delete/deactivate a user."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized.")
    utils.delete_user(user_id)
    return {"message": f"User {user_id} deleted."}


@router.post("/", response_model=schemas.UserPublic)
def create_user_admin(
    new_user: schemas.UserCreate,
    current_user: schemas.UserToken = Depends(get_current_user),
):
    """Admin: manually create a new user."""
    if current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Not authorized.")
    return utils.add_user(new_user)
