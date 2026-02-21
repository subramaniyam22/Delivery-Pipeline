"""
Pipeline orchestrator: evaluate stage readiness and auto-advance when safe.
Idempotent, with cooldown, circuit breaker, and ambiguity guard.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.jobs.queue import enqueue_job
from app.models import (
    AuditLog,
    ClientReminder,
    JobRun,
    JobRunStatus,
    Notification,
    OnboardingData,
    PipelineEvent,
    Project,
    ProjectStageState,
    ProjectStatus,
    Role,
    Stage,
    StageApproval,
    StageOutput,
    TemplateRegistry,
    User,
)
from app.pipeline.stages import (
    BLOCKED_REASON_NOT_IMPLEMENTED,
    GATES_IMPLEMENTED_KEYS,
    STAGES,
    STAGE_KEY_TO_ORDER,
    STAGE_KEY_TO_STAGE,
    STAGE_TO_KEY,
)
from app.pipeline.state_machine import (
    get_next_stage,
    is_autopilot_eligible,
    set_project_hold,
    set_project_needs_review,
    transition_project_stage,
)
from app.services.contract_service import get_contract
from app.services.hitl_service import (
    ensure_pending_approval,
    expire_old_pending_approvals,
    get_global_hitl_gates,
    get_project_overrides,
    resolve_gate_for_stage,
    should_require_approval,
    compute_stage_inputs_fingerprint,
)

logger = logging.getLogger(__name__)

# Throttle: do not enqueue if last action was within this many seconds
AUTOPILOT_THROTTLE_SECONDS = 10
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_LOCK_MINUTES = 30

# Event types for pipeline_events
EVENT_EVALUATED = "EVALUATED"
EVENT_AUTO_ENQUEUED = "AUTO_ENQUEUED"
EVENT_AUTO_PAUSED = "AUTO_PAUSED"
EVENT_CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
EVENT_JOB_COMPLETED = "JOB_COMPLETED"
EVENT_JOB_FAILED = "JOB_FAILED"


@dataclass
class StageStateView:
    stage_key: str
    status: str
    blocked_reasons: List[str]
    required_actions: List[str]
    last_job_id: Optional[UUID]
    updated_at: Optional[datetime]


@dataclass
class SafetyFlags:
    ambiguous_next_stage: bool = False
    circuit_breaker: bool = False
    cooldown_active: bool = False


@dataclass
class PendingApprovalView:
    stage_key: str
    id: UUID
    created_at: datetime
    reasons: List[str]
    approver_roles: List[str]


@dataclass
class PipelineStatus:
    project_id: UUID
    autopilot_enabled: bool
    autopilot_mode: str
    current_stage_key: Optional[str]
    stage_states: List[StageStateView]
    next_ready_stages: List[str]
    blocked_summary: List[str]
    awaiting_approval_stage_key: Optional[str] = None
    safety_flags: SafetyFlags = field(default_factory=SafetyFlags)
    pending_approvals: List[PendingApprovalView] = field(default_factory=list)


def _log_pipeline_event(
    db: Session,
    project_id: UUID,
    event_type: str,
    stage_key: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        db.add(
            PipelineEvent(
                project_id=project_id,
                stage_key=stage_key,
                event_type=event_type,
                details_json=details or {},
            )
        )
        db.commit()
    except Exception as e:
        logger.warning("Failed to log pipeline event: %s", e)
        db.rollback()


def ensure_stage_rows(db: Session, project_id: UUID) -> None:
    """Create missing project_stage_state rows for all STAGES (not_started)."""
    existing = {
        row.stage_key
        for row in db.query(ProjectStageState.stage_key).filter(
            ProjectStageState.project_id == project_id
        ).all()
    }
    for s in STAGES:
        key = s["key"]
        if key in existing:
            continue
        db.add(
            ProjectStageState(
                project_id=project_id,
                stage_key=key,
                status="not_started",
                blocked_reasons_json=[],
                required_actions_json=[],
            )
        )
    db.commit()


def build_hitl_context(db: Session, project_id: UUID, contract: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build context dict for HITL condition evaluation from contract (preferred) or DB."""
    if contract:
        meta = contract.get("meta", {})
        onboarding = contract.get("onboarding", {})
        assignments = contract.get("assignments", {})
        stages = contract.get("stages", {})
        artifacts = contract.get("artifacts", {})
        build_out = (artifacts.get("build_outputs") or {})
        quality = contract.get("quality", {})
        stage_outputs_flat: Dict[str, Any] = {}
        _key_to_short = {"0_sales": "sales", "1_onboarding": "onboarding", "2_assignment": "assignment", "3_build": "build", "4_test": "test", "5_defect_validation": "defect_validation", "6_complete": "complete"}
        for sk, sv in (stages or {}).items():
            out = (sv.get("outputs") or {}) if isinstance(sv, dict) else {}
            short = _key_to_short.get(sk, sk.replace("_", ""))
            if short:
                stage_outputs_flat[short] = out
        return {
            "project": {
                "id": meta.get("project_id"),
                "updated_at": meta.get("updated_at"),
                "consultant_user_id": assignments.get("consultant_id"),
                "builder_user_id": assignments.get("builder_id"),
                "tester_user_id": assignments.get("tester_id"),
            },
            "onboarding": {
                "submitted_at": None,
                "selected_template_id": (contract.get("template") or {}).get("selected_template_id"),
                "theme_preference": (onboarding.get("design_preferences") or {}).get("theme_preference"),
                "updated_at": onboarding.get("updated_at"),
            },
            "stage_states": {k: {"status": v.get("status") if isinstance(v, dict) else "not_started", "blocked_reasons": (v.get("blocked_reasons") or []) if isinstance(v, dict) else []} for k, v in stages.items()},
            "stage_outputs": stage_outputs_flat,
            "quality": quality,
        }
    # Fallback: build from DB
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {}
    ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    onboarding_minimal: Dict[str, Any] = {}
    if ob:
        onboarding_minimal = {
            "submitted_at": ob.submitted_at.isoformat() if ob.submitted_at else None,
            "selected_template_id": ob.selected_template_id,
            "theme_preference": ob.theme_preference,
            "updated_at": ob.updated_at.isoformat() if ob.updated_at else None,
        }
    rows = db.query(ProjectStageState).filter(ProjectStageState.project_id == project_id).all()
    stage_states = {r.stage_key: {"status": r.status, "blocked_reasons": list(r.blocked_reasons_json or [])} for r in rows}
    outputs = db.query(StageOutput).filter(StageOutput.project_id == project_id).all()
    stage_outputs: Dict[str, Any] = {}
    for o in outputs:
        key = o.stage.value.lower()
        if key not in stage_outputs:
            stage_outputs[key] = []
        stage_outputs[key].append({
            "score": o.score,
            "report_json": o.report_json or {},
            "structured_output_json": o.structured_output_json or {},
        })
    stage_outputs_flat = {}
    for k, v in stage_outputs.items():
        if v:
            merged = {}
            for item in v:
                if isinstance(item, dict):
                    for kk, vv in (item.get("report_json") or {}).items():
                        merged[kk] = vv
                    for kk, vv in (item.get("structured_output_json") or {}).items():
                        merged[kk] = vv
            stage_outputs_flat[k] = merged
    return {
        "project": {
            "id": str(project.id),
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "consultant_user_id": str(project.consultant_user_id) if project.consultant_user_id else None,
            "builder_user_id": str(project.builder_user_id) if project.builder_user_id else None,
            "tester_user_id": str(project.tester_user_id) if project.tester_user_id else None,
        },
        "onboarding": onboarding_minimal,
        "stage_states": stage_states,
        "stage_outputs": stage_outputs_flat,
        "quality": {},
    }


def _evaluate_stage_gate(
    db: Session,
    project_id: UUID,
    stage_key: str,
    stage_state: ProjectStageState,
    contract: Optional[Dict[str, Any]] = None,
) -> tuple[str, List[str], List[str]]:
    """
    Returns (status, blocked_reasons, required_actions).
    Uses contract when provided; otherwise reads from DB.
    """
    if contract is None:
        project = db.query(Project).filter(Project.id == project_id).first()
    else:
        project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return "blocked", ["Project not found"], []

    if stage_key not in GATES_IMPLEMENTED_KEYS:
        return "blocked", [BLOCKED_REASON_NOT_IMPLEMENTED], []

    if stage_key == "1_onboarding":
        if contract:
            ob_status = (contract.get("onboarding") or {}).get("status", "draft")
            if ob_status == "submitted":
                return "complete", [], []
            return "blocked", ["Client onboarding not submitted"], []
        onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if not onboarding:
            return "blocked", ["Client onboarding not submitted"], []
        if onboarding.submitted_at is not None:
            return "complete", [], []
        return "blocked", ["Client onboarding not submitted"], []

    if stage_key == "2_assignment":
        if contract:
            stages = contract.get("stages") or {}
            ob_stage = stages.get("1_onboarding", {})
            if (ob_stage.get("status") or "") != "complete":
                return "blocked", ["Onboarding not complete"], []
            assignments = contract.get("assignments") or {}
            if assignments.get("consultant_id") and assignments.get("builder_id") and assignments.get("tester_id"):
                return "complete", [], []
            if not getattr(project, "autopilot_enabled", True):
                return "blocked", ["Autopilot disabled; manual assignment required"], []
            return "ready", [], ["Assignments missing: consultant/builder/tester"]
        ob = db.query(ProjectStageState).filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == "1_onboarding",
        ).first()
        if ob and ob.status != "complete":
            return "blocked", ["Onboarding not complete"], []
        if project.consultant_user_id and project.builder_user_id and project.tester_user_id:
            return "complete", [], []
        if not getattr(project, "autopilot_enabled", True):
            return "blocked", ["Autopilot disabled; manual assignment required"], []
        return "ready", [], ["Assignments missing: consultant/builder/tester"]

    if stage_key == "3_build":
        if contract:
            stages = contract.get("stages") or {}
            if (stages.get("2_assignment", {}).get("status") or "") != "complete":
                return "blocked", ["Assignment not complete"], []
        else:
            r_assignment = db.query(ProjectStageState).filter(
                ProjectStageState.project_id == project_id,
                ProjectStageState.stage_key == "2_assignment",
            ).first()
            if not r_assignment or r_assignment.status != "complete":
                return "blocked", ["Assignment not complete"], []
        template_id = None
        if contract:
            template_id = (contract.get("template") or {}).get("selected_template_id") or (contract.get("onboarding") or {}).get("selected_template_id")
        if not template_id:
            ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
            if ob:
                template_id = getattr(ob, "selected_template_id", None) or getattr(ob, "theme_preference", None)
        if template_id:
            try:
                tid = UUID(str(template_id)) if template_id else None
                if tid:
                    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
                    if template:
                        v_status = getattr(template, "validation_status", None) or "not_run"
                        if v_status != "passed":
                            reasons = (getattr(template, "validation_results_json", None) or {}).get("failed_reasons") or ["Run validation in Template Registry"]
                            msg = "Validation failed: " + ("; ".join(reasons[:3]) if isinstance(reasons, list) else str(reasons))
                            return "blocked", [msg], ["Run template validation in Configuration → Template Registry"]
            except (ValueError, TypeError):
                pass
        # Client preview must be ready before Build stage can proceed
        client_preview_status = getattr(project, "client_preview_status", None) or "not_generated"
        if client_preview_status != "ready":
            if client_preview_status == "failed":
                err = getattr(project, "client_preview_error", None) or "Preview generation failed"
                return "blocked", [err], ["Regenerate client preview in Project detail"]
            return "blocked", ["Client preview not ready"], ["Generate client preview in Project detail"]
        return "ready", [], []

    return "blocked", [BLOCKED_REASON_NOT_IMPLEMENTED], []


def evaluate_project(db: Session, project_id: UUID) -> PipelineStatus:
    """
    Load project and stage rows, determine current stage and readiness,
    update project_stage_state rows, return status. Does not enqueue.
    Uses delivery contract when available for deterministic readiness and HITL.
    """
    ensure_stage_rows(db, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project not found")

    contract = get_contract(db, project_id)
    if contract is None and getattr(project, "contract_build_error", None):
        # Contract build failed: block all non-complete stages and return
        rows = db.query(ProjectStageState).filter(ProjectStageState.project_id == project_id).order_by(ProjectStageState.stage_key).all()
        for r in rows:
            if r.status != "complete":
                r.status = "blocked"
                r.blocked_reasons_json = [project.contract_build_error or "Contract build failed"]
                r.required_actions_json = []
                r.updated_at = datetime.utcnow()
        db.commit()
        stage_states = [StageStateView(r.stage_key, r.status, list(r.blocked_reasons_json or []), list(r.required_actions_json or []), r.last_job_id, r.updated_at) for r in rows]
        return PipelineStatus(
            project_id=project_id,
            autopilot_enabled=bool(project.autopilot_enabled),
            autopilot_mode=project.autopilot_mode or "conditional",
            current_stage_key=rows[0].stage_key if rows else None,
            stage_states=stage_states,
            next_ready_stages=[],
            blocked_summary=[f"Contract build failed: {project.contract_build_error}"],
            awaiting_approval_stage_key=None,
            safety_flags=SafetyFlags(),
            pending_approvals=[],
        )

    rows = (
        db.query(ProjectStageState)
        .filter(ProjectStageState.project_id == project_id)
        .order_by(ProjectStageState.stage_key)
        .all()
    )
    by_key = {r.stage_key: r for r in rows}

    # Determine current = first stage not complete (by order)
    sorted_keys = sorted(by_key.keys(), key=lambda k: STAGE_KEY_TO_ORDER.get(k, 99))
    current_stage_key = None
    for key in sorted_keys:
        if by_key[key].status != "complete":
            current_stage_key = key
            break

    # Build HITL context from contract (preferred) or DB
    hitl_context = build_hitl_context(db, project_id, contract=contract)
    global_gates = get_global_hitl_gates(db)
    project_overrides = get_project_overrides(db, project_id)
    autopilot_mode = (project.autopilot_mode or "conditional").strip().lower()

    # Evaluate each stage in order; first non-complete gets evaluated for readiness
    for key in sorted_keys:
        row = by_key[key]
        if row.status in ("running", "awaiting_approval"):
            continue
        if row.status == "complete":
            continue
        status, blocked, required = _evaluate_stage_gate(db, project_id, key, row, contract=contract)
        row.status = status
        row.blocked_reasons_json = blocked
        row.required_actions_json = required
        if status == "complete":
            row.last_error = None
        row.updated_at = datetime.utcnow()

        # HITL: if stage would be ready, check if approval required
        if status == "ready":
            gate_rule = resolve_gate_for_stage(key, global_gates, project_overrides)
            required_approval, approval_reasons = should_require_approval(gate_rule, hitl_context, autopilot_mode)
            if required_approval:
                row.status = "awaiting_approval"
                row.blocked_reasons_json = ["Awaiting approval"] + (approval_reasons or [])
                approver_roles = gate_rule.get("approver_roles") or ["admin", "manager"]
                row.required_actions_json = [
                    {"type": "approve", "stage_key": key},
                    {"type": "reject", "stage_key": key},
                    f"Approver roles: {', '.join(approver_roles)}",
                ]
                fingerprint = compute_stage_inputs_fingerprint(db, project_id, key)
                snapshot = dict(gate_rule)
                snapshot["_reasons"] = approval_reasons or []
                ensure_pending_approval(
                    db, project_id, key,
                    gate_snapshot=snapshot,
                    inputs_fingerprint=fingerprint,
                    reasons=approval_reasons or [],
                )
                row.updated_at = datetime.utcnow()

    # Assignment stage: if assignments exist, mark complete (state-only, no job)
    if "2_assignment" in by_key:
        r2 = by_key["2_assignment"]
        assignments_ok = project.consultant_user_id and project.builder_user_id and project.tester_user_id
        if contract:
            a = contract.get("assignments") or {}
            assignments_ok = bool(a.get("consultant_id") and a.get("builder_id") and a.get("tester_id"))
        if r2.status == "ready" and assignments_ok:
            r2.status = "complete"
            r2.blocked_reasons_json = []
            r2.required_actions_json = []
            r2.last_error = None
            r2.updated_at = datetime.utcnow()

    # Lazy expiry of old pending approvals
    expire_old_pending_approvals(db, project_id)

    db.commit()
    _log_pipeline_event(db, project_id, EVENT_EVALUATED, details={"current_stage_key": current_stage_key})

    # Pending approvals for response
    pending_approval_rows = (
        db.query(StageApproval)
        .filter(
            StageApproval.project_id == project_id,
            StageApproval.status == "pending",
        )
        .all()
    )
    pending_approvals = [
        PendingApprovalView(
            stage_key=a.stage_key,
            id=a.id,
            created_at=a.created_at,
            reasons=(a.gate_snapshot_json or {}).get("_reasons", []) or [],
            approver_roles=list((a.gate_snapshot_json or {}).get("approver_roles", [])) or ["admin", "manager"],
        )
        for a in pending_approval_rows
    ]

    # Build response
    stage_states = [
        StageStateView(
            stage_key=r.stage_key,
            status=r.status,
            blocked_reasons=list(r.blocked_reasons_json or []),
            required_actions=list(r.required_actions_json or []),
            last_job_id=r.last_job_id,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    next_ready = [s.stage_key for s in stage_states if s.status == "ready"]
    blocked_summary = []
    for s in stage_states:
        if s.blocked_reasons:
            blocked_summary.append(f"{s.stage_key}: {'; '.join(s.blocked_reasons)}")
    awaiting = next((s.stage_key for s in stage_states if s.status == "awaiting_approval"), None)

    return PipelineStatus(
        project_id=project_id,
        autopilot_enabled=bool(project.autopilot_enabled),
        autopilot_mode=project.autopilot_mode or "conditional",
        current_stage_key=current_stage_key,
        stage_states=stage_states,
        next_ready_stages=next_ready,
        blocked_summary=blocked_summary,
        awaiting_approval_stage_key=awaiting,
        safety_flags=SafetyFlags(),
        pending_approvals=pending_approvals,
    )


def _is_state_only_stage(stage_key: str) -> bool:
    """Stages that complete by data only (no job to enqueue). 2_assignment runs via auto-assignment job."""
    return stage_key == "1_onboarding"


def _get_stage_for_job(stage_key: str) -> Optional[Stage]:
    """Return Stage enum for enqueue; None if state-only or placeholder."""
    return STAGE_KEY_TO_STAGE.get(stage_key)


def auto_advance(db: Session, project_id: UUID, trigger_source: str) -> PipelineStatus:
    """
    Evaluate project; if autopilot on and safe, enqueue exactly one ready stage when applicable.
    Idempotent: no double-enqueue for same stage; throttle; circuit breaker; ambiguity guard.
    """
    status = evaluate_project(db, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return status

    if not project.autopilot_enabled or (project.autopilot_mode or "").lower() == "off":
        return status
    if not is_autopilot_eligible(project):
        return status

    now = datetime.utcnow()
    if project.autopilot_lock_until and project.autopilot_lock_until > now:
        status.safety_flags.cooldown_active = True
        return status

    # Throttle
    if project.autopilot_last_action_at:
        if (now - project.autopilot_last_action_at).total_seconds() < AUTOPILOT_THROTTLE_SECONDS:
            status.safety_flags.cooldown_active = True
            return status

    # Any stage running? Do nothing.
    rows = (
        db.query(ProjectStageState)
        .filter(ProjectStageState.project_id == project_id)
        .all()
    )
    by_key = {r.stage_key: r for r in rows}
    if any(r.status == "running" for r in rows):
        return status
    if any(r.status == "awaiting_approval" for r in rows):
        return status

    ready = [s.stage_key for s in status.stage_states if s.status == "ready"]
    if not ready:
        return status

    if len(ready) > 1:
        status.safety_flags.ambiguous_next_stage = True
        project.autopilot_paused_reason = "Ambiguous next stage: requires admin decision"
        db.commit()
        _log_pipeline_event(
            db, project_id, EVENT_AUTO_PAUSED,
            details={"reason": "ambiguous_next_stage", "ready_stages": ready},
        )
        return evaluate_project(db, project_id)

    stage_key = ready[0]
    if _is_state_only_stage(stage_key):
        # Re-evaluate; state-only stages become complete in evaluate when data is present
        return evaluate_project(db, project_id)

    stage_enum = _get_stage_for_job(stage_key)
    if not stage_enum:
        return status

    # Idempotency: if last_job_id exists and job is QUEUED or RUNNING, do not enqueue
    row = by_key.get(stage_key)
    if row and row.last_job_id:
        job = db.query(JobRun).filter(JobRun.id == row.last_job_id).first()
        if job and job.status in (JobRunStatus.QUEUED, JobRunStatus.RUNNING):
            return status

    # Enqueue
    correlation_id = uuid.uuid4()
    idempotency_key = f"{project_id}:{stage_key}:0"
    payload = {
        "stage_key": stage_key,
        "project_id": str(project_id),
        "trigger_source": trigger_source,
        "idempotency_key": idempotency_key,
    }
    if stage_enum == Stage.BUILD:
        from app.services.template_instance_service import get_template_id_for_build
        tid = get_template_id_for_build(db, project_id)
        if tid:
            payload["template_id"] = str(tid)
    config_version = None
    try:
        from app.services.config_service import get_config
        cfg = get_config(db, "decision_policies_json")
        if cfg and getattr(cfg, "config_version", None) is not None:
            config_version = cfg.config_version
    except Exception:
        pass
    try:
        job_id = enqueue_job(
            project_id=project_id,
            stage=stage_enum,
            payload_json=payload,
            request_id=str(correlation_id),
            actor_user_id=None,
            db=db,
            correlation_id=correlation_id,
            requested_by="system",
            requested_by_user_id=None,
            config_version=config_version,
        )
        if row:
            row.last_job_id = job_id
            row.status = "running"
            row.updated_at = now
        project.autopilot_last_action_at = now
        project.autopilot_failure_count = 0
        db.commit()
        _log_pipeline_event(
            db, project_id, EVENT_AUTO_ENQUEUED,
            stage_key=stage_key,
            details={"job_id": str(job_id), "trigger_source": trigger_source},
        )
        return evaluate_project(db, project_id)
    except Exception as e:
        logger.exception("Autopilot enqueue failed for project %s stage %s", project_id, stage_key)
        project.autopilot_failure_count = (project.autopilot_failure_count or 0) + 1
        if row:
            row.last_error = str(e)
            row.status = "failed"
        if project.autopilot_failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
            project.autopilot_enabled = False
            project.autopilot_lock_until = now + timedelta(minutes=CIRCUIT_BREAKER_LOCK_MINUTES)
            project.autopilot_paused_reason = "Circuit breaker: repeated failures"
            _log_pipeline_event(db, project_id, EVENT_CIRCUIT_BREAKER, stage_key=stage_key, details={"error": str(e)})
        db.commit()
        return evaluate_project(db, project_id)


def on_job_success(
    db: Session,
    project_id: UUID,
    stage: Stage,
    job_id: UUID,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    """Called by worker when a job completes successfully. Updates stage state, syncs project.current_stage via state machine, triggers auto_advance."""
    stage_key = STAGE_TO_KEY.get(stage)
    if not stage_key:
        return
    row = (
        db.query(ProjectStageState)
        .filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == stage_key,
        )
        .first()
    )
    if row:
        row.status = "complete"
        row.last_error = None
        row.last_job_id = job_id
        row.updated_at = datetime.utcnow()
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.autopilot_failure_count = 0

    # Transition project.current_stage to next stage (single source of truth)
    next_stage = get_next_stage(stage, success=True, rework=False)
    if next_stage:
        transition_project_stage(
            db, project_id,
            from_stage=stage,
            to_stage=next_stage,
            reason="job_complete",
            metadata={"job_id": str(job_id), "trigger": "on_job_success"},
            actor_user_id=None,
        )
    # When Complete stage succeeds, mark project as COMPLETED (delivered)
    if stage == Stage.COMPLETE and project:
        project.status = ProjectStatus.COMPLETED
        project.updated_at = datetime.utcnow()
        _log_pipeline_event(
            db, project_id, EVENT_JOB_COMPLETED,
            stage_key=STAGE_TO_KEY.get(Stage.COMPLETE),
            details={"job_id": str(job_id), "project_completed": True},
        )
    db.commit()
    try:
        from app.services.contract_service import create_or_update_contract
        create_or_update_contract(db, project_id, source="system:job_complete")
    except Exception as e:
        logger.warning("Contract sync after job complete failed: %s", e)
    _log_pipeline_event(
        db, project_id, EVENT_JOB_COMPLETED,
        stage_key=stage_key,
        details={"job_id": str(job_id)},
    )
    auto_advance(db, project_id, trigger_source="job_complete")


def run_autopilot_sweeper(db: Session, max_projects: int = 50) -> int:
    """
    Backstop: find ACTIVE projects that are autopilot-eligible and have a ready stage
    with no running job; enqueue one per project. Idempotent and concurrency-safe.
    Returns number of projects that were evaluated for enqueue.
    """
    projects = (
        db.query(Project)
        .filter(
            Project.status == ProjectStatus.ACTIVE,
            Project.autopilot_enabled == True,
        )
        .limit(max_projects)
        .all()
    )
    count = 0
    for project in projects:
        if not is_autopilot_eligible(project):
            continue
        try:
            auto_advance(db, project.id, trigger_source="sweeper")
            count += 1
        except Exception as e:
            logger.warning("Autopilot sweeper project %s: %s", project.id, e)
            db.rollback()
    return count


def _get_defect_cycle_cap(db: Session) -> int:
    """Read defect_cycle_cap from decision_policies_json (default 5)."""
    from app.services.config_service import get_config
    config = get_config(db, "decision_policies_json")
    if config and isinstance(config.value_json, dict):
        try:
            return int(config.value_json.get("defect_cycle_cap", 5))
        except (TypeError, ValueError):
            pass
    return 5


def on_job_failure(
    db: Session,
    project_id: UUID,
    stage: Stage,
    job_id: UUID,
    error_message: Optional[str] = None,
) -> None:
    """Called by worker when a job fails. Updates stage state. For TEST/DEFECT_VALIDATION rework: transition to BUILD, increment defect_cycle_count; cap -> NEEDS_REVIEW."""
    stage_key = STAGE_TO_KEY.get(stage)
    if not stage_key:
        return
    row = (
        db.query(ProjectStageState)
        .filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == stage_key,
        )
        .first()
    )
    if row:
        row.status = "failed"
        row.last_error = error_message or "Job failed"
        row.last_job_id = job_id
        row.updated_at = datetime.utcnow()

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        db.commit()
        _log_pipeline_event(db, project_id, EVENT_JOB_FAILED, stage_key=stage_key, details={"job_id": str(job_id), "error": error_message})
        return

    project.autopilot_failure_count = (project.autopilot_failure_count or 0) + 1
    if project.autopilot_failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
        now = datetime.utcnow()
        project.autopilot_enabled = False
        project.autopilot_lock_until = now + timedelta(minutes=CIRCUIT_BREAKER_LOCK_MINUTES)
        project.autopilot_paused_reason = "Circuit breaker: repeated failures"
        _log_pipeline_event(
            db, project_id, EVENT_CIRCUIT_BREAKER,
            stage_key=stage_key,
            details={"error": error_message or "repeated failures"},
        )
        db.commit()
        _log_pipeline_event(db, project_id, EVENT_JOB_FAILED, stage_key=stage_key, details={"job_id": str(job_id), "error": error_message})
        return

    # Rework path: TEST or DEFECT_VALIDATION failed -> back to BUILD (defect cycle)
    if stage in (Stage.TEST, Stage.DEFECT_VALIDATION):
        cap = _get_defect_cycle_cap(db)
        project.defect_cycle_count = (project.defect_cycle_count or 0) + 1
        if project.defect_cycle_count > cap:
            set_project_needs_review(
                db, project_id,
                reason=f"Defect cycle cap ({cap}) reached. Requires admin review.",
                metadata={"stage": stage.value, "job_id": str(job_id), "defect_cycle_count": project.defect_cycle_count},
                actor_user_id=None,
            )
            db.commit()
            _log_pipeline_event(
                db, project_id, EVENT_JOB_FAILED,
                stage_key=stage_key,
                details={"job_id": str(job_id), "error": error_message, "defect_cycle_cap_reached": True},
            )
            return
        # Mark this stage as complete (rework) so pipeline can proceed to BUILD
        if row:
            row.status = "complete"
            row.last_error = None
        transition_project_stage(
            db, project_id,
            from_stage=stage,
            to_stage=Stage.BUILD,
            reason="rework",
            metadata={"job_id": str(job_id), "defect_cycle_count": project.defect_cycle_count},
            actor_user_id=None,
        )
        db.commit()
        _log_pipeline_event(
            db, project_id, EVENT_JOB_FAILED,
            stage_key=stage_key,
            details={"job_id": str(job_id), "error": error_message, "rework_to_build": True, "defect_cycle_count": project.defect_cycle_count},
        )
        auto_advance(db, project_id, trigger_source="job_failure_rework")
        return

    db.commit()
    _log_pipeline_event(
        db, project_id, EVENT_JOB_FAILED,
        stage_key=stage_key,
        details={"job_id": str(job_id), "error": error_message},
    )


def _get_decision_policies(db: Session) -> Dict[str, Any]:
    """Read decision_policies_json (defaults for reminder cadence, max_reminders, min_scope_percent)."""
    from app.services.config_service import get_config
    config = get_config(db, "decision_policies_json")
    if config and isinstance(config.value_json, dict):
        return config.value_json
    return {
        "reminder_cadence_hours": 24,
        "max_reminders": 10,
        "min_scope_percent": 80,
    }


def run_onboarding_reminders_and_hold(db: Session, max_projects: int = 30) -> int:
    """
    Send onboarding reminders every reminder_cadence_hours for incomplete onboarding.
    After max_reminders, set project to HOLD with message.
    Returns number of projects processed (reminder sent or hold applied).
    """
    policies = _get_decision_policies(db)
    cadence_hours = int(policies.get("reminder_cadence_hours", 24))
    max_reminders = int(policies.get("max_reminders", 10))
    min_scope_percent = int(policies.get("min_scope_percent", 80))
    cadence_delta = timedelta(hours=cadence_hours)
    now = datetime.utcnow()

    projects = (
        db.query(Project)
        .join(OnboardingData, OnboardingData.project_id == Project.id)
        .filter(
            Project.status == ProjectStatus.ACTIVE,
            Project.current_stage == Stage.ONBOARDING,
            OnboardingData.auto_reminder_enabled == True,
            OnboardingData.reminder_count < max_reminders,
        )
        .limit(max_projects)
        .all()
    )
    count = 0
    for project in projects:
        try:
            ob = db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
            if not ob:
                continue
            # Incomplete: not submitted or completion below min_scope
            if ob.submitted_at is not None:
                continue
            if (ob.completion_percentage or 0) >= min_scope_percent:
                continue
            # Cadence: last reminder sent at least cadence_hours ago (or never)
            last_sent = ob.last_reminder_sent or ob.updated_at or ob.created_at
            if last_sent and (now - last_sent) < cadence_delta:
                continue

            # Send reminder
            to_emails = []
            if getattr(project, "client_emails", None) and isinstance(project.client_emails, list):
                to_emails = [e for e in project.client_emails if isinstance(e, str) and e.strip()]
            if not to_emails and getattr(project, "client_email_ids", None):
                to_emails = [e.strip() for e in str(project.client_email_ids).split(",") if e.strip()]
            if not to_emails:
                continue

            from app.services.email_service import send_client_reminder_email
            message = (
                "Your project onboarding is incomplete. Please complete the required fields so we can proceed. "
                f"We have sent you {ob.reminder_count + 1} reminder(s)."
            )
            subject = f"Reminder: Complete onboarding for {project.title}"
            send_client_reminder_email(
                to_emails, subject, message, project.title, "Delivery Pipeline", return_details=False
            )
            ob.reminder_count = (ob.reminder_count or 0) + 1
            ob.last_reminder_sent = now
            ob.next_reminder_at = now + cadence_delta
            db.add(
                ClientReminder(
                    project_id=project.id,
                    recipient_email=to_emails[0] if to_emails else "",
                    reminder_type="onboarding_incomplete",
                    message=message,
                )
            )
            db.add(
                AuditLog(
                    project_id=project.id,
                    actor_user_id=None,
                    action="REMINDER_SENT",
                    payload_json={
                        "reminder_count": ob.reminder_count,
                        "max_reminders": max_reminders,
                        "stage": "onboarding",
                    },
                )
            )
            db.commit()
            count += 1

            if ob.reminder_count >= max_reminders:
                hold_message = "Awaiting client response. We attempted to contact you 10 times."
                if max_reminders != 10:
                    hold_message = f"Awaiting client response. We attempted to contact you {max_reminders} times."
                set_project_hold(
                    db, project.id,
                    reason=hold_message,
                    metadata={"reminder_count": ob.reminder_count, "source": "onboarding_reminders"},
                    actor_user_id=None,
                )
        except Exception as e:
            logger.warning("Onboarding reminder project %s: %s", project.id, e)
            db.rollback()
    return count


def run_onboarding_idle_nudge(db: Session, max_projects: int = 20) -> int:
    """
    In-app nudge when no onboarding update for idle_minutes and still incomplete.
    If idleness_counts_toward_reminders is True, increment reminder_count (counts toward 10).
    """
    policies = _get_decision_policies(db)
    idle_minutes = int(policies.get("idle_minutes", 30))
    count_toward_reminders = bool(policies.get("idleness_counts_toward_reminders", False))
    idle_delta = timedelta(minutes=idle_minutes)
    now = datetime.utcnow()
    cutoff = now - idle_delta

    # Projects in ONBOARDING, incomplete, last content update older than idle_minutes
    q = (
        db.query(Project)
        .join(OnboardingData, OnboardingData.project_id == Project.id)
        .filter(
            Project.status == ProjectStatus.ACTIVE,
            Project.current_stage == Stage.ONBOARDING,
            (OnboardingData.completion_percentage or 0) < 100,
            OnboardingData.submitted_at.is_(None),
        )
        .limit(max_projects)
    )
    from sqlalchemy.sql import func
    last_update = func.coalesce(OnboardingData.last_content_update_at, OnboardingData.updated_at)
    q = q.filter(last_update < cutoff)
    projects = q.all()

    count = 0
    for project in projects:
        try:
            ob = db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
            if not ob:
                continue
            last_update_val = getattr(ob, "last_content_update_at", None) or ob.updated_at or ob.created_at
            if not last_update_val or (now - last_update_val) < idle_delta:
                continue
            # Avoid nudge spam: last ONBOARDING_IDLE_NUDGE for this project within idle_delta?
            last_nudge = (
                db.query(AuditLog)
                .filter(
                    AuditLog.project_id == project.id,
                    AuditLog.action == "ONBOARDING_IDLE_NUDGE",
                )
                .order_by(AuditLog.created_at.desc())
                .first()
            )
            if last_nudge and (now - last_nudge.created_at) < idle_delta:
                continue

            # Notify consultant or manager (in-app)
            recipient_id = project.consultant_user_id
            if not recipient_id:
                manager = db.query(User).filter(User.role == Role.MANAGER).first()
                recipient_id = manager.id if manager else None
            if recipient_id:
                db.add(
                    Notification(
                        user_id=recipient_id,
                        project_id=project.id,
                        type="ONBOARDING_IDLE_NUDGE",
                        message=f"Client has not updated onboarding for {idle_minutes} minutes. Project: {project.title}.",
                        is_read=False,
                    )
                )
            db.add(
                AuditLog(
                    project_id=project.id,
                    actor_user_id=None,
                    action="ONBOARDING_IDLE_NUDGE",
                    payload_json={
                        "idle_minutes": idle_minutes,
                        "counts_toward_reminders": count_toward_reminders,
                    },
                )
            )
            if count_toward_reminders:
                ob.reminder_count = (ob.reminder_count or 0) + 1
                ob.last_reminder_sent = now
            db.commit()
            count += 1
        except Exception as e:
            logger.warning("Onboarding idle nudge project %s: %s", project.id, e)
            db.rollback()
    return count
