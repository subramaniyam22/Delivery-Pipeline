"""
Auto-assignment job: assign Consultant, Builder, Tester by workload/skills/SLA.
Idempotent unless force=true; updates assignment_rationale_json and active_assignments_count.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Project, ProjectStageState, User, PipelineEvent
from app.models import Role
from app.services.contract_service import create_or_update_contract, get_contract
from app.services.assignment_engine import rank_candidates
from app.agents.role_assignment_agent import rerank_candidates
from app.pipeline.stages import STAGE_TO_KEY

logger = logging.getLogger(__name__)

AUTO_ASSIGN_RATE_LIMIT_MINUTES = 5
ROLES_TO_ASSIGN = [(Role.CONSULTANT, "consultant", "consultant_user_id"), (Role.BUILDER, "builder", "builder_user_id"), (Role.TESTER, "tester", "tester_user_id")]


def _dec_user_assignment_count(db: Session, user_id: Optional[UUID]) -> None:
    if not user_id:
        return
    u = db.query(User).filter(User.id == user_id).first()
    if u and getattr(u, "active_assignments_count", 0) > 0:
        u.active_assignments_count = (u.active_assignments_count or 0) - 1


def _inc_user_assignment_count(db: Session, user_id: Optional[UUID]) -> None:
    if not user_id:
        return
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.active_assignments_count = (getattr(u, "active_assignments_count", 0) or 0) + 1


def run_auto_assignment(project_id: UUID, force: bool = False, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Load project + contract; if already fully assigned and not force, skip.
    Score and pick best candidate per role; persist assignments, rationale, update counts.
    Emit AUTO_ASSIGNED, mark 2_assignment complete, trigger auto_advance.
    Returns dict with assigned, blocked_reasons, rationale.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        project = session.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"status": "error", "error": "Project not found"}
        contract = get_contract(session, project_id)
        if not contract:
            try:
                create_or_update_contract(session, project_id, source="system:auto_assign")
                contract = get_contract(session, project_id)
            except Exception:
                contract = {}
        already_consultant = project.consultant_user_id
        already_builder = project.builder_user_id
        already_tester = project.tester_user_id
        if not force and already_consultant and already_builder and already_tester:
            return {"status": "skipped", "message": "Already fully assigned"}
        rationale = dict(getattr(project, "assignment_rationale_json", None) or {})
        run_at = datetime.utcnow()
        if not force and rationale.get("run_at"):
            try:
                last = datetime.fromisoformat(str(rationale["run_at"]).replace("Z", "+00:00"))
                if (run_at - last).total_seconds() < AUTO_ASSIGN_RATE_LIMIT_MINUTES * 60:
                    return {"status": "skipped", "message": "Rate limited"}
            except Exception:
                pass
        rationale["run_at"] = run_at.isoformat()
        rationale["consultant"] = rationale.get("consultant") or {}
        rationale["builder"] = rationale.get("builder") or {}
        rationale["tester"] = rationale.get("tester") or {}
        blocked: List[str] = []
        project_summary = f"{project.title} | {project.client_name} | priority={project.priority}"
        high_risk = str(project.priority or "").upper() in ("HIGH", "CRITICAL") or bool(project.is_delayed)
        for role_enum, role_key, project_attr in ROLES_TO_ASSIGN:
            current_id = getattr(project, project_attr)
            if not force and current_id:
                continue
            ranked = rank_candidates(session, project, contract, role_enum)
            if not ranked:
                blocked.append(f"No available {role_key}")
                rationale[role_key] = {"user_id": None, "reasons": [f"No eligible {role_key}"], "score": 0.0}
                continue
            candidates = [{"user_id": str(u.id), "name": u.name, "score": s, "reasons": r} for u, s, r in ranked]
            if high_risk or (len(ranked) >= 2 and abs(ranked[0][1] - ranked[1][1]) < 0.05):
                try:
                    reranked = rerank_candidates(role_key, candidates, project_summary, use_ai=True)
                    by_id = {str(u.id): (u, s, r) for u, s, r in ranked}
                    seen = {d.get("user_id") for d in reranked}
                    ordered = [by_id[d["user_id"]] for d in reranked if d.get("user_id") in by_id]
                    ordered += [(u, s, r) for u, s, r in ranked if str(u.id) not in seen]
                    ranked = ordered
                except Exception:
                    pass
            chosen_user = None
            for u, score, reasons in ranked:
                cap = getattr(u, "capacity", None) or 1
                active = getattr(u, "active_assignments_count", None) or 0
                if active < cap:
                    chosen_user = u
                    break
            if not chosen_user:
                blocked.append(f"No {role_key} with capacity")
                rationale[role_key] = {"user_id": None, "reasons": ["All at capacity"], "score": 0.0}
                continue
            old_id = getattr(project, project_attr)
            _dec_user_assignment_count(session, old_id)
            setattr(project, project_attr, chosen_user.id)
            _inc_user_assignment_count(session, chosen_user.id)
            chosen_score, chosen_reasons = 0.0, []
            for u, s, r in ranked:
                if u.id == chosen_user.id:
                    chosen_score, chosen_reasons = s, r
                    break
            rationale[role_key] = {"user_id": str(chosen_user.id), "reasons": chosen_reasons, "score": round(chosen_score, 2), "auto_assigned": True}
        project.assignment_rationale_json = rationale
        session.add(PipelineEvent(project_id=project_id, stage_key="2_assignment", event_type="AUTO_ASSIGNED", details_json={"rationale": rationale}))
        if blocked:
            row = session.query(ProjectStageState).filter(ProjectStageState.project_id == project_id, ProjectStageState.stage_key == "2_assignment").first()
            if row:
                row.status = "blocked"
                row.blocked_reasons_json = blocked
                row.required_actions_json = [f"Assign: {b}" for b in blocked]
            session.commit()
            if close:
                session.close()
            return {"status": "partial", "assigned": not all(b for b in blocked), "blocked_reasons": blocked, "rationale": rationale}
        create_or_update_contract(session, project_id, source="system:auto_assigned")
        row = session.query(ProjectStageState).filter(ProjectStageState.project_id == project_id, ProjectStageState.stage_key == "2_assignment").first()
        if row:
            row.status = "complete"
            row.blocked_reasons_json = []
            row.required_actions_json = []
        session.commit()
        try:
            from app.services.pipeline_orchestrator import auto_advance
            auto_advance(session, project_id, trigger_source="auto_assignment")
        except Exception as e:
            logger.warning("auto_advance after auto_assignment failed: %s", e)
        if close:
            session.close()
        return {"status": "ok", "rationale": rationale}
    except Exception as e:
        logger.exception("run_auto_assignment failed: %s", e)
        if session:
            try:
                row = session.query(ProjectStageState).filter(ProjectStageState.project_id == project_id, ProjectStageState.stage_key == "2_assignment").first()
                if row:
                    row.status = "blocked"
                    row.blocked_reasons_json = [str(e)]
                session.commit()
            except Exception:
                pass
        if close and session:
            session.close()
        return {"status": "error", "error": str(e)}
    finally:
        if close and session:
            session.close()
