"""
Handles report creation, retrieval, and moderation actions.
Routes are protected by role-based access (member/critic vs moderator/admin).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.reports import utils, schemas
from backend.authentication.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=schemas.Report)
def submit_report(report: schemas.ReportCreate, user=Depends(get_current_user)):
    """Submit a new report (accessible to member/critic)."""
    if user["role"] not in ["member", "critic"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return utils.create_report(
        reported_item=report.reported_item,
        type=report.type,
        reason=report.reason,
        reporter_id=user["user_id"],
    )


@router.get("/", response_model=List[schemas.Report])
def get_all_reports(user=Depends(get_current_user)):
    """Retrieve all reports (moderator/admin only)."""
    if user["role"] not in ["moderator", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return utils.load_reports()


@router.get("/{report_id}", response_model=schemas.Report)
def get_report(report_id: str, user=Depends(get_current_user)):
    """Retrieve a specific report (moderator/admin only)."""
    if user["role"] not in ["moderator", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    report = utils.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.patch("/{report_id}", response_model=schemas.Report)
def update_report(report_id: str, update: schemas.ReportUpdate, user=Depends(get_current_user)):
    """Update a report’s status (moderator/admin only)."""
    if user["role"] not in ["moderator", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    updated = utils.update_report_status(report_id, update.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Report not found.")
    return updated


@router.delete("/{report_id}")
def delete_report(report_id: str, user=Depends(get_current_user)):
    """Delete a report (admin only)."""
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    deleted = utils.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"message": f"Report {report_id} deleted."}
