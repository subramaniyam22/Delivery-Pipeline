"""Blueprint generator: produces schema-conforming blueprint_json from template + demo context."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

from app.agents.prompts import get_llm
from app.agents.templates.prompts import GENERATOR_SYSTEM, GENERATOR_USER
from app.models import TemplateRegistry
from app.templates.blueprint_schema_v1 import validate_blueprint_v1
from app.utils.llm import invoke_llm

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Dict[str, Any] | None:
    """Extract JSON object from LLM output (may be wrapped in markdown)."""
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


def generate_blueprint(template: TemplateRegistry, demo_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate blueprint_json for the template. Returns validated blueprint or raises.
    On schema validation failure, does one repair pass via refiner with errors; if still invalid, raises.
    """
    from app.agents.templates.refiner import refine_blueprint
    name = template.name or "Untitled"
    category = template.category or "general"
    style = template.style or "modern"
    tags = list(template.feature_tags_json or []) if hasattr(template, "feature_tags_json") else []
    required = list(template.required_inputs_json or []) if hasattr(template, "required_inputs_json") else []
    demo_str = json.dumps(demo_context or {}, default=str)
    user_prompt = GENERATOR_USER.format(
        name=name,
        category=category,
        style=style,
        tags=json.dumps(tags),
        required_inputs=json.dumps(required),
        demo_context=demo_str,
    )
    llm = get_llm(task="analysis")
    try:
        response = invoke_llm(llm, GENERATOR_SYSTEM + "\n\n" + user_prompt)
        content = getattr(response, "content", response) if response else ""
        if isinstance(content, str):
            raw = _extract_json(content)
        else:
            raw = None
        if not raw:
            raise ValueError("Generator did not return valid JSON")
        if raw.get("error"):
            raise ValueError(raw.get("error", "Generator returned error"))
        raw.setdefault("schema_version", 1)
        meta = raw.get("meta") or {}
        meta.setdefault("generated_at", datetime.utcnow().isoformat() + "Z")
        meta.setdefault("generator", {"model": "gpt-4", "temperature": 0.7})
        raw["meta"] = meta
        valid, errors = validate_blueprint_v1(raw)
        if valid:
            return raw
        # One repair pass
        repair_issues = [{"path": e.split(":")[0] if ":" in e else "root", "message": e, "fix_hint": e} for e in errors]
        repaired = refine_blueprint(raw, repair_issues)
        if repaired:
            valid2, errors2 = validate_blueprint_v1(repaired)
            if valid2:
                return repaired
            raise ValueError(f"Blueprint still invalid after repair: {errors2}")
        raise ValueError(f"Blueprint invalid: {errors}")
    except Exception as e:
        logger.exception("generate_blueprint failed: %s", e)
        raise
