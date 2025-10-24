"""
schemas.py – Penalty data models for WatchWorthy.

Admins and moderators can issue penalties that restrict actions like
posting reviews, submitting reports, or accessing the system.

Features:
- Automatic expiry (based on severity/type or optional duration override)
- Computed time remaining (human-readable & numeric)
- Separate schemas for creation vs stored objects
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timedelta
import uuid


# ────────────────────────────────
# Enumerations
# ────────────────────────────────
PenaltyType = Literal[
    "review_ban",       # Cannot post/edit reviews
    "report_ban",       # Cannot submit reports
    "posting_ban",      # Cannot post reviews or reports
    "suspension",       # Account temporarily suspended
    "warning"           # Record-only warning (no expiry)
]

PenaltySeverity = Literal["minor", "moderate", "severe"]
PenaltyStatus = Literal["active", "resolved", "expired"]


# ────────────────────────────────
# Base model (shared fields)
# ────────────────────────────────
class PenaltyBase(BaseModel):
    user_id: str
    type: PenaltyType
    severity: PenaltySeverity = "minor"
    reason: str
    notes: Optional[str] = None


# ────────────────────────────────
# Request model (admin/mod input)
# ────────────────────────────────
class PenaltyCreate(PenaltyBase):
    """
    Schema used when an admin or moderator issues a new penalty.

    Fields required from client:
    - user_id
    - type
    - severity
    - reason
    - (optional) duration_days → custom override for default duration
    """
    duration_days: Optional[int] = None


# ────────────────────────────────
# Stored/response model (full data)
# ────────────────────────────────
class Penalty(PenaltyBase):
    penalty_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issued_by: str
    issued_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    status: PenaltyStatus = "active"

    class Config:
        orm_mode = True  # ensures computed properties show in JSON responses

    # ────────────────────────────────
    # Computed properties
    # ────────────────────────────────
    def has_expired(self) -> bool:
        """Return True if this penalty's expiry date has passed."""
        if not self.expires_at:
            return False
        try:
            return datetime.utcnow() > datetime.fromisoformat(self.expires_at)
        except Exception:
            return False

    @property
    def time_remaining(self) -> Optional[str]:
        """
        Human-readable time left until expiry.
        Examples: '2d 4h remaining', 'Expired', or None if no expiry.
        """
        if not self.expires_at:
            return None  # Permanent or warning
        try:
            remaining = datetime.fromisoformat(self.expires_at) - datetime.utcnow()
            if remaining.total_seconds() <= 0:
                return "Expired"
            days, seconds = remaining.days, remaining.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if days > 0:
                return f"{days}d {hours}h remaining"
            elif hours > 0:
                return f"{hours}h {minutes}m remaining"
            else:
                return f"{minutes}m remaining"
        except Exception:
            return None

    @property
    def time_remaining_seconds(self) -> Optional[int]:
        """Exact seconds remaining until expiry (useful for countdown timers)."""
        if not self.expires_at:
            return None
        try:
            remaining = datetime.fromisoformat(self.expires_at) - datetime.utcnow()
            return max(0, int(remaining.total_seconds()))
        except Exception:
            return None


# ────────────────────────────────
# Helper function for expiry logic
# ────────────────────────────────
def calculate_expiry(
    p_type: PenaltyType,
    severity: PenaltySeverity,
    duration_days: Optional[int] = None
) -> Optional[str]:
    """
    Determine expiry timestamp based on penalty type, severity, or custom override.
    - If duration_days > 0 → use custom override.
    - Otherwise → use default durations based on severity/type.
    - Warnings never expire.
    """
    now = datetime.utcnow()

    # Custom override if positive integer
    if duration_days and duration_days > 0:
        return (now + timedelta(days=duration_days)).isoformat()

    # Warnings never expire
    if p_type == "warning":
        return None

    # Defaults by severity
    match severity:
        case "minor":
            return (now + timedelta(days=3)).isoformat()
        case "moderate":
            return (now + timedelta(days=7)).isoformat()
        case "severe":
            if p_type == "suspension":
                return (now + timedelta(days=30)).isoformat()
            return (now + timedelta(days=14)).isoformat()
        case _:
            return (now + timedelta(days=7)).isoformat()
