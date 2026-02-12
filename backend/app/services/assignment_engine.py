"""
Assignment scoring engine: deterministic + configurable weights.
Scores users for a project/role using skill match, workload, availability, performance, SLA urgency.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models import Project, User
from app.models import Role


# Weights (configurable later via admin config)
WEIGHT_SKILL = 0.35
WEIGHT_WORKLOAD = 0.25
WEIGHT_AVAILABILITY = 0.15
WEIGHT_PERFORMANCE = 0.15
WEIGHT_SLA_URGENCY = 0.10


def _project_needs_skills(project: Project, contract: Optional[Dict[str, Any]], role: Role) -> List[str]:
    """Derive required/desired skills from project, contract, template category."""
    needs: List[str] = []
    if project.features_json and isinstance(project.features_json, dict):
        needs.extend(k for k in (project.features_json.keys() if isinstance(project.features_json, dict) else []))
    if project.features_json and isinstance(project.features_json, list):
        needs.extend(str(x).lower() for x in project.features_json)
    if contract:
        tpl = contract.get("template") or {}
        cat = tpl.get("category") or contract.get("onboarding", {}).get("category")
        if cat:
            needs.append(str(cat).lower())
        ob = contract.get("onboarding") or {}
        if isinstance(ob, dict):
            for k in ("features", "feature_tags"):
                v = ob.get(k)
                if isinstance(v, list):
                    needs.extend(str(x).lower() for x in v)
    if not needs and role == Role.BUILDER:
        needs = ["react", "property_management", "seo"]
    if not needs and role == Role.TESTER:
        needs = ["qa", "accessibility", "testing"]
    if not needs and role == Role.CONSULTANT:
        needs = ["property_management", "client_communication"]
    return list(dict.fromkeys(needs))


def _skill_match_score(user_skills: List[str], need_skills: List[str]) -> float:
    if not need_skills:
        return 0.7
    user_set = set(s.lower().strip() for s in (user_skills or []) if s)
    need_set = set(s.lower().strip() for s in need_skills if s)
    if not need_set:
        return 0.7
    overlap = len(user_set & need_set) / len(need_set)
    return min(1.0, overlap + 0.2)


def _workload_score(active_count: int, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (active_count / capacity)))


def _availability_score(status: Optional[str]) -> float:
    s = (status or "available").strip().lower()
    if s == "available":
        return 1.0
    if s == "busy":
        return 0.5
    if s in ("out_of_office", "ooo", "leave"):
        return 0.0
    return 0.5


def _performance_score(score: Optional[float]) -> float:
    if score is None:
        return 0.7
    return max(0.0, min(1.0, float(score)))


def _sla_urgency_score(project: Project, contract: Optional[Dict[str, Any]]) -> float:
    """Higher urgency -> higher score (we favor available/capable users when SLA is tight)."""
    if project.priority and str(project.priority).upper() in ("HIGH", "CRITICAL"):
        return 0.9
    if project.is_delayed:
        return 0.85
    phase = (project.phase_deadlines or {}) if isinstance(project.phase_deadlines, dict) else {}
    if phase:
        return 0.6
    return 0.5


def score_user_for_project(
    user: User,
    project: Project,
    contract: Optional[Dict[str, Any]],
    role: Role,
) -> tuple[float, List[str]]:
    """
    Returns (score 0-1, list of reason strings for explainability).
    """
    reasons: List[str] = []
    need_skills = _project_needs_skills(project, contract, role)
    user_skills = getattr(user, "skills_json", None) or []
    if not isinstance(user_skills, list):
        user_skills = []
    skill = _skill_match_score(user_skills, need_skills)
    reasons.append(f"skill_match={skill:.2f}")
    active = getattr(user, "active_assignments_count", None) or 0
    cap = getattr(user, "capacity", None) or 1
    workload = _workload_score(active, cap)
    reasons.append(f"workload={workload:.2f}({active}/{cap})")
    avail = _availability_score(getattr(user, "availability_status", None))
    reasons.append(f"availability={avail:.2f}")
    perf = _performance_score(getattr(user, "performance_score", None))
    reasons.append(f"performance={perf:.2f}")
    sla = _sla_urgency_score(project, contract)
    reasons.append(f"sla_urgency={sla:.2f}")
    score = (
        WEIGHT_SKILL * skill
        + WEIGHT_WORKLOAD * workload
        + WEIGHT_AVAILABILITY * avail
        + WEIGHT_PERFORMANCE * perf
        + WEIGHT_SLA_URGENCY * sla
    )
    return max(0.0, min(1.0, score)), reasons


def get_eligible_users(
    db: Any,
    role: Role,
    exclude_ooo: bool = True,
) -> List[User]:
    """Users with this role, active, optionally exclude out_of_office."""
    q = db.query(User).filter(User.role == role, User.is_active == True, User.is_archived == False)
    users = q.all()
    if exclude_ooo:
        users = [u for u in users if (getattr(u, "availability_status", None) or "available").lower() != "out_of_office"]
    return users


def rank_candidates(
    db: Any,
    project: Project,
    contract: Optional[Dict[str, Any]],
    role: Role,
) -> List[tuple[User, float, List[str]]]:
    """Returns list of (user, score, reasons) sorted by score desc."""
    users = get_eligible_users(db, role)
    scored = []
    for u in users:
        score, reasons = score_user_for_project(u, project, contract, role)
        scored.append((u, score, reasons))
    scored.sort(key=lambda x: -x[1])
    return scored
