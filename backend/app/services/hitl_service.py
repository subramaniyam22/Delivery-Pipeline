"""
HITL gate resolution (global + project overrides), approval creation, and invalidation.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    AdminConfig,
    Artifact,
    OnboardingData,
    Project,
    ProjectConfig,
    ProjectContract,
    ProjectStageState,
    StageApproval,
    StageOutput,
)
from app.services.config_service import get_config
from app.services.conditions import evaluate_conditions_json

logger = logging.getLogger(__name__)

# Only one pending approval per (project_id, stage_key) - enforced in code
PENDING_STATUS = "pending"
APPROVED_STATUS = "approved"
REJECTED_STATUS = "rejected"
EXPIRED_STATUS = "expired"
INVALIDATED_STATUS = "invalidated"

# Pending approval expiry (configurable); lazy check in evaluate
PENDING_APPROVAL_EXPIRY_DAYS = 7


def get_global_hitl_gates(db: Session) -> List[Dict[str, Any]]:
    """Return global HITL gate rules from AdminConfig key hitl_gates_json."""
    config = get_config(db, "hitl_gates_json")
    if not config or not config.value_json:
        return []
    if isinstance(config.value_json, list):
        return config.value_json
    return []


def get_project_overrides(db: Session, project_id: UUID) -> List[Dict[str, Any]]:
    """Return project-level HITL overrides from ProjectConfig.hitl_overrides_json."""
    pc = db.query(ProjectConfig).filter(ProjectConfig.project_id == project_id).first()
    if not pc or not pc.hitl_overrides_json:
        return []
    if isinstance(pc.hitl_overrides_json, list):
        return pc.hitl_overrides_json
    return []


def resolve_gate_for_stage(
    stage_key: str,
    global_rules: List[Dict[str, Any]],
    project_rules: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Project override (by stage_key) > global > implicit { mode: never }."""
    for rule in project_rules:
        if rule.get("stage_key") == stage_key:
            return dict(rule)
    for rule in global_rules:
        if rule.get("stage_key") == stage_key:
            return dict(rule)
    return {"stage_key": stage_key, "mode": "never"}


def should_require_approval(
    gate_rule: Dict[str, Any],
    context: Dict[str, Any],
    autopilot_mode: str = "conditional",
) -> Tuple[bool, List[str]]:
    """
    Returns (required: bool, reasons: list).
    Full autopilot mode: treat conditional as never, but still respect always.
    """
    mode = (gate_rule.get("mode") or "never").strip().lower()
    reasons: List[str] = []

    # Feature flag: full autopilot skips conditional gates but keeps always
    if autopilot_mode == "full":
        if mode == "always":
            return True, ["Approval required by policy"]
        return False, []

    if mode == "never":
        return False, []
    if mode == "always":
        return True, ["Approval required by policy"]

    if mode == "conditional":
        conditions_json = gate_rule.get("conditions_json")
        passed, failure_reasons = evaluate_conditions_json(conditions_json, context)
        if passed:
            return False, []
        reasons = [f"Gate conditions failed: {r}" for r in failure_reasons] if failure_reasons else ["Gate conditions failed"]
        return True, reasons

    return False, []


def ensure_pending_approval(
    db: Session,
    project_id: UUID,
    stage_key: str,
    gate_snapshot: Dict[str, Any],
    inputs_fingerprint: str,
    reasons: List[str],
) -> StageApproval:
    """Create or update pending approval for (project_id, stage_key). Only one pending per stage."""
    existing = (
        db.query(StageApproval)
        .filter(
            StageApproval.project_id == project_id,
            StageApproval.stage_key == stage_key,
            StageApproval.status == PENDING_STATUS,
        )
        .first()
    )
    if existing:
        existing.gate_snapshot_json = gate_snapshot
        existing.inputs_fingerprint = inputs_fingerprint
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    approval = StageApproval(
        project_id=project_id,
        stage_key=stage_key,
        status=PENDING_STATUS,
        gate_snapshot_json=gate_snapshot,
        inputs_fingerprint=inputs_fingerprint,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def compute_stage_inputs_fingerprint(
    db: Session,
    project_id: UUID,
    stage_key: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Hash of relevant inputs for invalidation. Include contract version when present."""
    parts: List[str] = [stage_key]
    pc = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    if pc:
        parts.append(f"contract_v:{pc.version}")
        parts.append(f"contract_updated:{pc.updated_at}")
    else:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            parts.append(f"p_updated:{project.updated_at or project.created_at}")
        ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if ob:
            parts.append(f"ob_updated:{ob.updated_at}")
            parts.append(f"template:{ob.selected_template_id or ob.theme_preference or ''}")
        artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()
        if artifacts:
            parts.append(f"art_count:{len(artifacts)}")
            last_art = max((a.created_at for a in artifacts), default=None)
            if last_art:
                parts.append(f"art_last:{last_art}")
        outputs = db.query(StageOutput).filter(StageOutput.project_id == project_id).all()
        if outputs:
            parts.append(f"out_count:{len(outputs)}")
            for o in outputs[:20]:
                parts.append(f"out_{o.stage.value}:{o.id}")
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def invalidate_pending_approvals_if_stale(db: Session, project_id: UUID) -> None:
    """
    For each pending approval, recompute fingerprint; if different, mark invalidated.
    Optionally create new pending (we keep same row and set status=invalidated; orchestrator will create new on next evaluate).
    """
    pendings = (
        db.query(StageApproval)
        .filter(
            StageApproval.project_id == project_id,
            StageApproval.status == PENDING_STATUS,
        )
        .all()
    )
    for approval in pendings:
        new_fp = compute_stage_inputs_fingerprint(db, project_id, approval.stage_key)
        if new_fp != approval.inputs_fingerprint:
            approval.status = INVALIDATED_STATUS
            approval.updated_at = datetime.utcnow()
            row = (
                db.query(ProjectStageState)
                .filter(
                    ProjectStageState.project_id == project_id,
                    ProjectStageState.stage_key == approval.stage_key,
                )
                .first()
            )
            if row and row.status == "awaiting_approval":
                row.blocked_reasons_json = list(row.blocked_reasons_json or []) + ["Inputs changed; approval must be re-approved"]
                row.required_actions_json = ["An approver must approve this stage"]
                row.updated_at = datetime.utcnow()
    db.commit()


def expire_old_pending_approvals(db: Session, project_id: Optional[UUID] = None) -> int:
    """Mark pending approvals older than PENDING_APPROVAL_EXPIRY_DAYS as expired. Returns count expired."""
    cutoff = datetime.utcnow() - timedelta(days=PENDING_APPROVAL_EXPIRY_DAYS)
    q = db.query(StageApproval).filter(
        StageApproval.status == PENDING_STATUS,
        StageApproval.created_at < cutoff,
    )
    if project_id:
        q = q.filter(StageApproval.project_id == project_id)
    count = 0
    for approval in q.all():
        approval.status = EXPIRED_STATUS
        approval.updated_at = datetime.utcnow()
        row = (
            db.query(ProjectStageState)
            .filter(
                ProjectStageState.project_id == approval.project_id,
                ProjectStageState.stage_key == approval.stage_key,
            )
            .first()
        )
        if row and row.status == "awaiting_approval":
            reasons = list(row.blocked_reasons_json or [])
            if "Approval request expired" not in str(reasons):
                row.blocked_reasons_json = reasons + ["Approval request expired; please re-approve"]
            row.updated_at = datetime.utcnow()
        count += 1
    if count:
        db.commit()
    return count
