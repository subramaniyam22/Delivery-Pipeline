from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role
from app.schemas import WorkflowAdvanceRequest, ApprovalRequest, SendBackRequest
from app.deps import get_current_active_user
from app.services import project_service
from app.rbac import check_full_access
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["workflow"])


@router.post("/{project_id}/advance")
def advance_workflow(
    project_id: UUID,
    data: WorkflowAdvanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Advance workflow to next stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can advance workflow"
        )
    
    result = project_service.advance_workflow(db, project_id, current_user, data.notes)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{project_id}/human/approve-build")
def approve_build(
    project_id: UUID,
    data: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve build stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can approve build"
        )
    
    result = project_service.approve_build(db, project_id, current_user, data.notes)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{project_id}/human/send-back")
def send_back(
    project_id: UUID,
    data: SendBackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send project back to previous stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can send back projects"
        )
    
    result = project_service.send_back(db, project_id, data.target_stage, data.reason, current_user)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result
