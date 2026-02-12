"""Blueprint critic: scorecard + hard checks + issues list."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from app.agents.prompts import get_llm
from app.agents.templates.prompts import CRITIC_SYSTEM, CRITIC_USER
from app.templates.quality_rubric import (
    critic_result_shape,
    run_hard_checks,
    local_heuristic_scores,
)
from app.utils.llm import invoke_llm

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    for start in ("```json", "```"):
        if text.startswith(start):
            text = text[len(start):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def critique_blueprint(blueprint_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run LLM critique + local hard-check verification. Combine into critic_result_shape.
    If LLM says pass but local hard-check fails, downgrade and add issues.
    """
    llm = get_llm(task="analysis")
    blueprint_str = json.dumps(blueprint_json, indent=2)
    prompt = CRITIC_SYSTEM + "\n\n" + CRITIC_USER.format(blueprint_json=blueprint_str)
    try:
        response = invoke_llm(llm, prompt)
        content = getattr(response, "content", response) if response else ""
        raw = _extract_json(content) if isinstance(content, str) else None
    except Exception as e:
        logger.warning("Critic LLM failed: %s", e)
        raw = None
    hard = run_hard_checks(blueprint_json)
    local_scores = local_heuristic_scores(blueprint_json)
    issues: List[Dict[str, Any]] = []
    if not hard.get("has_home"):
        issues.append({"severity": "blocker", "path": "pages", "message": "Missing home page", "fix_hint": "Add page with slug 'home'"})
    if not hard.get("has_contact_or_lead"):
        issues.append({"severity": "blocker", "path": "forms", "message": "Missing contact form or lead form", "fix_hint": "Add contact_form section or enable lead form"})
    if not hard.get("has_cta"):
        issues.append({"severity": "major", "path": "pages", "message": "No CTA section", "fix_hint": "Add cta_banner or hero with CTA"})
    if not hard.get("has_accessible_nav_labels"):
        issues.append({"severity": "major", "path": "navigation.items", "message": "Nav items need labels", "fix_hint": "Add label or ariaLabel to each item"})
    if not hard.get("mobile_first"):
        issues.append({"severity": "minor", "path": "constraints", "message": "mobile_first should be true", "fix_hint": "Set constraints.mobile_first to true"})
    if raw and not raw.get("error"):
        scorecard = raw.get("scorecard") or {}
        for k in ("conversion", "clarity", "accessibility_heuristics", "completeness", "consistency"):
            if k in scorecard:
                local_scores[k] = min(100, max(0, int(scorecard[k])))
        issues = raw.get("issues") or issues
        summary = raw.get("summary") or "Critique complete."
    else:
        summary = "Local heuristic critique only (LLM unavailable)."
    return critic_result_shape(
        scorecard=local_scores,
        hard_checks=hard,
        issues=issues,
        summary=summary,
    )
