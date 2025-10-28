"""
Utility functions for managing users stored in JSON files.
Handles reading, writing, updating, and deleting user records.
"""

import os, json, uuid
from passlib.context import CryptContext
from fastapi import HTTPException
from backend.users import schemas
from backend.authentication import security

# 📁 File paths
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "users")
ACTIVE_FILE = os.path.join(BASE_DIR, "users_active.json")
INACTIVE_FILE = os.path.join(BASE_DIR, "users_inactive.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# 🔹 Helper functions
# =========================

def _load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def load_active_users():
    return _load_json(ACTIVE_FILE)


def load_inactive_users():
    return _load_json(INACTIVE_FILE)


def get_user_by_id(user_id: str):
    users = load_active_users() + load_inactive_users()
    for user in users:
        if user["user_id"] == user_id:
            return user
    return None


def add_user(new_user: schemas.UserCreate):
    users = load_active_users()

    # Prevent duplicates
    if any(u["email"] == new_user.email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pw = pwd_context.hash(new_user.password)
    user_obj = {
        "user_id": str(uuid.uuid4()),
        "username": new_user.username,
        "email": new_user.email,
        "hashed_password": hashed_pw,
        "role": new_user.role,
        "status": new_user.status,
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    users.append(user_obj)
    _save_json(ACTIVE_FILE, users)
    return user_obj


def update_user(user_id: str, updates: dict):
    users = load_active_users()
    for user in users:
        if user["user_id"] == user_id:
            user.update(updates)
            _save_json(ACTIVE_FILE, users)
            return user
    raise HTTPException(status_code=404, detail="User not found.")


def update_user_status(user_id: str, status: str):
    """Update active/inactive status and move between files if needed."""
    active = load_active_users()
    inactive = load_inactive_users()

    # Move user between lists based on new status
    for user_list, target_list, current_status in [
        (active, inactive, "inactive"),
        (inactive, active, "active"),
    ]:
        for user in user_list:
            if user["user_id"] == user_id:
                user["status"] = status
                if status == current_status:
                    raise HTTPException(status_code=400, detail="Already in that state.")
                target_list.append(user)
                user_list.remove(user)
                _save_json(ACTIVE_FILE, active)
                _save_json(INACTIVE_FILE, inactive)
                return {"message": f"User {user_id} moved to {status}."}

    raise HTTPException(status_code=404, detail="User not found.")


def change_password(user_id: str, old_password: str, new_password: str):
    users = load_active_users()
    for user in users:
        if user["user_id"] == user_id:
            if not pwd_context.verify(old_password, user["hashed_password"]):
                raise HTTPException(status_code=403, detail="Incorrect old password.")
            user["hashed_password"] = pwd_context.hash(new_password)
            _save_json(ACTIVE_FILE, users)
            return
    raise HTTPException(status_code=404, detail="User not found.")


def delete_user(user_id: str):
    users = load_active_users()
    updated = [u for u in users if u["user_id"] != user_id]
    if len(users) == len(updated):
        raise HTTPException(status_code=404, detail="User not found.")
    _save_json(ACTIVE_FILE, updated)
