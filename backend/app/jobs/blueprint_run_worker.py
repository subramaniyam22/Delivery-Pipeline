"""
Blueprint run worker: process a single TemplateBlueprintRun (generate -> parse -> validate -> optional repair).
Updates run status, stores raw_output (redacted), error_* on failure; updates template on success.
"""
from __future__ import annotations

import json
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.templates.generator import _extract_json
from app.agents.templates.prompts import GENERATOR_SYSTEM, GENERATOR_USER, REPAIR_VALIDATION_SYSTEM, REPAIR_VALIDATION_USER
from app.agents.prompts import get_llm
from app.config import settings
from app.db import SessionLocal
from app.models import TemplateBlueprintRun, TemplateRegistry
from app.templates.blueprint_schema_v1 import validate_blueprint_v1
from app.utils.llm import invoke_llm
from app.utils.redact import redact_secrets

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
RETRYABLE_ERROR_CODES = ("OPENAI_ERROR", "PARSE_ERROR")


def _model_for_attempt(attempt: int) -> str:
    if attempt == 2 and getattr(settings, "OPENAI_MODEL_FALLBACK", None):
        return settings.OPENAI_MODEL_FALLBACK
    return settings.OPENAI_MODEL


def _generate_raw(template: TemplateRegistry, demo_context: Dict[str, Any], model_override: str | None) -> Tuple[str, str]:
    """Call LLM for blueprint JSON. Returns (raw_content, model_used)."""
    name = template.name or "Untitled"
    category = template.category or "general"
    style = template.style or "modern"
    tags = list(template.feature_tags_json or []) if hasattr(template, "feature_tags_json") else []
    required = list(template.required_inputs_json or []) if hasattr(template, "required_inputs_json") else []
    demo_str = json.dumps(demo_context or {}, default=str)
    user_prompt = GENERATOR_USER.format(
        name=name,
        category=category,
        style=style,
        tags=json.dumps(tags),
        required_inputs=json.dumps(required),
        demo_context=demo_str,
    )
    # get_llm uses settings.OPENAI_MODEL; we need to override for fallback. Create LLM with model_override if set.
    if model_override:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model_override,
            temperature=settings.OPENAI_TEMPERATURE,
            request_timeout=settings.OPENAI_TIMEOUT_SECONDS,
            model_kwargs={"max_tokens": settings.OPENAI_MAX_TOKENS} if settings.OPENAI_MAX_TOKENS else {},
        )
    else:
        llm = get_llm(task="analysis")
    response = invoke_llm(llm, GENERATOR_SYSTEM + "\n\n" + user_prompt)
    content = getattr(response, "content", response) if response else ""
    raw = content if isinstance(content, str) else ""
    model_used = model_override or settings.OPENAI_MODEL
    return raw, model_used


def _repair_once(raw_output: str, errors: list) -> str | None:
    """One repair LLM call. Returns new raw string or None."""
    from app.agents.templates.prompts import REPAIR_VALIDATION_SYSTEM, REPAIR_VALIDATION_USER
    errors_str = "\n".join(errors[:30]) if isinstance(errors, list) else str(errors)[:2000]
    raw_truncated = (raw_output or "")[:15000]
    prompt = REPAIR_VALIDATION_SYSTEM + "\n\n" + REPAIR_VALIDATION_USER.format(errors=errors_str, raw_output=raw_truncated)
    llm = get_llm(task="analysis")
    try:
        response = invoke_llm(llm, prompt)
        content = getattr(response, "content", response) if response else ""
        return content if isinstance(content, str) else None
    except Exception:
        return None


def _parse_and_validate(raw: str, run: TemplateBlueprintRun, db: Session) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Parse raw string to JSON and validate. Returns (blueprint_dict, None) on success,
    or (None, error_code) on failure. Run is updated with error_* and raw_output on failure.
    """
    raw_redacted = redact_secrets(raw)
    run.raw_output = raw_redacted[:100000]  # cap size
    parsed = _extract_json(raw)
    if not parsed:
        run.error_code = "PARSE_ERROR"
        run.error_message = "Model output was not valid JSON."
        run.error_details = "Failed to parse as JSON. Check raw_output for content."
        return None, "PARSE_ERROR"
    if parsed.get("error"):
        run.error_code = "VALIDATION_ERROR"
        run.error_message = str(parsed.get("error", "Generator returned error"))[:500]
        run.error_details = run.error_message
        return None, "VALIDATION_ERROR"
    valid, errors = validate_blueprint_v1(parsed)
    if valid:
        return parsed, None
    run.error_code = "VALIDATION_ERROR"
    run.error_message = "; ".join(errors[:5])[:500] if errors else "Schema validation failed"
    run.error_details = "\n".join(errors[:50])
    return None, "VALIDATION_ERROR"


def run_blueprint_run(run_id: UUID, db: Session | None = None) -> None:
    """
    Process a single TemplateBlueprintRun: generating -> validating -> ready/failed.
    Updates run and template; stores redacted raw_output and error_* on failure.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        run = session.query(TemplateBlueprintRun).filter(TemplateBlueprintRun.id == run_id).first()
        if not run:
            logger.warning("Blueprint run not found: %s", run_id)
            return
        if run.status not in ("queued",):
            logger.info("Run %s already in status %s, skipping", run_id, run.status)
            return
        template = session.query(TemplateRegistry).filter(TemplateRegistry.id == run.template_id).first()
        if not template:
            run.status = "failed"
            run.error_code = "INTERNAL"
            run.error_message = "Template not found."
            run.finished_at = datetime.utcnow()
            session.commit()
            return
        if not getattr(settings, "OPENAI_API_KEY", None):
            run.status = "failed"
            run.error_code = "OPENAI_ERROR"
            run.error_message = "OpenAI API key not set."
            run.finished_at = datetime.utcnow()
            session.commit()
            return

        correlation_id = str(uuid.uuid4())[:8]
        run.correlation_id = correlation_id
        run.status = "generating"
        run.started_at = datetime.utcnow()
        run.model_used = _model_for_attempt(run.attempt_number)
        session.commit()

        demo_context = {"category": template.category or "general", "style": template.style or "modern"}
        raw_output: str | None = None
        model_used = run.model_used
        last_error_code: str | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            run.attempt_number = attempt
            run.model_used = _model_for_attempt(attempt)
            model_used = run.model_used
            try:
                raw_output, model_used = _generate_raw(template, demo_context, run.model_used if attempt == 2 else None)
            except Exception as e:
                logger.exception("Blueprint generate attempt %s failed: %s", attempt, e)
                last_error_code = "OPENAI_ERROR"
                run.raw_output = redact_secrets(str(e))[:5000]
                run.error_code = "OPENAI_ERROR"
                run.error_message = "Blueprint generation failed. See details."
                run.error_details = traceback.format_exc()
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                session.commit()
                if attempt < MAX_ATTEMPTS:
                    run.status = "queued"
                    run.error_code = None
                    run.error_message = None
                    run.error_details = None
                    run.raw_output = None
                    session.commit()
                    continue
                return

            run.status = "validating"
            session.commit()

            parsed, err_code = _parse_and_validate(raw_output or "", run, session)
            if parsed is not None:
                run.status = "ready"
                run.blueprint_json = parsed
                run.finished_at = datetime.utcnow()
                run.error_code = None
                run.error_message = None
                run.error_details = None
                run.model_used = model_used
                session.commit()
                template.blueprint_json = parsed
                template.blueprint_schema_version = 1
                template.blueprint_status = "ready"
                template.blueprint_last_run_id = run.id
                template.blueprint_updated_at = datetime.utcnow()
                session.commit()
                return
            last_error_code = err_code
            # Self-repair once for PARSE_ERROR or VALIDATION_ERROR
            errors_list = (run.error_details or "").split("\n") if run.error_details else []
            repair_raw = _repair_once(raw_output or "", errors_list)
            if repair_raw:
                raw_output = repair_raw
                run.raw_output = redact_secrets(raw_output)[:100000]
                parsed, _ = _parse_and_validate(raw_output, run, session)
                if parsed is not None:
                    run.status = "ready"
                    run.blueprint_json = parsed
                    run.finished_at = datetime.utcnow()
                    run.error_code = None
                    run.error_message = None
                    run.error_details = None
                    run.model_used = model_used
                    session.commit()
                    template.blueprint_json = parsed
                    template.blueprint_schema_version = 1
                    template.blueprint_status = "ready"
                    template.blueprint_last_run_id = run.id
                    template.blueprint_updated_at = datetime.utcnow()
                    session.commit()
                    return
            # Retry with fallback model only for OPENAI_ERROR (and optionally PARSE_ERROR)
            if err_code in RETRYABLE_ERROR_CODES and attempt < MAX_ATTEMPTS:
                run.status = "queued"
                run.error_code = None
                run.error_message = None
                run.error_details = None
                run.raw_output = None
                session.commit()
                continue
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            session.commit()
            template.blueprint_status = "failed"
            template.blueprint_last_run_id = run.id
            template.blueprint_updated_at = datetime.utcnow()
            session.commit()
            return
    except Exception as e:
        logger.exception("run_blueprint_run failed: %s", e)
        try:
            run = session.query(TemplateBlueprintRun).filter(TemplateBlueprintRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.error_code = "INTERNAL"
                run.error_message = "Blueprint generation failed. See details."
                run.error_details = traceback.format_exc()[:10000]
                run.finished_at = datetime.utcnow()
                session.commit()
        except Exception:
            pass
    finally:
        if close and session:
            session.close()
