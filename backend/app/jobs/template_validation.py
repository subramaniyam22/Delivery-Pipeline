"""
Template validation pipeline: Lighthouse + axe + content checks, persist results, enforce gates.
Runs in background task.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AdminConfig, Project, TemplateRegistry, TemplateValidationJob
from app.jobs.template_blueprint import _blueprint_hash
from app.jobs.template_preview import run_template_preview_pipeline
from app.services.validation_fix import apply_color_contrast_fix, get_fix_actions
from app.services.validation_runner import (
    aggregate_results,
    run_axe,
    run_content_checks,
    run_lighthouse,
)

logger = logging.getLogger(__name__)

VALIDATION_JOBS_CONCURRENCY = int(os.getenv("VALIDATION_JOBS_CONCURRENCY", "2"))
_validation_semaphore = threading.Semaphore(VALIDATION_JOBS_CONCURRENCY)


def _resolve_thresholds(db: Session, project_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Global thresholds merged with project quality_overrides_json."""
    global_config = db.query(AdminConfig).filter(AdminConfig.key == "global_thresholds_json").first()
    global_thresholds = (global_config.value_json if global_config and isinstance(global_config.value_json, dict) else {}) or {}
    if project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and getattr(project, "quality_overrides_json", None) and isinstance(project.quality_overrides_json, dict):
            overrides = project.quality_overrides_json
            return {**global_thresholds, **overrides}
    return global_thresholds


def _validation_hash(blueprint_hash: Optional[str], preview_url: Optional[str], thresholds_json: str) -> str:
    return hashlib.sha256(
        f"{blueprint_hash or ''}|{preview_url or ''}|{thresholds_json}".encode()
    ).hexdigest()


def run_template_validation_pipeline(
    template_id: UUID,
    force: bool = False,
    project_id: Optional[UUID] = None,
    db: Optional[Session] = None,
    auto_fix_attempted: bool = False,
) -> Dict[str, Any]:
    """
    Load template, resolve thresholds, compute validation_hash.
    If validation_hash unchanged and status==passed and not force: skip.
    Set validation_status=running, run lighthouse + axe + content, aggregate, persist.
    """
    if not _validation_semaphore.acquire(blocking=True, timeout=60):
        return {"status": "failed", "error": "Validation job concurrency timeout"}
    session = db or SessionLocal()
    close = db is None
    try:
        template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            _validation_semaphore.release()
            return {"status": "failed", "error": "Template not found"}
        preview_url = getattr(template, "preview_url", None) or template.preview_url
        if not preview_url:
            template.validation_status = "failed"
            template.validation_results_json = (template.validation_results_json or {}) | {
                "error": "No preview URL. Generate preview first.",
                "run_at": datetime.utcnow().isoformat(),
            }
            session.commit()
            _validation_semaphore.release()
            return {"status": "failed", "error": "No preview URL"}
        thresholds = _resolve_thresholds(session, project_id)
        thresholds_str = json.dumps(thresholds, sort_keys=True)
        blueprint_hash = getattr(template, "blueprint_hash", None)
        new_hash = _validation_hash(blueprint_hash, preview_url, thresholds_str)
        if not force and getattr(template, "validation_hash", None) == new_hash and (getattr(template, "validation_status", None) or "") == "passed":
            _validation_semaphore.release()
            return {"status": "passed", "skipped": True, "validation_hash": new_hash}
        template.validation_status = "running"
        session.commit()
        timeouts = thresholds.get("timeouts") or {}
        lh = run_lighthouse(preview_url, timeouts)
        axe = run_axe(preview_url, timeouts)
        content = run_content_checks(preview_url)
        summary = aggregate_results(lh, axe, content, thresholds)
        passed = summary.get("passed", False)
        template.validation_results_json = summary
        template.validation_status = "passed" if passed else "failed"
        template.validation_last_run_at = datetime.utcnow()
        template.validation_hash = new_hash
        if passed:
            template.status = "validated"
        if not passed and summary.get("failed_reasons"):
            template.preview_error = "; ".join(summary["failed_reasons"][:5])
        else:
            template.preview_error = None
        session.commit()

        # Auto-fix: on first failure, apply color-contrast fix if applicable and re-run once.
        if not passed and not auto_fix_attempted:
            fix_actions = get_fix_actions(summary)
            color_contrast = next(
                (a for a in fix_actions if a.get("type") == "color_contrast" and a.get("applicable")),
                None,
            )
            blueprint = getattr(template, "blueprint_json", None)
            if color_contrast and isinstance(blueprint, dict) and blueprint:
                try:
                    fixed = apply_color_contrast_fix(blueprint)
                    template.blueprint_json = fixed
                    template.blueprint_hash = _blueprint_hash(fixed)
                    session.commit()
                    _validation_semaphore.release()
                    run_template_preview_pipeline(template_id, db=session)
                    return run_template_validation_pipeline(
                        template_id,
                        force=True,
                        project_id=project_id,
                        db=session,
                        auto_fix_attempted=True,
                    )
                except Exception as fix_err:
                    logger.warning("Auto-fix (color-contrast) failed, returning original result: %s", fix_err)

        _validation_semaphore.release()
        return {"status": "passed" if passed else "failed", "passed": passed, "validation_hash": new_hash, "failed_reasons": summary.get("failed_reasons", [])}
    except Exception as e:
        logger.exception("Template validation pipeline failed: %s", e)
        try:
            _validation_semaphore.release()
        except Exception:
            pass
        if session:
            try:
                template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
                if template:
                    template.validation_status = "failed"
                    template.validation_last_run_at = datetime.utcnow()
                    err_msg = str(e)
                    template.preview_error = err_msg
                    template.validation_results_json = (template.validation_results_json or {}) | {"error": err_msg, "run_at": datetime.utcnow().isoformat()}
                    session.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}
    finally:
        if close and session:
            session.close()


def run_validation_job(job_id: UUID) -> None:
    """Load TemplateValidationJob, run pipeline, update job and template."""
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(TemplateValidationJob).filter(TemplateValidationJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        payload = job.payload_json or {}
        result = run_template_validation_pipeline(
            template_id=job.template_id,
            force=payload.get("force", False),
            project_id=payload.get("project_id") and UUID(str(payload["project_id"])),
            db=db,
        )
        job.finished_at = datetime.utcnow()
        job.result_json = result
        job.status = "success" if result.get("status") == "passed" else "failed"
        if result.get("error"):
            job.error_text = result.get("error")
        db.commit()
    except Exception as e:
        logger.exception("run_validation_job failed: %s", e)
        try:
            job = db.query(TemplateValidationJob).filter(TemplateValidationJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_text = str(e)
                job.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
