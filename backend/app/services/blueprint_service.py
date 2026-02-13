"""
Blueprint generation service: called by worker for job type template.blueprint.generate.
Loads run + template, generates via LLM, parses/validates, persists to run and template.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.jobs.blueprint_run_worker import run_blueprint_run

logger = logging.getLogger(__name__)


def generate_blueprint(template_id: UUID, run_id: UUID, db: Session | None = None) -> None:
    """
    Run blueprint generation for the given run. Updates TemplateBlueprintRun and template.
    Called by worker when processing job type template.blueprint.generate.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        run_blueprint_run(run_id, db=session)
    finally:
        if close and session:
            session.close()
