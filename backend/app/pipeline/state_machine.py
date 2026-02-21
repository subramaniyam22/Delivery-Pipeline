"""
Single source of truth for project stage order and valid transitions.
All stage transitions must go through transition_project_stage().
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Project,
    ProjectStageState,
    ProjectStatus,
    Stage,
)
from app.pipeline.stages import STAGE_KEY_TO_ORDER, STAGE_TO_KEY, STAGES

logger = logging.getLogger(__name__)

# Explicit project lifecycle statuses (ProjectStatus enum extended in code; DB may need migration for HOLD/NEEDS_REVIEW)
# ACTIVE, HOLD, NEEDS_REVIEW, COMPLETE, ARCHIVED, PAUSED are the canonical set for autonomy.
# DRAFT, CANCELLED, COMPLETED remain for backward compatibility (COMPLETED = COMPLETE).

# Allowed stage order (strict)
STAGE_ORDER: List[Stage] = [
    Stage.SALES,
    Stage.ONBOARDING,
    Stage.ASSIGNMENT,
    Stage.BUILD,
    Stage.TEST,
    Stage.DEFECT_VALIDATION,
    Stage.COMPLETE,
]

# Valid next stage(s) from each stage (no branching except DEFECT_VALIDATION -> BUILD or COMPLETE)
VALID_NEXT: Dict[Stage, List[Stage]] = {
    Stage.SALES: [Stage.ONBOARDING],
    Stage.ONBOARDING: [Stage.ASSIGNMENT],
    Stage.ASSIGNMENT: [Stage.BUILD],
    Stage.BUILD: [Stage.TEST],
    Stage.TEST: [Stage.DEFECT_VALIDATION, Stage.BUILD],  # BUILD = rework
    Stage.DEFECT_VALIDATION: [Stage.COMPLETE, Stage.BUILD],  # BUILD = rework
    Stage.COMPLETE: [],
}


def get_next_stage(from_stage: Stage, success: bool = True, rework: bool = False) -> Optional[Stage]:
    """Return the next stage after from_stage. For TEST/DEFECT_VALIDATION, rework=True means BUILD."""
    if from_stage not in VALID_NEXT:
        return None
    options = VALID_NEXT[from_stage]
    if rework and Stage.BUILD in options:
        return Stage.BUILD
    # Default: first option (success path)
    return options[0] if options else None


def can_transition(from_stage: Optional[Stage], to_stage: Stage) -> bool:
    """Check if transition from_stage -> to_stage is allowed."""
    if from_stage is None:
        return to_stage in STAGE_ORDER
    if from_stage not in VALID_NEXT:
        return False
    return to_stage in VALID_NEXT[from_stage]


def transition_project_stage(
    db: Session,
    project_id: UUID,
    from_stage: Optional[Stage],
    to_stage: Stage,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    actor_user_id: Optional[UUID] = None,
) -> bool:
    """
    Atomically transition project to a new stage. Idempotent if already in to_stage.
    Updates project.current_stage, project_stage_state, and writes audit log.
    Returns True if transition was applied, False if no-op (e.g. already in to_stage).
    """
    project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
    if not project:
        logger.warning("transition_project_stage: project not found %s", project_id)
        return False

    current = project.current_stage
    if current == to_stage:
        return False

    if not can_transition(from_stage or current, to_stage):
        logger.warning(
            "transition_project_stage: invalid transition project=%s from=%s to=%s",
            project_id, from_stage or current, to_stage,
        )
        return False

    previous_stage = project.current_stage
    project.current_stage = to_stage
    project.updated_at = datetime.utcnow()

    # Stage history and phase_start_dates for UI/timeline
    history = getattr(project, "stage_history", None) or []
    history.append({
        "from_stage": previous_stage.value if previous_stage else None,
        "to_stage": to_stage.value,
        "at": datetime.utcnow().isoformat(),
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
    })
    project.stage_history = history
    if to_stage:
        project.phase_start_dates = getattr(project, "phase_start_dates", None) or {}
        if not project.phase_start_dates.get(to_stage.value):
            project.phase_start_dates[to_stage.value] = datetime.utcnow().isoformat()

    # Update project_stage_state: mark previous stage complete (if any), set next to not_started or ready
    from_key = STAGE_TO_KEY.get(previous_stage) if previous_stage else None
    to_key = STAGE_TO_KEY.get(to_stage)
    if from_key:
        prev_row = db.query(ProjectStageState).filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == from_key,
        ).first()
        if prev_row:
            prev_row.status = "complete"
            prev_row.blocked_reasons_json = []
            prev_row.required_actions_json = []
            prev_row.updated_at = datetime.utcnow()
    if to_key:
        next_row = db.query(ProjectStageState).filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == to_key,
        ).first()
        if next_row:
            if next_row.status in ("not_started", "blocked", "failed"):
                next_row.status = "ready"
                next_row.blocked_reasons_json = []
                next_row.required_actions_json = []
            next_row.updated_at = datetime.utcnow()

    payload = {
        "from_stage": previous_stage.value if previous_stage else None,
        "to_stage": to_stage.value,
        "reason": reason,
        **(metadata or {}),
    }
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=actor_user_id,
            action="STAGE_TRANSITION",
            payload_json=payload,
        )
    )
    db.commit()
    logger.info(
        "transition_project_stage: project=%s %s -> %s",
        project_id, previous_stage.value if previous_stage else None, to_stage.value,
    )
    return True


def set_project_hold(
    db: Session,
    project_id: UUID,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    actor_user_id: Optional[UUID] = None,
) -> None:
    """Set project status to HOLD with reason."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    project.status = ProjectStatus.HOLD
    project.hold_reason = reason
    project.needs_review_reason = None
    project.autopilot_paused_reason = reason
    project.updated_at = datetime.utcnow()
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=actor_user_id,
            action="PROJECT_HOLD",
            payload_json={"reason": reason, **(metadata or {})},
        )
    )
    db.commit()


def set_project_needs_review(
    db: Session,
    project_id: UUID,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    actor_user_id: Optional[UUID] = None,
) -> None:
    """Set project status to NEEDS_REVIEW with reason."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    project.status = ProjectStatus.NEEDS_REVIEW
    project.needs_review_reason = reason
    project.autopilot_paused_reason = reason
    project.updated_at = datetime.utcnow()
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=actor_user_id,
            action="PROJECT_NEEDS_REVIEW",
            payload_json={"reason": reason, **(metadata or {})},
        )
    )
    db.commit()


def is_autopilot_eligible(project: Project) -> bool:
    """Return False if project is on HOLD or NEEDS_REVIEW; only ACTIVE projects auto-advance."""
    if project.status in (ProjectStatus.HOLD, ProjectStatus.NEEDS_REVIEW):
        return False
    if project.status not in (ProjectStatus.ACTIVE, ProjectStatus.DRAFT):
        return False
    return True
