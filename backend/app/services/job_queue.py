"""
Generic job queue: enqueue typed jobs with idempotency and leasing.
Jobs are executed by the worker loop (see jobs/worker.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Job

logger = logging.getLogger(__name__)

JOB_TYPE_BLUEPRINT_GENERATE = "template.blueprint.generate"
LEASE_SECONDS = 120
BACKOFF_BASE_SECONDS = 10
BACKOFF_MAX_SECONDS = 900  # 15 min
MAX_LAST_ERROR_LEN = 2000


def enqueue_job(
    type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    run_at: Optional[datetime] = None,
    max_attempts: int = 5,
    db: Optional[Session] = None,
) -> UUID:
    """
    Enqueue a job. Idempotent: if idempotency_key is set and a job with that key
    exists with status in (queued, running, retry), returns existing job id without inserting.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        if idempotency_key:
            existing = (
                session.query(Job)
                .filter(
                    Job.idempotency_key == idempotency_key,
                    Job.status.in_(["queued", "running", "retry"]),
                )
                .first()
            )
            if existing:
                logger.debug("Job idempotent skip: key=%s job_id=%s", idempotency_key, existing.id)
                return existing.id
        run_at = run_at or datetime.utcnow()
        job = Job(
            type=type,
            payload_json=payload or {},
            status="queued",
            attempts=0,
            max_attempts=max_attempts,
            run_at=run_at,
            idempotency_key=idempotency_key,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id
    finally:
        if close and session:
            session.close()


def backoff_seconds(attempts: int) -> int:
    """Min(2^attempts * 10s, 15min)."""
    sec = min((2 ** attempts) * BACKOFF_BASE_SECONDS, BACKOFF_MAX_SECONDS)
    return sec


def claim_next_generic_job(worker_id: str, lease_seconds: int = LEASE_SECONDS, db: Optional[Session] = None) -> Optional[Job]:
    """Claim one due job: status in (queued, retry), run_at <= now, lock_expires_at expired or null. SELECT FOR UPDATE SKIP LOCKED."""
    session = db or SessionLocal()
    close = db is None
    try:
        now = datetime.utcnow()
        job = (
            session.query(Job)
            .filter(
                Job.status.in_(["queued", "retry"]),
                Job.run_at <= now,
                (Job.lock_expires_at.is_(None)) | (Job.lock_expires_at < now),
            )
            .order_by(Job.run_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job:
            return None
        job.status = "running"
        job.locked_by = worker_id
        job.locked_at = now
        job.lock_expires_at = now + timedelta(seconds=lease_seconds)
        job.updated_at = now
        session.commit()
        session.refresh(job)
        return job
    finally:
        if close and session:
            session.close()


def extend_lease(job_id: UUID, lease_seconds: int, db: Optional[Session] = None) -> bool:
    """Extend lock_expires_at for heartbeat."""
    session = db or SessionLocal()
    close = db is None
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != "running":
            return False
        now = datetime.utcnow()
        job.lock_expires_at = now + timedelta(seconds=lease_seconds)
        job.updated_at = now
        session.commit()
        return True
    finally:
        if close and session:
            session.close()


def mark_generic_job_success(job_id: UUID, db: Optional[Session] = None) -> Optional[Job]:
    session = db or SessionLocal()
    close = db is None
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        job.status = "success"
        job.locked_by = None
        job.locked_at = None
        job.lock_expires_at = None
        job.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(job)
        return job
    finally:
        if close and session:
            session.close()


def mark_generic_job_failed(
    job_id: UUID,
    error_message: str,
    db: Optional[Session] = None,
) -> Optional[Job]:
    session = db or SessionLocal()
    close = db is None
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        now = datetime.utcnow()
        job.attempts += 1
        job.last_error = (error_message or "")[:MAX_LAST_ERROR_LEN]
        job.locked_by = None
        job.locked_at = None
        job.lock_expires_at = None
        job.updated_at = now
        if job.attempts >= job.max_attempts:
            job.status = "dead"
        else:
            job.status = "retry"
            job.run_at = now + timedelta(seconds=backoff_seconds(job.attempts))
        session.commit()
        session.refresh(job)
        return job
    finally:
        if close and session:
            session.close()
