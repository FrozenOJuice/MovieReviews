"""
Pydantic schemas for user management and admin CRUD operations.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from uuid import uuid4


# =========================
# 🔹 BASE SCHEMAS
# =========================

class UserPublic(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str
    status: str
    movies_reviewed: List[str]
    watch_later: List[str]
    penalties: List[str]


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = Field(default="member")
    status: str = Field(default="active")


class UserSelfUpdate(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class StatusUpdate(BaseModel):
    status: str


class UserAdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None


# =========================
# 🔹 TOKEN SCHEMA
# =========================

class UserToken(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str
