"""
Handles report creation, retrieval, and moderation actions.
Routes are protected by role-based access (member/critic vs moderator/admin).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.reports import utils, schemas
from backend.authentication.security import get_current_user
from backend.penalties import utils as penalty_utils

router = APIRouter(prefix="/reports", tags=["Reports"])

# --- MODERATOR/ADMIN: Summary endpoint ---
@router.get("/summary", response_model=schemas.ReportSummary)
def get_summary(user=Depends(get_current_user)):
    """Retrieve a summary of report statuses for dashboard analytics."""
    if user.role not in ["moderator", "administrator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return utils.get_summary()

# --- MEMBER/CRITIC: Submit report ---
@router.post("/", response_model=schemas.Report)
def submit_report(
    report: schemas.ReportCreate,
    user=Depends(get_current_user)
):
    """
    Submit a new report (accessible to member/critic).
    Restricted by penalties:
    - report_ban
    - posting_ban
    - suspension
    """
    # 🔒 Check for penalties
    restriction = penalty_utils.check_active_penalty(
        user.user_id,
        ["report_ban", "posting_ban", "suspension"]
    )
    if restriction:
        raise HTTPException(status_code=403, detail=restriction)

    # Role-based access
    if user.role not in ["member", "critic"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    # Proceed with report creation
    return utils.create_report(
        reporter_id=user.user_id,
        reported_id=report.reported_id,
        type=report.type,
        reason=report.reason,
    )


# --- MODERATOR/ADMIN: View all reports ---
@router.get("/", response_model=List[schemas.Report])
def get_all_reports(user=Depends(get_current_user)):
    """Retrieve all reports (moderator/admin only)."""
    if user.role not in ["moderator", "administrator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    return utils.load_reports()


# --- MODERATOR/ADMIN: View single report ---
@router.get("/{report_id}", response_model=schemas.Report)
def get_report(report_id: str, user=Depends(get_current_user)):
    """Retrieve a specific report (moderator/admin only)."""
    if user.role not in ["moderator", "administrator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    report = utils.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


# --- MODERATOR/ADMIN: Update report status ---
@router.patch("/{report_id}", response_model=schemas.Report)
def update_report(report_id: str, update: schemas.ReportUpdate, user=Depends(get_current_user)):
    """Update a report’s status and moderator notes."""
    if user.role not in ["moderator", "administrator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    updated = utils.update_report_status(report_id, update, moderator_id=user.user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Report not found.")
    return updated


# --- ADMIN: Delete report ---
@router.delete("/{report_id}")
def delete_report(report_id: str, user=Depends(get_current_user)):
    """Delete a report (admin only)."""
    if user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")
    deleted = utils.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"message": f"Report {report_id} deleted."}





