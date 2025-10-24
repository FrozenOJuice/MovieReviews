"""
Defines the data models and enums for report management.
"""

from pydantic import BaseModel
from enum import Enum
from typing import Optional


class ReportStatus(str, Enum):
    pending = "pending"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(BaseModel):
    id: str
    reported_item: str
    type: str  # e.g., "review", "user", "comment"
    reason: str
    reporter_id: str
    status: ReportStatus
    created_at: str


class ReportCreate(BaseModel):
    reported_item: str
    type: str
    reason: str


class ReportUpdate(BaseModel):
    status: ReportStatus


class ReportSummary(BaseModel):
    total_reports: int
    pending: int
    resolved: int
    dismissed: int
