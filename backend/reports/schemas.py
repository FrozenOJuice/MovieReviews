"""
Defines the data models and enums for the Reports module.
Improved schema adds stronger field names, cross-linking, and moderation tracking.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


# --- ENUMS ---
class ReportStatus(str, Enum):
    pending = "pending"
    under_review = "under_review"
    resolved = "resolved"
    dismissed = "dismissed"


class ReportType(str, Enum):
    review = "review"
    user = "user"
    movie = "movie"
    comment = "comment"


# --- BASE SCHEMAS ---
class ReportBase(BaseModel):
    """Shared fields across ReportCreate and Report."""
    type: ReportType = Field(..., description="What is being reported: user, review, movie, etc.")
    reported_id: str = Field(..., description="ID of the item or user being reported.")
    reason: str = Field(..., description="Short explanation or reason for the report.")


# --- CREATE SCHEMA ---
class ReportCreate(ReportBase):
    """Schema used when submitting a new report."""
    pass


# --- UPDATE SCHEMA ---
class ReportUpdate(BaseModel):
    """Schema used when moderator/admin updates report status or notes."""
    status: ReportStatus
    moderator_notes: Optional[str] = Field(None, description="Moderator remarks or decisions.")


# --- MAIN SCHEMA ---
class Report(ReportBase):
    """Full stored report with metadata."""
    report_id: str
    reporter_id: str = Field(..., description="User ID of the person submitting the report.")
    status: ReportStatus = ReportStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None, description="When the report was resolved/dismissed.")
    moderator_id: Optional[str] = Field(None, description="Admin/moderator who reviewed the report.")
    moderator_notes: Optional[str] = None


# --- SUMMARY SCHEMA (optional dashboard endpoint) ---
class ReportSummary(BaseModel):
    total_reports: int
    pending: int
    under_review: int
    resolved: int
    dismissed: int
