"""
Utility functions for loading, saving, and managing report data in JSON files.
"""

import os, json, uuid
from typing import List, Optional
from datetime import datetime
from backend.reports import schemas

REPORTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "reports", "reports.json")


def _load_json() -> List[dict]:
    if not os.path.exists(REPORTS_FILE):
        return []
    with open(REPORTS_FILE, "r") as f:
        return json.load(f)


def _save_json(data: List[dict]) -> None:
    os.makedirs(os.path.dirname(REPORTS_FILE), exist_ok=True)
    with open(REPORTS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_reports() -> List[schemas.Report]:
    """Return all reports as Pydantic models."""
    return [schemas.Report(**r) for r in _load_json()]


def save_reports(data: List[schemas.Report]) -> None:
    """Save list of Pydantic report models."""
    _save_json([r.dict() for r in data])


def create_report(reported_item: str, type: str, reason: str, reporter_id: str) -> schemas.Report:
    """Create and persist a new report."""
    reports = _load_json()
    new_report = schemas.Report(
        id=str(uuid.uuid4()),
        reported_item=reported_item,
        type=type,
        reason=reason,
        reporter_id=reporter_id,
        status=schemas.ReportStatus.pending,
        created_at=datetime.utcnow().isoformat(),
    )
    reports.append(new_report.dict())
    _save_json(reports)
    return new_report


def get_report(report_id: str) -> Optional[schemas.Report]:
    """Fetch specific report by ID."""
    for report in _load_json():
        if report["id"] == report_id:
            return schemas.Report(**report)
    return None


def update_report_status(report_id: str, status: schemas.ReportStatus) -> Optional[schemas.Report]:
    """Update the status (resolved/dismissed/pending) of a report."""
    reports = _load_json()
    for report in reports:
        if report["id"] == report_id:
            report["status"] = status
            _save_json(reports)
            return schemas.Report(**report)
    return None


def delete_report(report_id: str) -> bool:
    """Delete a report by ID."""
    reports = _load_json()
    updated = [r for r in reports if r["id"] != report_id]
    if len(updated) == len(reports):
        return False
    _save_json(updated)
    return True


def filter_reports_by_status(status: schemas.ReportStatus) -> List[schemas.Report]:
    """Filter reports by status (pending/resolved/dismissed)."""
    return [schemas.Report(**r) for r in _load_json() if r["status"] == status]
