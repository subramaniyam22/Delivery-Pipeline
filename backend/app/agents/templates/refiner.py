"""Blueprint refiner: fixes issues and returns improved blueprint."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from app.agents.prompts import get_llm
from app.agents.templates.prompts import REFINER_SYSTEM, REFINER_USER
from app.templates.blueprint_schema_v1 import validate_blueprint_v1
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


def refine_blueprint(blueprint_json: Dict[str, Any], critic_issues: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """
    Return improved blueprint fixing the given issues. Validates after refine.
    If invalid, adds schema errors to issues and retries once (caller can pass back).
    """
    if not critic_issues:
        return blueprint_json
    issues_str = json.dumps(critic_issues, indent=2)
    blueprint_str = json.dumps(blueprint_json, indent=2)
    prompt = REFINER_SYSTEM + "\n\n" + REFINER_USER.format(blueprint_json=blueprint_str, issues_json=issues_str)
    llm = get_llm(task="analysis")
    try:
        response = invoke_llm(llm, prompt)
        content = getattr(response, "content", response) if response else ""
        raw = _extract_json(content) if isinstance(content, str) else None
        if not raw or raw.get("error"):
            return None
        valid, errors = validate_blueprint_v1(raw)
        if valid:
            return raw
        # Retry once with schema errors
        extra = [{"path": e.split(":")[0], "message": e, "fix_hint": e} for e in errors]
        retry_prompt = REFINER_USER.format(blueprint_json=json.dumps(raw), issues_json=json.dumps(extra))
        response2 = invoke_llm(llm, REFINER_SYSTEM + "\n\n" + retry_prompt)
        content2 = getattr(response2, "content", response2) if response2 else ""
        raw2 = _extract_json(content2) if isinstance(content2, str) else None
        if raw2 and not raw2.get("error"):
            valid2, _ = validate_blueprint_v1(raw2)
            if valid2:
                return raw2
        return raw  # return last attempt even if invalid so caller can see
    except Exception as e:
        logger.warning("refine_blueprint failed: %s", e)
        return None
