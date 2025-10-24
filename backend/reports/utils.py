"""
Utility functions for loading, saving, and managing report data in JSON files.
Now aligned with the improved Report schema (report_id, reporter_id, reported_id, etc.).
"""

import os, json, uuid
from typing import List, Optional
from datetime import datetime
from backend.reports import schemas

REPORTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "reports", "reports.json")


# --- Internal Helpers ---
def _load_json() -> List[dict]:
    """Load the reports JSON file safely."""
    if not os.path.exists(REPORTS_FILE):
        return []
    try:
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def _save_json(data: List[dict]) -> None:
    """Write updated report data back to file."""
    os.makedirs(os.path.dirname(REPORTS_FILE), exist_ok=True)
    with open(REPORTS_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)


# --- CRUD Operations ---
def load_reports() -> List[schemas.Report]:
    """Return all reports as Pydantic models."""
    return [schemas.Report(**r) for r in _load_json()]


def get_report(report_id: str) -> Optional[schemas.Report]:
    """Fetch specific report by ID."""
    for report in _load_json():
        if report["report_id"] == report_id:
            return schemas.Report(**report)
    return None


def create_report(reporter_id: str, reported_id: str, type: schemas.ReportType, reason: str) -> schemas.Report:
    """Create and persist a new report."""
    reports = _load_json()
    new_report = schemas.Report(
        report_id=str(uuid.uuid4()),
        reporter_id=reporter_id,
        reported_id=reported_id,
        type=type,
        reason=reason,
        status=schemas.ReportStatus.pending,
        created_at=datetime.utcnow(),
        resolved_at=None,
        moderator_id=None,
        moderator_notes=None,
    )
    reports.append(new_report.dict())
    _save_json(reports)
    return new_report


def update_report_status(report_id: str, update: schemas.ReportUpdate, moderator_id: str) -> Optional[schemas.Report]:
    """Update the status and moderator info for a report."""
    reports = _load_json()
    for report in reports:
        if report["report_id"] == report_id:
            report["status"] = update.status
            report["moderator_id"] = moderator_id
            report["moderator_notes"] = update.moderator_notes
            if update.status in [schemas.ReportStatus.resolved, schemas.ReportStatus.dismissed]:
                report["resolved_at"] = datetime.utcnow().isoformat()
            _save_json(reports)
            return schemas.Report(**report)
    return None


def delete_report(report_id: str) -> bool:
    """Delete a report by ID."""
    reports = _load_json()
    updated = [r for r in reports if r["report_id"] != report_id]
    if len(updated) == len(reports):
        return False
    _save_json(updated)
    return True


def filter_reports_by_status(status: schemas.ReportStatus) -> List[schemas.Report]:
    """Filter reports by status (pending, under_review, resolved, etc.)."""
    return [schemas.Report(**r) for r in _load_json() if r["status"] == status]


def get_summary() -> schemas.ReportSummary:
    """Compute counts of reports by status (for moderator dashboards)."""
    data = _load_json()
    total = len(data)
    return schemas.ReportSummary(
        total_reports=total,
        pending=sum(1 for r in data if r["status"] == schemas.ReportStatus.pending),
        under_review=sum(1 for r in data if r["status"] == schemas.ReportStatus.under_review),
        resolved=sum(1 for r in data if r["status"] == schemas.ReportStatus.resolved),
        dismissed=sum(1 for r in data if r["status"] == schemas.ReportStatus.dismissed),
    )
