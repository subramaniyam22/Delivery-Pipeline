import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import JobRun, JobRunStatus, Stage
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent, EventType
import asyncio

logger = logging.getLogger(__name__)


def _get_db(db: Optional[Session]) -> Session:
    if db is not None:
        return db
    return SessionLocal()


def _broadcast_job_update(job: JobRun) -> None:
    if not job:
        return
    event = WebSocketEvent.create_event(
        EventType.NOTIFICATION,
        {
            "message": f"Job {job.id} {job.status.value.lower()}",
            "job_id": str(job.id),
            "status": job.status.value,
            "stage": job.stage.value,
            "project_id": str(job.project_id),
        },
        project_id=str(job.project_id),
    )
    try:
        asyncio.run(manager.notify_project_subscribers(str(job.project_id), event))
    except Exception:
        pass


def enqueue_job(
    project_id: UUID,
    stage: Stage,
    payload_json: Optional[Dict[str, Any]],
    request_id: Optional[str],
    actor_user_id: Optional[UUID],
    db: Optional[Session] = None,
    max_attempts: int = 3,
    correlation_id: Optional[UUID] = None,
    requested_by: Optional[str] = None,
    requested_by_user_id: Optional[UUID] = None,
) -> UUID:
    session = _get_db(db)
    close_session = db is None
    try:
        job = JobRun(
            project_id=project_id,
            stage=stage,
            status=JobRunStatus.QUEUED,
            attempts=0,
            max_attempts=max_attempts,
            payload_json=payload_json or {},
            error_json={},
            request_id=request_id,
            actor_user_id=actor_user_id,
            next_run_at=datetime.utcnow(),
            correlation_id=correlation_id,
            requested_by=requested_by,
            requested_by_user_id=requested_by_user_id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id
    finally:
        if close_session:
            session.close()


def claim_next_job(worker_id: str, db: Optional[Session] = None) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        now = datetime.utcnow()
        job = (
            session.query(JobRun)
            .filter(
                JobRun.status == JobRunStatus.QUEUED,
                JobRun.next_run_at <= now,
            )
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job:
            return None
        job.locked_by = worker_id
        job.locked_at = now
        session.commit()
        session.refresh(job)
        _broadcast_job_update(job)
        return job
    finally:
        if close_session:
            session.close()


def mark_running(job_id: UUID, db: Optional[Session] = None) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        job = session.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            return None
        job.status = JobRunStatus.RUNNING
        if not job.started_at:
            job.started_at = datetime.utcnow()
        job.attempts += 1
        session.commit()
        session.refresh(job)
        _broadcast_job_update(job)
        return job
    finally:
        if close_session:
            session.close()


def mark_success(job_id: UUID, db: Optional[Session] = None) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        job = session.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            return None
        job.status = JobRunStatus.SUCCESS
        job.finished_at = datetime.utcnow()
        job.locked_by = None
        job.locked_at = None
        session.commit()
        session.refresh(job)
        _broadcast_job_update(job)
        return job
    finally:
        if close_session:
            session.close()


def mark_failed(
    job_id: UUID,
    error_json: Optional[Dict[str, Any]],
    retryable: bool = True,
    db: Optional[Session] = None,
) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        job = session.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            return None
        job.error_json = error_json or {}
        job.locked_by = None
        job.locked_at = None
        now = datetime.utcnow()

        if retryable and job.attempts < job.max_attempts:
            delay_seconds = min(3600, (2 ** max(job.attempts - 1, 0)) * 30)
            job.status = JobRunStatus.QUEUED
            job.next_run_at = now + timedelta(seconds=delay_seconds)
        else:
            job.status = JobRunStatus.FAILED
            job.finished_at = now

        session.commit()
        session.refresh(job)
        _broadcast_job_update(job)
        return job
    finally:
        if close_session:
            session.close()


def mark_needs_human(
    job_id: UUID,
    report_json: Optional[Dict[str, Any]],
    db: Optional[Session] = None,
) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        job = session.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            return None
        job.status = JobRunStatus.NEEDS_HUMAN
        job.error_json = report_json or {}
        job.finished_at = datetime.utcnow()
        job.locked_by = None
        job.locked_at = None
        session.commit()
        session.refresh(job)
        _broadcast_job_update(job)
        return job
    finally:
        if close_session:
            session.close()


def cancel_job(job_id: UUID, db: Optional[Session] = None) -> Optional[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        job = session.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            return None
        job.status = JobRunStatus.CANCELED
        job.finished_at = datetime.utcnow()
        job.locked_by = None
        job.locked_at = None
        session.commit()
        session.refresh(job)
        return job
    finally:
        if close_session:
            session.close()


def list_jobs(project_id: UUID, db: Optional[Session] = None) -> List[JobRun]:
    session = _get_db(db)
    close_session = db is None
    try:
        return (
            session.query(JobRun)
            .filter(JobRun.project_id == project_id)
            .order_by(JobRun.created_at.desc())
            .all()
        )
    finally:
        if close_session:
            session.close()
