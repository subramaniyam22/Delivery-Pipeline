"""Pipeline status and autopilot control API. Admin/Manager for write endpoints."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user
from app.models import Project, User
from app.rbac import check_full_access
from app.services.pipeline_orchestrator import (
    PipelineStatus,
    SafetyFlags,
    StageStateView,
    auto_advance,
    evaluate_project,
)

router = APIRouter(tags=["pipeline"])


def _role_in_approver_roles(role_value: str, approver_roles: List[str]) -> bool:
    """Check if user role (lowercase) is in gate approver_roles (e.g. admin, manager, qa)."""
    if not approver_roles:
        return False
    r = (role_value or "").lower()
    return r in [x.lower() for x in approver_roles]


def _serialize_status(s: PipelineStatus) -> Dict[str, Any]:
    return {
        "project_id": str(s.project_id),
        "autopilot_enabled": s.autopilot_enabled,
        "autopilot_mode": s.autopilot_mode,
        "current_stage_key": s.current_stage_key,
        "stage_states": [
            {
                "stage_key": v.stage_key,
                "status": v.status,
                "blocked_reasons": v.blocked_reasons,
                "required_actions": v.required_actions,
                "last_job_id": str(v.last_job_id) if v.last_job_id else None,
                "updated_at": v.updated_at.isoformat() if v.updated_at else None,
            }
            for v in s.stage_states
        ],
        "next_ready_stages": s.next_ready_stages,
        "blocked_summary": s.blocked_summary,
        "awaiting_approval_stage_key": s.awaiting_approval_stage_key,
        "safety_flags": {
            "ambiguous_next_stage": s.safety_flags.ambiguous_next_stage,
            "circuit_breaker": s.safety_flags.circuit_breaker,
            "cooldown_active": s.safety_flags.cooldown_active,
        },
        "pending_approvals": [
            {
                "stage_key": p.stage_key,
                "id": str(p.id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "reasons": p.reasons,
                "approver_roles": p.approver_roles,
            }
            for p in (s.pending_approvals or [])
        ],
    }


class PauseBody(BaseModel):
    reason: Optional[str] = None


class ResumeBody(BaseModel):
    reset_failure_count: bool = True


@router.get("/{project_id}/pipeline/status")
def get_pipeline_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return pipeline status (evaluate only, no enqueue)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    status = evaluate_project(db, project_id)
    return _serialize_status(status)


@router.post("/{project_id}/pipeline/advance")
def pipeline_advance(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin/Manager only. Run auto_advance with trigger_source=manual_advance."""
    if not check_full_access(current_user.role):
        raise HTTPException(status_code=403, detail="Admin or Manager required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    status = auto_advance(db, project_id, trigger_source="manual_advance")
    return _serialize_status(status)


@router.post("/{project_id}/pipeline/pause")
def pipeline_pause(
    project_id: UUID,
    body: Optional[PauseBody] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin/Manager only. Set autopilot_enabled=false and optional paused reason."""
    if not check_full_access(current_user.role):
        raise HTTPException(status_code=403, detail="Admin or Manager required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.autopilot_enabled = False
    project.autopilot_paused_reason = (body.reason if body else None) or "Paused by admin"
    db.commit()
    status = evaluate_project(db, project_id)
    return _serialize_status(status)


@router.post("/{project_id}/pipeline/resume")
def pipeline_resume(
    project_id: UUID,
    body: Optional[ResumeBody] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin/Manager only. Set autopilot_enabled=true, clear reason, optional reset failure_count, then auto_advance."""
    if not check_full_access(current_user.role):
        raise HTTPException(status_code=403, detail="Admin or Manager required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.autopilot_enabled = True
    project.autopilot_paused_reason = None
    if body is None or body.reset_failure_count:
        project.autopilot_failure_count = 0
        project.autopilot_lock_until = None
    db.commit()
    status = auto_advance(db, project_id, trigger_source="manual_resume")
    return _serialize_status(status)


# ---------- Approval endpoints ----------

# ---------- Contract API (read-only) ----------

@router.get("/{project_id}/contract")
def get_project_contract(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the delivery contract for the project (read-only). Lazy init if missing."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    from app.services.contract_service import get_contract
    contract = get_contract(db, project_id)
    if contract is None:
        raise HTTPException(status_code=503, detail="Contract unavailable (build failed)")
    return contract


@router.get("/{project_id}/contract/versions")
def get_project_contract_versions(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return contract version history (version, updated_at). Read-only."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    from app.models import ProjectContract
    row = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    if not row:
        return []
    audit = (row.contract_json.get("meta") or {}).get("audit") or []
    return [
        {"version": row.version, "updated_at": row.updated_at.isoformat() if row.updated_at else None},
        *[{"event": e.get("event"), "at": e.get("at"), "by": e.get("by")} for e in audit[-20:]],
    ]


@router.get("/{project_id}/pipeline/approvals")
def list_pipeline_approvals(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return all approvals for the project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    from app.models import StageApproval
    rows = db.query(StageApproval).filter(StageApproval.project_id == project_id).order_by(StageApproval.created_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "stage_key": r.stage_key,
            "status": r.status,
            "reviewer_user_id": str(r.reviewer_user_id) if r.reviewer_user_id else None,
            "reviewer_role": r.reviewer_role,
            "comment": r.comment,
            "gate_snapshot": r.gate_snapshot_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


class ApproveBody(BaseModel):
    stage_key: str
    comment: Optional[str] = None


class RejectBody(BaseModel):
    stage_key: str
    comment: Optional[str] = None


@router.post("/{project_id}/pipeline/approve")
def pipeline_approve(
    project_id: UUID,
    body: ApproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve a pending stage. User role must be in gate approver_roles."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models import StageApproval, ProjectStageState
    from app.services.hitl_service import (
        get_global_hitl_gates,
        get_project_overrides,
        resolve_gate_for_stage,
        compute_stage_inputs_fingerprint,
    )

    global_gates = get_global_hitl_gates(db)
    project_overrides = get_project_overrides(db, project_id)
    gate_rule = resolve_gate_for_stage(body.stage_key, global_gates, project_overrides)
    approver_roles = gate_rule.get("approver_roles") or ["admin", "manager"]
    if not _role_in_approver_roles(current_user.role.value, approver_roles):
        raise HTTPException(status_code=403, detail="Your role is not allowed to approve this stage")

    pending = (
        db.query(StageApproval)
        .filter(
            StageApproval.project_id == project_id,
            StageApproval.stage_key == body.stage_key,
            StageApproval.status == "pending",
        )
        .first()
    )
    if not pending:
        raise HTTPException(status_code=409, detail="No pending approval")

    current_fp = compute_stage_inputs_fingerprint(db, project_id, body.stage_key)
    if current_fp != pending.inputs_fingerprint:
        raise HTTPException(status_code=409, detail="Approval is stale; re-request approval")

    pending.status = "approved"
    pending.reviewer_user_id = current_user.id
    pending.reviewer_role = current_user.role.value
    pending.comment = body.comment
    pending.updated_at = datetime.utcnow()

    row = (
        db.query(ProjectStageState)
        .filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == body.stage_key,
        )
        .first()
    )
    if row:
        row.status = "ready"
        row.blocked_reasons_json = []
        row.required_actions_json = []
        row.updated_at = datetime.utcnow()

    db.commit()
    try:
        from app.services.contract_service import create_or_update_contract
        create_or_update_contract(db, project_id, source="user:approval_granted")
    except Exception:
        pass
    status = auto_advance(db, project_id, trigger_source="approval_granted")
    return _serialize_status(status)


@router.post("/{project_id}/pipeline/reject")
def pipeline_reject(
    project_id: UUID,
    body: RejectBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a pending stage. User role must be in gate approver_roles."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models import StageApproval, ProjectStageState
    from app.services.hitl_service import (
        get_global_hitl_gates,
        get_project_overrides,
        resolve_gate_for_stage,
    )

    global_gates = get_global_hitl_gates(db)
    project_overrides = get_project_overrides(db, project_id)
    gate_rule = resolve_gate_for_stage(body.stage_key, global_gates, project_overrides)
    approver_roles = gate_rule.get("approver_roles") or ["admin", "manager"]
    if not _role_in_approver_roles(current_user.role.value, approver_roles):
        raise HTTPException(status_code=403, detail="Your role is not allowed to reject this stage")

    pending = (
        db.query(StageApproval)
        .filter(
            StageApproval.project_id == project_id,
            StageApproval.stage_key == body.stage_key,
            StageApproval.status == "pending",
        )
        .first()
    )
    if not pending:
        raise HTTPException(status_code=409, detail="No pending approval")

    pending.status = "rejected"
    pending.reviewer_user_id = current_user.id
    pending.reviewer_role = current_user.role.value
    pending.comment = body.comment
    pending.updated_at = datetime.utcnow()

    row = (
        db.query(ProjectStageState)
        .filter(
            ProjectStageState.project_id == project_id,
            ProjectStageState.stage_key == body.stage_key,
        )
        .first()
    )
    if row:
        row.status = "blocked"
        reasons = list(row.blocked_reasons_json or [])
        reasons.append(f"Rejected: {body.comment or 'No comment'}")
        row.blocked_reasons_json = reasons
        row.required_actions_json = ["Fix issues and request approval again"]
        row.updated_at = datetime.utcnow()

    project.autopilot_paused_reason = "Approval rejected"
    db.commit()
    status = evaluate_project(db, project_id)
    return _serialize_status(status)
