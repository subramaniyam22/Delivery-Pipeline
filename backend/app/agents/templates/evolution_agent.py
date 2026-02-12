"""
Template evolution agent: propose improvements from metrics + feedback (Prompt 9).
Does NOT auto-apply; proposals are stored for human review.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Tag -> suggested blueprint change reason
TAG_TO_SUGGESTION = {
    "navigation_confusion": ("pages.home.sections.navigation.variant", "simplified", "Users found navigation confusing"),
    "design_clarity": ("pages.home.sections.hero.variant", "centered", "Improve design clarity with centered hero"),
    "mobile_issues": ("pages.home.sections", "reduce_count", "High mobile issues: fewer sections on home"),
    "accessibility": ("tokens.a11y", "enhance", "Repeated accessibility feedback"),
    "load_time": ("pages.home.sections.gallery_grid", "lazy", "Improve load time with lazy images"),
}

SENTIMENT_THRESHOLD = 3.5
DEFECT_RATE_HIGH = 3.0  # avg defects per project
PROPOSAL_RATE_LIMIT_WEEKS = 1


def propose_template_improvements(
    template_id: str,
    version: int,
    metrics: Dict[str, Any],
    recent_feedback: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Propose template improvements. Returns proposal_json for storage.
    Never auto-applies; caller stores as evolution proposal for review.
    """
    change_summary_parts: List[str] = []
    suggested_blueprint_changes: List[Dict[str, Any]] = []
    rationale_parts: List[str] = []

    avg_sentiment = (metrics or {}).get("avg_sentiment")
    avg_defects = (metrics or {}).get("avg_defects")
    tags_seen: Dict[str, int] = {}
    for f in recent_feedback or []:
        tags = f.get("tags_json") or f.get("tags") or []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str):
                    tags_seen[t] = tags_seen.get(t, 0) + 1

    # Low sentiment -> suggest general improvement
    if avg_sentiment is not None and avg_sentiment < SENTIMENT_THRESHOLD:
        rationale_parts.append(f"Average sentiment ({avg_sentiment}) below threshold ({SENTIMENT_THRESHOLD}).")
        change_summary_parts.append("Improve overall layout and clarity")

    # High defect rate -> suggest simplification
    if avg_defects is not None and avg_defects >= DEFECT_RATE_HIGH:
        rationale_parts.append(f"Defect rate ({avg_defects}) is high; suggest simpler layouts.")
        suggested_blueprint_changes.append({
            "path": "pages.0.sections",
            "from": "current",
            "to": "reduce_sections",
            "reason": "High defect rate: reduce section count on home for maintainability",
        })

    # Tag-based suggestions
    for tag, count in tags_seen.items():
        if count < 2:
            continue
        if tag in TAG_TO_SUGGESTION:
            path, to_val, reason = TAG_TO_SUGGESTION[tag]
            suggested_blueprint_changes.append({
                "path": path,
                "from": "current",
                "to": to_val,
                "reason": reason,
            })
            change_summary_parts.append(reason)
            rationale_parts.append(f"Repeated feedback tag '{tag}' ({count} times).")

    if not change_summary_parts and not suggested_blueprint_changes:
        return {
            "new_version": version + 1,
            "change_summary": "No changes suggested; metrics within acceptable range.",
            "rationale": "No actionable feedback or thresholds not met.",
            "suggested_blueprint_changes": [],
            "expected_impact": {},
        }

    change_summary = "; ".join(change_summary_parts) if change_summary_parts else "Blueprint refinements suggested from feedback."
    rationale = " ".join(rationale_parts) if rationale_parts else "Based on aggregated sentiment and delivery outcomes."

    expected_impact: Dict[str, str] = {}
    if avg_sentiment is not None and avg_sentiment < SENTIMENT_THRESHOLD:
        expected_impact["sentiment"] = "+0.3"
    if tags_seen.get("accessibility"):
        expected_impact["a11y"] = "+5"
    if avg_defects is not None and avg_defects >= DEFECT_RATE_HIGH:
        expected_impact["defects"] = "-20%"
    if "conversion" not in expected_impact and (metrics or {}).get("conversion_proxy") is not None:
        expected_impact["conversion"] = "+8%"

    return {
        "new_version": version + 1,
        "change_summary": change_summary,
        "rationale": rationale,
        "suggested_blueprint_changes": suggested_blueprint_changes,
        "expected_impact": expected_impact,
    }
