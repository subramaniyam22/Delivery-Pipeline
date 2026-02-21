import logging
import signal
import subprocess
import threading
import time
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from app.db import SessionLocal
from app.jobs.queue import (
    claim_next_job,
    mark_failed,
    mark_needs_human,
    mark_running,
    mark_success,
)
from app.models import StageStatus, AdminConfig, AuditLog, JobRunStatus, JobRun, Project
from app.error_codes import ErrorCode
from app.services.workflow_runner import run_stage
from app.services.pipeline_orchestrator import on_job_success, on_job_failure
from app.services.job_queue import (
    JOB_TYPE_BLUEPRINT_GENERATE,
    claim_next_generic_job,
    extend_lease,
    mark_generic_job_failed,
    mark_generic_job_success,
    LEASE_SECONDS,
)
from app.services.blueprint_service import generate_blueprint as blueprint_generate

logger = logging.getLogger(__name__)

_should_stop = False
WORKER_HEARTBEAT_KEY = "worker:heartbeat:delivery-worker"
WORKER_HEARTBEAT_INTERVAL = 10


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
        "assignment": 5,
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


def _run_generic_job(job, db) -> bool:
    """Run an already-claimed generic job. Returns True."""
    job_id = job.id
    job_type = job.type
    payload = job.payload_json or {}
    logger.info("Generic job started", extra={"job_id": str(job_id), "type": job_type})
    try:
        if job_type == JOB_TYPE_BLUEPRINT_GENERATE:
            run_id = payload.get("run_id")
            template_id = payload.get("template_id")
            if not run_id or not template_id:
                mark_generic_job_failed(job_id, "Missing run_id or template_id in payload", db=db)
                return True
            blueprint_generate(UUID(template_id), UUID(run_id), db=db)
        else:
            mark_generic_job_failed(job_id, f"Unknown job type: {job_type}", db=db)
            return True
        mark_generic_job_success(job_id, db=db)
        logger.info("Generic job completed", extra={"job_id": str(job_id), "type": job_type})
    except Exception as e:
        logger.exception("Generic job failed: %s", e)
        mark_generic_job_failed(job_id, str(e), db=db)
    return True


SWEEPER_INTERVAL_SECONDS = 90  # Run autopilot sweeper every 90s
_last_sweeper_run = 0.0


def _run_autopilot_sweeper() -> None:
    """Periodic backstop: enqueue ready stages; apply onboarding reminders and HOLD."""
    global _last_sweeper_run
    now = time.time()
    if now - _last_sweeper_run < SWEEPER_INTERVAL_SECONDS:
        return
    _last_sweeper_run = now
    try:
        from app.services.pipeline_orchestrator import (
            run_autopilot_sweeper,
            run_onboarding_reminders_and_hold,
            run_onboarding_idle_nudge,
        )
        db = SessionLocal()
        try:
            run_onboarding_reminders_and_hold(db, max_projects=30)
            run_onboarding_idle_nudge(db, max_projects=20)
            run_autopilot_sweeper(db, max_projects=50)
        finally:
            db.close()
    except Exception as e:
        logger.warning("Autopilot sweeper failed: %s", e)


def _run_once(worker_id: str) -> bool:
    db = SessionLocal()
    try:
        _mark_stuck_jobs(db)
        _run_autopilot_sweeper()
        generic_job = claim_next_generic_job(worker_id, lease_seconds=LEASE_SECONDS, db=db)
        if generic_job:
            return _run_generic_job(generic_job, db)
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
                err_code = (result or {}).get("error_code") or ErrorCode.JOB_EXECUTION_ERROR.value
                payload = dict(result) if isinstance(result, dict) else {"error": str(result)}
                if "error_code" not in payload:
                    payload["error_code"] = err_code
                mark_failed(job.id, error_json=payload, retryable=True, db=db)
                try:
                    err_msg = str(result) if result else None
                    on_job_failure(db, job.project_id, job.stage, job.id, error_message=err_msg)
                except Exception as hook_err:
                    logger.warning("Pipeline on_job_failure hook failed: %s", hook_err)
            else:
                mark_success(job.id, db=db)
                try:
                    on_job_success(db, job.project_id, job.stage, job.id, result=result)
                except Exception as hook_err:
                    logger.warning("Pipeline on_job_success hook failed: %s", hook_err)
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
                error_json={"error_code": ErrorCode.TIMEOUT_STUCK_RUN.value, "error": "Job execution timed out"},
                retryable=False,
                db=db,
            )
            try:
                on_job_failure(db, job.project_id, job.stage, job.id, error_message="Job execution timed out")
            except Exception as hook_err:
                logger.warning("Pipeline on_job_failure hook failed: %s", hook_err)
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
            mark_failed(
                job.id,
                error_json={"error_code": ErrorCode.JOB_EXECUTION_ERROR.value, "error": str(exc)},
                retryable=True,
                db=db,
            )
            try:
                on_job_failure(db, job.project_id, job.stage, job.id, error_message=str(exc))
            except Exception as hook_err:
                logger.warning("Pipeline on_job_failure hook failed: %s", hook_err)
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
                error_json={"error_code": ErrorCode.TIMEOUT_STUCK_RUN.value, "error": "Job exceeded max runtime"},
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


def _log_worker_readiness() -> None:
    """Log node, lighthouse, chromium versions and Worker ready for local + Render debugging."""
    try:
        node_v = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=5)
        logger.info("node_version=%s", (node_v.stdout or node_v.stderr or "unknown").strip())
    except Exception as e:
        logger.info("node_version=not_available (%s)", e)
    try:
        lh_v = subprocess.run(["lighthouse", "--version"], capture_output=True, text=True, timeout=5)
        logger.info("lighthouse_version=%s", (lh_v.stdout or lh_v.stderr or "unknown").strip())
    except Exception as e:
        logger.info("lighthouse_version=not_available (%s)", e)
    try:
        import playwright
        logger.info("playwright_chromium=installed (playwright %s)", getattr(playwright, "__version__", "?"))
    except Exception as e:
        logger.info("playwright_chromium=not_available (%s)", e)


def _heartbeat_loop() -> None:
    """Write worker heartbeat to Redis every 10s for /health worker_ok."""
    while not _should_stop:
        try:
            from app.utils.cache import cache
            if cache.client:
                cache.client.set(WORKER_HEARTBEAT_KEY, str(time.time()), ex=90)
        except Exception as e:
            logger.debug("Worker heartbeat write failed: %s", e)
        for _ in range(WORKER_HEARTBEAT_INTERVAL):
            if _should_stop:
                break
            time.sleep(1)


def main(poll_interval_seconds: float = 2.0) -> None:
    worker_id = f"worker-{uuid.uuid4()}"
    logger.info("Worker started: %s", worker_id)
    _log_worker_readiness()

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    logger.info("Worker heartbeat thread started (key=%s)", WORKER_HEARTBEAT_KEY)

    db = SessionLocal()
    try:
        max_workers = max(1, _get_worker_concurrency(db))
        # Verify Redis (used by cache/jobs)
        try:
            from app.utils.cache import cache
            if cache.client:
                cache.client.ping()
        except Exception:
            pass
        logger.info("Worker ready (db+redis connected, max_parallel_jobs=%s)", max_workers)
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
