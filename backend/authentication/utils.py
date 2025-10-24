import os, json
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.authentication import schemas


# DATA STORAGE CONFIGURATION
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'users')
ACTIVE_FILE = os.path.join(BASE_DIR, 'users_active.json')
INACTIVE_FILE = os.path.join(BASE_DIR, 'users_inactive.json')
REVOKED_TOKENS_FILE = os.path.join(BASE_DIR, "revoked_tokens.json")

def _convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetime_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_to_string(item) for item in obj]
    else:
        return obj

# Helper to load a JSON file
def _load_json(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Helper to save a JSON file
def _save_json(file_path: str, data: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # Convert datetime objects to strings before saving
    data_serializable = _convert_datetime_to_string(data)
    with open(file_path, 'w') as f:
        json.dump(data_serializable, f, indent=4)


# Load all users (active + inactive)
def load_all_users() -> List[Dict[str, Any]]:
    return _load_json(ACTIVE_FILE) + _load_json(INACTIVE_FILE)

# Load active users
def load_active_users() -> List[Dict[str, Any]]:
    return _load_json(ACTIVE_FILE)
# Save activeusers
def save_active_users(users: List[Dict[str, Any]]):
    _save_json(ACTIVE_FILE, users)

# Load inactive users
def load_inactive_users() -> List[Dict[str, Any]]:
    return _load_json(INACTIVE_FILE)
# Save inactive users
def save_inactive_users(users: List[Dict[str, Any]]):
    _save_json(INACTIVE_FILE, users)



# Check username/email uniqueness
def user_exists(username: str, email: str) -> tuple[bool, Optional[str]]:
    users = load_all_users()
    username_taken = any(u['username'] == username for u in users)
    email_taken = any(u['email'] == email for u in users)
    if username_taken and email_taken:
        return True, "Username and Email already taken"
    elif username_taken:
        return True, "Username already taken"
    elif email_taken:
        return True, "Email already taken"
    return False, None

# Save new user upon registration
def add_user(user: Dict[str, Any], active: bool = True):
    # Ensure penalties array exists
    if 'penalties' not in user:
        user['penalties'] = []
    
    if active:
        users = load_active_users()
        users.append(user)
        save_active_users(users)
    else:
        users = load_inactive_users()
        users.append(user)
        save_inactive_users(users)


# Get user by ID (search active + inactive)
def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    for user in load_all_users():
        if user['user_id'] == user_id:
            return user
    return None

# Get user by username (search active + inactive)
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    for user in load_all_users():
        if user['username'] == username:
            return user
    return None


# Update user status (move between files)
def update_user_status(user_id: str, status: schemas.UserStatus) -> bool:
    active_users = load_active_users()
    inactive_users = load_inactive_users()

    # Remove from both in case duplicates
    user = None
    active_users = [u for u in active_users if not (u['user_id'] == user_id and (user := u))]
    inactive_users = [u for u in inactive_users if not (u['user_id'] == user_id and (user := u))]

    if not user:
        return False

    user['status'] = status.value
    if status == schemas.UserStatus.ACTIVE:
        active_users.append(user)
    else:
        inactive_users.append(user)

    save_active_users(active_users)
    save_inactive_users(inactive_users)
    return True





def load_revoked_tokens() -> list[str]:
    """Load revoked tokens safely."""
    if not os.path.exists(REVOKED_TOKENS_FILE):
        return []
    with open(REVOKED_TOKENS_FILE, "r") as f:
        try:
            content = f.read().strip()
            return json.loads(content) if content else []
        except json.JSONDecodeError:
            return []


def save_revoked_tokens(tokens: list[str]):
    os.makedirs(os.path.dirname(REVOKED_TOKENS_FILE), exist_ok=True)
    with open(REVOKED_TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=4)