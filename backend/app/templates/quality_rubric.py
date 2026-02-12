"""
Template quality rubric: scoring categories (0-100) and hard checks for the Critic.
"""
from typing import Any, Dict, List

# Default thresholds (used until config wired in Prompt 6)
DEFAULT_THRESHOLDS = {
    "conversion": 75,
    "clarity": 75,
    "accessibility_heuristics": 80,
    "completeness": 80,
    "consistency": 75,
}


def run_hard_checks(blueprint: Dict[str, Any]) -> Dict[str, bool]:
    """Run hard checks; all must be True for pass."""
    out: Dict[str, bool] = {}
    pages = blueprint.get("pages") or []
    out["has_home"] = any(
        (p.get("slug") or "").strip().lower() == "home" or i == 0
        for i, p in enumerate(pages) if isinstance(p, dict)
    ) and len(pages) >= 1
    out["has_contact_or_lead"] = False
    lead = (blueprint.get("forms") or {}).get("lead")
    if isinstance(lead, dict) and lead.get("enabled"):
        out["has_contact_or_lead"] = True
    for p in pages:
        if not isinstance(p, dict):
            continue
        for s in (p.get("sections") or []):
            if isinstance(s, dict) and s.get("type") == "contact_form":
                out["has_contact_or_lead"] = True
                break
    out["has_cta"] = False
    for p in pages:
        if not isinstance(p, dict):
            continue
        for s in (p.get("sections") or []):
            if isinstance(s, dict) and s.get("type") in ("cta_banner", "hero"):
                out["has_cta"] = True
                break
        if out["has_cta"]:
            break
    nav = blueprint.get("navigation") or {}
    items = nav.get("items") or []
    out["has_accessible_nav_labels"] = all(
        isinstance(it, dict) and (it.get("label") or it.get("ariaLabel"))
        for it in items
    ) if items else True
    out["mobile_first"] = (blueprint.get("constraints") or {}).get("mobile_first") is True
    return out


def critic_result_shape(
    scorecard: Dict[str, int],
    hard_checks: Dict[str, bool],
    issues: List[Dict[str, Any]],
    summary: str,
) -> Dict[str, Any]:
    """Build critic output in required shape."""
    return {
        "scorecard": scorecard,
        "hard_checks": hard_checks,
        "issues": issues,
        "summary": summary,
    }


def local_heuristic_scores(blueprint: Dict[str, Any]) -> Dict[str, int]:
    """Local heuristic scoring 0-100 for each category (no LLM)."""
    scores = {"conversion": 50, "clarity": 50, "accessibility_heuristics": 50, "completeness": 50, "consistency": 50}
    hard = run_hard_checks(blueprint)
    if hard.get("has_home"):
        scores["completeness"] = min(100, scores["completeness"] + 15)
    if hard.get("has_contact_or_lead"):
        scores["conversion"] = min(100, scores["conversion"] + 20)
    if hard.get("has_cta"):
        scores["conversion"] = min(100, scores["conversion"] + 15)
    if hard.get("has_accessible_nav_labels"):
        scores["accessibility_heuristics"] = min(100, scores["accessibility_heuristics"] + 25)
    if hard.get("mobile_first"):
        scores["accessibility_heuristics"] = min(100, scores["accessibility_heuristics"] + 15)
    tokens = blueprint.get("tokens") or {}
    if tokens.get("colors") and tokens.get("typography"):
        scores["consistency"] = min(100, scores["consistency"] + 25)
    pages = blueprint.get("pages") or []
    if len(pages) >= 2:
        scores["completeness"] = min(100, scores["completeness"] + 10)
    return scores
