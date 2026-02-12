"""
Template blueprint pipeline: generate -> critique -> refine loop (runs in worker).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.templates.generator import generate_blueprint
from app.agents.templates.critic import critique_blueprint
from app.agents.templates.refiner import refine_blueprint
from app.db import SessionLocal
from app.models import TemplateBlueprintJob, TemplateRegistry
from app.templates.blueprint_schema_v1 import validate_blueprint_v1
from app.templates.quality_rubric import DEFAULT_THRESHOLDS, run_hard_checks

logger = logging.getLogger(__name__)

# Circuit breaker: abort if generator fails this many times
GENERATOR_FAILURE_LIMIT = 2


def _blueprint_hash(blueprint_json: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(blueprint_json, sort_keys=True).encode()).hexdigest()


def _meets_thresholds(scorecard: Dict[str, int], hard_checks: Dict[str, bool]) -> bool:
    thresholds = DEFAULT_THRESHOLDS
    for key, min_val in thresholds.items():
        if scorecard.get(key, 0) < min_val:
            return False
    return all(hard_checks.values())


def run_template_blueprint_pipeline(
    template_id: UUID,
    max_iterations: int = 3,
    regenerate: bool = False,
    db: Session | None = None,
) -> Dict[str, Any]:
    """
    Load template, generate or load blueprint, iterate critique->refine until pass or max_iterations.
    Persist blueprint_json, blueprint_quality_json, prompt_log_json, blueprint_hash, status.
    Returns result dict with status, iterations, error if any.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            return {"status": "failed", "error": "Template not found"}
        from app.config import settings
        if not getattr(settings, "OPENAI_API_KEY", None):
            return {"status": "failed", "error": "OpenAI API key not set. Set OPENAI_API_KEY."}
        job = (
            session.query(TemplateBlueprintJob)
            .filter(TemplateBlueprintJob.template_id == template_id, TemplateBlueprintJob.status == "running")
            .first()
        )
        if job:
            job.status = "failed"
            job.error_text = "Aborted (duplicate run)"
            job.finished_at = datetime.utcnow()
            session.commit()
        generator_failures = 0
        blueprint = None
        if regenerate or not getattr(template, "blueprint_json", None):
            demo_context = {"category": template.category or "general", "style": template.style or "modern"}
            try:
                blueprint = generate_blueprint(template, demo_context)
            except Exception as e:
                generator_failures += 1
                logger.exception("Generator failed: %s", e)
                return {"status": "failed", "error": str(e), "generator_failures": 1}
        else:
            blueprint = template.blueprint_json
        if not blueprint:
            return {"status": "failed", "error": "No blueprint"}
        last_hash = _blueprint_hash(blueprint)
        prompt_log = list(getattr(template, "prompt_log_json", None) or [])
        for i in range(max_iterations):
            critic_result = critique_blueprint(blueprint)
            scorecard = critic_result.get("scorecard") or {}
            hard_checks = critic_result.get("hard_checks") or {}
            issues = critic_result.get("issues") or []
            prompt_log.append({
                "iteration": i + 1,
                "event": "critique",
                "model": "gpt-4",
                "summary": (critic_result.get("summary") or "")[:500],
            })
            if _meets_thresholds(scorecard, hard_checks):
                break
            refined = refine_blueprint(blueprint, issues)
            if not refined:
                prompt_log.append({"iteration": i + 1, "event": "refine_failed"})
                break
            new_hash = _blueprint_hash(refined)
            if new_hash == last_hash:
                prompt_log.append({"iteration": i + 1, "event": "stuck", "message": "Blueprint unchanged after refine"})
                break
            last_hash = new_hash
            blueprint = refined
            valid, errs = validate_blueprint_v1(blueprint)
            if not valid:
                prompt_log.append({"iteration": i + 1, "event": "schema_errors", "errors": errs[:5]})
        critic_final = critique_blueprint(blueprint)
        scorecard_final = critic_final.get("scorecard") or {}
        hard_final = critic_final.get("hard_checks") or {}
        passed = _meets_thresholds(scorecard_final, hard_final)
        template.blueprint_json = blueprint
        template.blueprint_schema_version = 1
        template.blueprint_hash = _blueprint_hash(blueprint)
        template.blueprint_quality_json = {
            "iterations": max_iterations,
            "scorecard": scorecard_final,
            "hard_checks": hard_final,
            "issues": critic_final.get("issues") or [],
            "status": "pass" if passed else "fail",
            "thresholds": DEFAULT_THRESHOLDS,
        }
        template.prompt_log_json = prompt_log[-20:]
        if passed:
            template.status = "validated"
        else:
            template.status = getattr(template, "status", None) or "draft"
        template.validation_status = "not_run"
        template.validation_hash = None
        session.commit()
        return {
            "status": "success" if passed else "fail",
            "iterations": max_iterations,
            "scorecard": scorecard_final,
            "hard_checks": hard_final,
            "passed": passed,
        }
    except Exception as e:
        logger.exception("Blueprint pipeline failed: %s", e)
        if session:
            template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
            if template:
                template.blueprint_quality_json = (template.blueprint_quality_json or {}) | {"status": "fail", "error": str(e)}
                session.commit()
        return {"status": "failed", "error": str(e)}
    finally:
        if close and session:
            session.close()


def run_blueprint_job(job_id: UUID) -> None:
    """Called from background task: load job, run pipeline, update job and template."""
    db = SessionLocal()
    try:
        job = db.query(TemplateBlueprintJob).filter(TemplateBlueprintJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        payload = job.payload_json or {}
        result = run_template_blueprint_pipeline(
            template_id=job.template_id,
            max_iterations=payload.get("max_iterations", 3),
            regenerate=payload.get("regenerate", False),
            db=db,
        )
        job.finished_at = datetime.utcnow()
        job.result_json = result
        job.status = "success" if result.get("status") in ("success", "pass") else "failed"
        if result.get("error"):
            job.error_text = result.get("error")
        db.commit()
    except Exception as e:
        logger.exception("run_blueprint_job failed: %s", e)
        try:
            job = db.query(TemplateBlueprintJob).filter(TemplateBlueprintJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_text = str(e)
                job.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
