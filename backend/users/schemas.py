from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from backend.authentication import schemas as auth_schemas

class Penalty(BaseModel):
    penalty_id: str
    type: str  # "late_review", "spam", "inappropriate_content", etc.
    reason: str
    applied_by: str  # admin user_id
    applied_at: str
    expires_at: Optional[str] = None
    status: str  # "active", "expired", "revoked"

class UserDashboard(BaseModel):
    user: dict
    watch_later: List[dict]
    recent_reviews: List[dict]
    penalties: List[Penalty]
    stats: dict

class UserAdminResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    status: str
    movies_reviewed: List[str]
    watch_later: List[str]
    penalties: List[Penalty]
    created_at: Optional[str] = None

class UserStatusUpdate(BaseModel):
    status: auth_schemas.UserStatus

class PenaltyCreate(BaseModel):
    type: str
    reason: str
    expires_at: Optional[str] = None