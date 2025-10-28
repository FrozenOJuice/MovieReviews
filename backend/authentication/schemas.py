from pydantic import BaseModel, EmailStr, validator
import re
from enum import Enum
from typing import List, Optional, Dict

# USER ROLE HIERARCHY
class UserRole(str, Enum):
    GUEST = "guest"           # 👥 Browse only
    MEMBER = "member"         # 👤 Basic user - rate/review
    CRITIC = "critic"         # 📝 Featured reviewer
    MODERATOR = "moderator"   # 🛡️ Content moderator
    ADMINISTRATOR = "administrator"  # ⚙️ System administrator

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# USER REGISTRATION CONTRACT
class UserCreate(BaseModel):
    username: str
    email: EmailStr  # Built-in email validation
    password: str
    role: UserRole = UserRole.MEMBER  # Default to member role

    # USERNAME VALIDATION PROCESS
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v
    
    # PASSWORD VALIDATION PROCESS
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters")
        return v

# USER RESPONSE CONTRACT (Safe data - no passwords)
class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    status: str
    movies_reviewed: List = []
    watch_later: List = []
    penalties: List[Dict] = []

# USER LOGIN CONTRACT
class UserLogin(BaseModel):
    username: str
    password: str

# TOKEN RESPONSE CONTRACT
class Token(BaseModel):
    access_token: str  # 🔑 JWT token
    token_type: str = "bearer"  # 🏷️ Standard token type

# TOKEN DATA CONTRACT (What's embedded in JWT)
class TokenData(BaseModel):
    user_id: Optional[str] = None  # 👤 User identifier
    role: Optional[str] = None     # 🎭 User role for authorization
    status: Optional[str] = None
