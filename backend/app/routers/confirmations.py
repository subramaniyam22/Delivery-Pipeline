"""Confirmation requests: list, decide, approve, reject (client token or admin)."""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.deps import get_current_active_user, get_current_user_optional
from app.models import ConfirmationRequest, OnboardingData, User
from app.rbac import require_admin_manager
from app.schemas import ConfirmationDecideRequest, ConfirmationRequestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["confirmations"])

# Flat routes: POST /confirmations/{id}/approve and POST /confirmations/{id}/reject
router_flat = APIRouter(prefix="/confirmations", tags=["confirmations"])


class ConfirmationRequestCreate(BaseModel):
    type: str = Field(..., description="fallback_template | substitute_artifact | other")
    title: str
    description: Optional[str] = None
    metadata_json: Optional[dict] = None


@router.post("/{project_id}/confirmations", response_model=ConfirmationRequestResponse, status_code=status.HTTP_201_CREATED)
def create_confirmation(
    project_id: UUID,
    body: ConfirmationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a confirmation request (Admin/Manager). Used when fallback template or substitute artifact is needed."""
    require_admin_manager(current_user)
    from app.models import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    cr = ConfirmationRequest(
        project_id=project_id,
        type=body.type,
        title=body.title,
        description=body.description,
        status="pending",
        metadata_json=body.metadata_json or {},
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)
    from app.config import settings
    from app.services.email_service import send_confirmation_request_email
    to_emails = []
    if getattr(project, "client_emails", None) and isinstance(project.client_emails, list):
        to_emails = [e for e in project.client_emails if isinstance(e, str) and e.strip()]
    if not to_emails and getattr(project, "client_email_ids", None):
        to_emails = [e.strip() for e in str(project.client_email_ids).split(",") if e.strip()]
    if to_emails:
        portal_url = (settings.FRONTEND_URL or "").rstrip("/")
        onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if onboarding and getattr(onboarding, "client_access_token", None):
            portal_url = f"{portal_url}/client-onboarding/{onboarding.client_access_token}"
        try:
            send_confirmation_request_email(to_emails, project.title or "Project", cr.title, portal_url)
        except Exception:
            pass
    return cr


def _allow_access(db: Session, project_id: UUID, current_user: Optional[User], client_token: Optional[str]) -> None:
    """Raises 401/403 if neither JWT (admin/manager) nor valid client_token for this project."""
    if client_token:
        onboarding = db.query(OnboardingData).filter(
            OnboardingData.client_access_token == client_token,
            OnboardingData.project_id == project_id,
        ).first()
        if onboarding:
            return
    if current_user:
        require_admin_manager(current_user)
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required (Bearer or client_token)")


@router.get("/{project_id}/confirmations", response_model=list[ConfirmationRequestResponse])
def list_confirmations(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_token: Optional[str] = Query(None, alias="client_token"),
):
    """List confirmation requests for a project. Use JWT (admin/manager) or client_token (client portal)."""
    _allow_access(db, project_id, current_user, client_token)
    requests = (
        db.query(ConfirmationRequest)
        .filter(ConfirmationRequest.project_id == project_id)
        .order_by(ConfirmationRequest.requested_at.desc())
        .all()
    )
    return list(requests)


@router.post("/{project_id}/confirmations/{confirmation_id}/decide", response_model=ConfirmationRequestResponse)
def decide_confirmation(
    project_id: UUID,
    confirmation_id: UUID,
    body: ConfirmationDecideRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_token: Optional[str] = Query(None, alias="client_token"),
):
    """Approve or reject a confirmation request (comment required). Client token or admin."""
    _allow_access(db, project_id, current_user, client_token)
    decided_by = current_user.id if current_user else None

    cr = (
        db.query(ConfirmationRequest)
        .filter(
            ConfirmationRequest.id == confirmation_id,
            ConfirmationRequest.project_id == project_id,
        )
        .first()
    )
    if not cr:
        raise HTTPException(status_code=404, detail="Confirmation request not found")
    if cr.status != "pending":
        raise HTTPException(status_code=400, detail="Already decided")
    cr.status = "approved" if body.approve else "rejected"
    cr.decided_at = datetime.utcnow()
    cr.decided_by = decided_by
    cr.decision_comment = body.comment
    db.commit()
    db.refresh(cr)
    logger.info(
        "confirmation_decision project_id=%s confirmation_id=%s decision=%s",
        str(project_id),
        str(confirmation_id),
        cr.status,
        extra={"project_id": str(project_id), "confirmation_id": str(confirmation_id), "decision": cr.status},
    )
    return cr


class ApproveRejectBody(BaseModel):
    comment: str = Field(..., min_length=1, description="Required when approving or rejecting")


def _decide_by_id(confirmation_id: UUID, approve: bool, body: ApproveRejectBody, db: Session, current_user: Optional[User], client_token: Optional[str]) -> ConfirmationRequest:
    """Resolve confirmation by id, check access via project, then set status."""
    cr = db.query(ConfirmationRequest).filter(ConfirmationRequest.id == confirmation_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Confirmation request not found")
    _allow_access(db, cr.project_id, current_user, client_token)
    if cr.status != "pending":
        raise HTTPException(status_code=400, detail="Already decided")
    decided_by = current_user.id if current_user else None
    cr.status = "approved" if approve else "rejected"
    cr.decided_at = datetime.utcnow()
    cr.decided_by = decided_by
    cr.decision_comment = body.comment
    db.commit()
    db.refresh(cr)
    logger.info(
        "confirmation_decision confirmation_id=%s decision=%s",
        str(confirmation_id),
        cr.status,
        extra={"confirmation_id": str(confirmation_id), "decision": cr.status},
    )
    return cr


@router_flat.post("/{confirmation_id}/approve", response_model=ConfirmationRequestResponse)
def approve_confirmation(
    confirmation_id: UUID,
    body: ApproveRejectBody,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_token: Optional[str] = Query(None, alias="client_token"),
):
    """Approve a confirmation request (client token or admin)."""
    return _decide_by_id(confirmation_id, True, body, db, current_user, client_token)


@router_flat.post("/{confirmation_id}/reject", response_model=ConfirmationRequestResponse)
def reject_confirmation(
    confirmation_id: UUID,
    body: ApproveRejectBody,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    client_token: Optional[str] = Query(None, alias="client_token"),
):
    """Reject a confirmation request (client token or admin)."""
    return _decide_by_id(confirmation_id, False, body, db, current_user, client_token)
