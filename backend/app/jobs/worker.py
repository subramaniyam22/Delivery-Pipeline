import logging
import signal
import time
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from app.db import SessionLocal
from app.jobs.queue import (
    claim_next_job,
    mark_failed,
    mark_needs_human,
    mark_running,
    mark_success,
)
from app.models import StageStatus, AdminConfig, AuditLog, JobRunStatus, JobRun, Project
from app.services.workflow_runner import run_stage

logger = logging.getLogger(__name__)

_should_stop = False


def _get_worker_concurrency(db) -> int:
    config = db.query(AdminConfig).filter(AdminConfig.key == "worker_concurrency_json").first()
    if config and isinstance(config.value_json, dict):
        try:
            return int(config.value_json.get("max_parallel_jobs", 1))
        except Exception:
            return 1
    return 1


def _get_stage_timeout_minutes(db, stage) -> int:
    config = db.query(AdminConfig).filter(AdminConfig.key == "global_thresholds_json").first()
    if config and isinstance(config.value_json, dict):
        timeouts = config.value_json.get("stage_timeouts_minutes") or {}
        value = timeouts.get(stage.value.lower())
        if value:
            try:
                return int(value)
            except Exception:
                return 30
    defaults = {
        "build": 30,
        "test": 15,
        "defect_validation": 10,
        "complete": 5,
    }
    return defaults.get(stage.value.lower(), 30)


def _resolve_actor_user_id(db, job: JobRun):
    if job.actor_user_id:
        return job.actor_user_id
    project = db.query(Project).filter(Project.id == job.project_id).first()
    if project:
        return project.created_by_user_id
    return None


def _handle_shutdown(signum, frame) -> None:
    global _should_stop
    _should_stop = True
    logger.info("Worker shutdown signal received")


def _run_once(worker_id: str) -> bool:
    db = SessionLocal()
    try:
        _mark_stuck_jobs(db)
        job = claim_next_job(worker_id, db=db)
        if not job:
            return False

        mark_running(job.id, db=db)
        actor_id = _resolve_actor_user_id(db, job)
        logger.info(
            "Job started",
            extra={
                "job_id": str(job.id),
                "project_id": str(job.project_id),
                "stage": job.stage.value,
                "request_id": job.request_id,
            },
        )
        if actor_id:
            db.add(
                AuditLog(
                    project_id=job.project_id,
                    actor_user_id=actor_id,
                    action="WORKER_STAGE_STARTED",
                    payload_json={
                        "job_id": str(job.id),
                        "stage": job.stage.value,
                        "request_id": job.request_id,
                    },
                )
            )
            db.commit()
        try:
            timeout_minutes = _get_stage_timeout_minutes(db, job.stage)
            timeout_seconds = max(60, timeout_minutes * 60)
            start_ts = time.time()
            result = run_stage(
                db=db,
                project_id=job.project_id,
                stage=job.stage,
                job_id=job.id,
                request_id=job.request_id,
                payload=job.payload_json,
            )
            duration = time.time() - start_ts
            if duration > timeout_seconds:
                raise TimeoutError("Job execution timed out")
            status = result.get("status")
            if status == StageStatus.NEEDS_HUMAN:
                mark_needs_human(job.id, report_json=result, db=db)
            elif status == StageStatus.FAILED:
                mark_failed(job.id, error_json=result, retryable=True, db=db)
            else:
                mark_success(job.id, db=db)
            logger.info(
                "Job completed",
                extra={
                    "job_id": str(job.id),
                    "project_id": str(job.project_id),
                    "stage": job.stage.value,
                    "request_id": job.request_id,
                    "status": str(status),
                },
            )
            if actor_id:
                db.add(
                    AuditLog(
                        project_id=job.project_id,
                        actor_user_id=actor_id,
                        action="WORKER_STAGE_FINISHED",
                        payload_json={
                            "job_id": str(job.id),
                            "stage": job.stage.value,
                            "status": str(status),
                            "request_id": job.request_id,
                        },
                    )
                )
                db.commit()
        except TimeoutError as exc:
            logger.error("Job timed out: %s", exc)
            mark_failed(
                job.id,
                error_json={"error": "Job execution timed out"},
                retryable=False,
                db=db,
            )
            if actor_id:
                db.add(
                    AuditLog(
                        project_id=job.project_id,
                        actor_user_id=actor_id,
                        action="WORKER_STAGE_TIMEOUT",
                        payload_json={
                            "job_id": str(job.id),
                            "stage": job.stage.value,
                            "request_id": job.request_id,
                        },
                    )
                )
                db.commit()
        except Exception as exc:
            logger.exception("Job execution failed")
            mark_failed(job.id, error_json={"error": str(exc)}, retryable=True, db=db)
        return True
    finally:
        db.close()


def _mark_stuck_jobs(db):
    now = time.time()
    jobs = (
        db.query(JobRun)
        .filter(JobRun.status == JobRunStatus.RUNNING, JobRun.started_at.isnot(None))
        .all()
    )
    for job in jobs:
        actor_id = _resolve_actor_user_id(db, job)
        timeout_minutes = _get_stage_timeout_minutes(db, job.stage)
        timeout_seconds = max(60, timeout_minutes * 60)
        if job.started_at and (now - job.started_at.timestamp()) > timeout_seconds:
            mark_failed(
                job.id,
                error_json={"error": "Job exceeded max runtime"},
                retryable=False,
                db=db,
            )
            if actor_id:
                db.add(
                    AuditLog(
                        project_id=job.project_id,
                        actor_user_id=actor_id,
                        action="WORKER_STAGE_TIMEOUT",
                        payload_json={
                            "job_id": str(job.id),
                            "stage": job.stage.value,
                            "request_id": job.request_id,
                        },
                    )
                )
    db.commit()


def main(poll_interval_seconds: float = 2.0) -> None:
    worker_id = f"worker-{uuid.uuid4()}"
    logger.info("Worker started: %s", worker_id)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    db = SessionLocal()
    try:
        max_workers = max(1, _get_worker_concurrency(db))
    finally:
        db.close()

    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = set()
    while not _should_stop:
        futures = {f for f in futures if not f.done()}
        if len(futures) < max_workers:
            futures.add(executor.submit(_run_once, worker_id))
        time.sleep(poll_interval_seconds)

    logger.info("Worker stopped: %s", worker_id)


if __name__ == "__main__":
    main()
