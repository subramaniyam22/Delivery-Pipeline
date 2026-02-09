import uuid
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user
from app.jobs.queue import enqueue_job, list_jobs
from app.models import JobRun, Project, Role, Stage, User, AdminConfig, AuditLog, JobRunStatus
from app.schemas import JobEnqueueRequest, JobRunResponse
from datetime import datetime

router = APIRouter(tags=["jobs"])


def _can_enqueue_stage(role: Role, stage: Stage) -> bool:
    if role in [Role.ADMIN, Role.MANAGER]:
        return True
    allowed = {
        Role.BUILDER: [Stage.BUILD],
        Role.TESTER: [Stage.TEST],
        Role.PC: [Stage.ASSIGNMENT],
        Role.CONSULTANT: [Stage.ONBOARDING],
        Role.SALES: [Stage.SALES],
    }
    return stage in allowed.get(role, [])


@router.post(
    "/projects/{project_id}/stages/{stage}/enqueue",
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_stage_job(
    project_id: UUID,
    stage: Stage,
    data: JobEnqueueRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _can_enqueue_stage(current_user.role, stage):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to enqueue this stage",
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    request_id = x_request_id or str(uuid.uuid4())
    job_id = enqueue_job(
        project_id=project_id,
        stage=stage,
        payload_json=data.payload_json,
        request_id=request_id,
        actor_user_id=current_user.id,
        db=db,
    )
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=current_user.id,
            action="JOB_ENQUEUED",
            payload_json={"job_id": str(job_id), "stage": stage.value, "request_id": request_id},
        )
    )
    db.commit()
    return {"job_id": str(job_id), "request_id": request_id}


@router.get("/jobs/{job_id}", response_model=JobRunResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/projects/{project_id}/jobs", response_model=List[JobRunResponse])
def get_project_jobs(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return list_jobs(project_id, db=db)


def _require_admin_manager(user: User) -> None:
    if user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Admin or Manager can access job operations")


def _stage_timeout_minutes(db: Session, stage: Stage) -> int:
    config = db.query(AdminConfig).filter(AdminConfig.key == "global_thresholds_json").first()
    if config and isinstance(config.value_json, dict):
        timeouts = config.value_json.get("stage_timeouts_minutes") or {}
        try:
            return int(timeouts.get(stage.value.lower(), 30))
        except Exception:
            return 30
    return 30


@router.get("/admin/jobs", response_model=List[JobRunResponse])
def admin_list_jobs(
    status_filter: Optional[JobRunStatus] = None,
    stage: Optional[Stage] = None,
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    query = db.query(JobRun)
    if status_filter:
        query = query.filter(JobRun.status == status_filter)
    if stage:
        query = query.filter(JobRun.stage == stage)
    if project_id:
        query = query.filter(JobRun.project_id == project_id)
    return query.order_by(JobRun.created_at.desc()).limit(200).all()


@router.get("/admin/jobs/stuck", response_model=List[JobRunResponse])
def admin_list_stuck_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    now = datetime.utcnow()
    running = db.query(JobRun).filter(JobRun.status == JobRunStatus.RUNNING, JobRun.started_at.isnot(None)).all()
    stuck = []
    for job in running:
        timeout_minutes = _stage_timeout_minutes(db, job.stage)
        if job.started_at and (now - job.started_at).total_seconds() > timeout_minutes * 60:
            stuck.append(job)
    return stuck


@router.post("/admin/jobs/{job_id}/retry", response_model=JobRunResponse)
def admin_retry_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobRunStatus.QUEUED
    job.next_run_at = datetime.utcnow()
    job.locked_by = None
    job.locked_at = None
    job.error_json = {"retry_requested_by": str(current_user.id)}
    db.add(
        AuditLog(
            project_id=job.project_id,
            actor_user_id=current_user.id,
            action="JOB_RETRY_REQUESTED",
            payload_json={"job_id": str(job_id), "stage": job.stage.value},
        )
    )
    db.commit()
    db.refresh(job)
    return job


@router.post("/admin/jobs/{job_id}/cancel", response_model=JobRunResponse)
def admin_cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobRunStatus.CANCELED
    job.finished_at = datetime.utcnow()
    job.locked_by = None
    job.locked_at = None
    db.add(
        AuditLog(
            project_id=job.project_id,
            actor_user_id=current_user.id,
            action="JOB_CANCELED",
            payload_json={"job_id": str(job_id), "stage": job.stage.value},
        )
    )
    db.commit()
    db.refresh(job)
    return job
