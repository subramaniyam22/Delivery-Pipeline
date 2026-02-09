import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Stage, StageOutput, StageStatus, JobRun, JobRunStatus, AuditLog
from app.schemas import WorkflowAdvanceRequest, ApprovalRequest, SendBackRequest
from app.deps import get_current_active_user
from app.services import project_service
from app.rbac import check_full_access, require_admin_manager
from app.jobs.queue import enqueue_job
from app.services.project_service import record_stage_transition
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["workflow"])


@router.post("/{project_id}/advance", status_code=status.HTTP_202_ACCEPTED)
def advance_workflow(
    project_id: UUID,
    data: WorkflowAdvanceRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Advance workflow to next stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can advance workflow"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    request_id = x_request_id or str(uuid.uuid4())
    job_id = enqueue_job(
        project_id=project_id,
        stage=project.current_stage,
        payload_json={"notes": data.notes, "action": "advance"},
        request_id=request_id,
        actor_user_id=current_user.id,
        db=db,
    )
    return {"job_id": str(job_id), "request_id": request_id}


@router.post("/{project_id}/human/approve-build", status_code=status.HTTP_202_ACCEPTED)
def approve_build(
    project_id: UUID,
    data: ApprovalRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve build stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can approve build"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    if project.current_stage != Stage.BUILD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in BUILD stage"
        )

    request_id = x_request_id or str(uuid.uuid4())
    job_id = enqueue_job(
        project_id=project_id,
        stage=Stage.BUILD,
        payload_json={"notes": data.notes, "action": "approve_build"},
        request_id=request_id,
        actor_user_id=current_user.id,
        db=db,
    )
    return {"job_id": str(job_id), "request_id": request_id}


@router.post("/{project_id}/human/send-back", status_code=status.HTTP_202_ACCEPTED)
def send_back(
    project_id: UUID,
    data: Optional[SendBackRequest] = None,
    to_stage: Optional[Stage] = None,
    reason: Optional[str] = None,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send project back to a specific stage (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can send back stages"
        )

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    resolved_stage = to_stage or (data.target_stage if data else None)
    resolved_reason = reason or (data.reason if data else None)
    if not resolved_stage or not resolved_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_stage and reason are required"
        )

    request_id = x_request_id or str(uuid.uuid4())
    previous_stage = project.current_stage
    project.current_stage = resolved_stage
    record_stage_transition(
        project,
        previous_stage,
        project.current_stage,
        actor_user_id=str(current_user.id),
        request_id=request_id,
    )

    db.add(
        AuditLog(
            project_id=project.id,
            actor_user_id=current_user.id,
            action="HITL_SENT_BACK",
            payload_json={
                "from_stage": previous_stage.value,
                "to_stage": resolved_stage.value,
                "reason": resolved_reason,
                "request_id": request_id,
            },
        )
    )
    db.commit()

    enqueue_job(
        project_id=project.id,
        stage=resolved_stage,
        payload_json={"reason": resolved_reason, "action": "hitl_send_back"},
        request_id=request_id,
        actor_user_id=current_user.id,
        db=db,
    )

    return {"request_id": request_id}


@router.post("/{project_id}/human/approve", status_code=status.HTTP_202_ACCEPTED)
def approve_stage(
    project_id: UUID,
    stage: Stage,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    require_admin_manager(current_user)

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    output = (
        db.query(StageOutput)
        .filter(
            StageOutput.project_id == project_id,
            StageOutput.stage == stage,
            StageOutput.status == StageStatus.NEEDS_HUMAN,
        )
        .order_by(StageOutput.created_at.desc())
        .first()
    )
    if not output:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending HITL output found")

    request_id = x_request_id or str(uuid.uuid4())
    output.status = StageStatus.SUCCESS
    output.gate_decision = "APPROVED_HITL"

    job = None
    if output.job_run_id:
        job = db.query(JobRun).filter(JobRun.id == output.job_run_id).first()
        if job and job.status == JobRunStatus.NEEDS_HUMAN:
            job.status = JobRunStatus.SUCCESS
            job.finished_at = job.finished_at or output.created_at or None

    stage_order = [
        Stage.SALES,
        Stage.ONBOARDING,
        Stage.ASSIGNMENT,
        Stage.BUILD,
        Stage.TEST,
        Stage.DEFECT_VALIDATION,
        Stage.COMPLETE,
    ]
    next_stage = None
    if stage in stage_order and project.current_stage == stage:
        idx = stage_order.index(stage)
        if idx < len(stage_order) - 1:
            previous_stage = project.current_stage
            next_stage = stage_order[idx + 1]
            project.current_stage = next_stage
            record_stage_transition(
                project,
                previous_stage,
                project.current_stage,
                actor_user_id=str(current_user.id),
                request_id=request_id,
            )

    db.add(
        AuditLog(
            project_id=project.id,
            actor_user_id=current_user.id,
            action="HITL_APPROVED",
            payload_json={
                "stage": stage.value,
                "request_id": request_id,
            },
        )
    )
    db.commit()

    if next_stage:
        enqueue_job(
            project_id=project.id,
            stage=next_stage,
            payload_json={"triggered_by": stage.value, "action": "hitl_approved"},
            request_id=request_id,
            actor_user_id=current_user.id,
            db=db,
        )

    return {"job_id": str(output.job_run_id) if output.job_run_id else None, "request_id": request_id}


