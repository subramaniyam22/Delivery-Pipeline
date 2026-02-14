"""Copy agent: generates and validates template copy for accuracy and relevancy (real estate / property management)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from app.agents.prompts import get_llm
from app.utils.llm import invoke_llm

logger = logging.getLogger(__name__)

COPY_VALIDATOR_SYSTEM = """You are a copy quality validator for real estate and property management website templates.
You receive a blueprint JSON (pages with sections and content_slots) and validate:
1. Accuracy: copy is factually plausible for the industry (no made-up addresses, realistic claims).
2. Relevancy: headlines, body text, and CTAs are relevant to real estate or property management.
3. Consistency: tone and terminology are consistent across pages.
4. No lorem ipsum or placeholder gibberish.

You output ONLY valid JSON in this shape:
{
  "passed": true/false,
  "score": 0-100,
  "issues": [ { "path": "e.g. pages[0].sections[1].content_slots.headline", "message": "...", "suggestion": "..." } ],
  "summary": "One paragraph summary."
}
If you cannot comply, return {"error": "description"}."""

COPY_VALIDATOR_USER = """Validate the copy in this blueprint for real estate/property management accuracy and relevancy.
Industry context: {industry}

Blueprint JSON:
{blueprint_json}

Output ONLY the JSON object (passed, score, issues, summary)."""


def validate_copy(blueprint_json: Dict[str, Any], industry: str = "real_estate") -> Dict[str, Any]:
    """Run copy validation on blueprint. Returns { passed, score, issues, summary } or { error }."""
    try:
        llm = get_llm(task="analysis")
        user = COPY_VALIDATOR_USER.format(
            industry=industry,
            blueprint_json=json.dumps(blueprint_json, default=str)[:12000],
        )
        response = invoke_llm(llm, COPY_VALIDATOR_SYSTEM + "\n\n" + user)
        content = getattr(response, "content", response) or ""
        if isinstance(content, str):
            for start in ("```json", "```"):
                if content.startswith(start):
                    content = content[len(start):].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            out = json.loads(content)
        else:
            out = {}
        if out.get("error"):
            return {"passed": False, "score": 0, "issues": [], "summary": out.get("error", "Error")}
        out.setdefault("passed", False)
        out.setdefault("score", 0)
        out.setdefault("issues", [])
        out.setdefault("summary", "")
        return out
    except Exception as e:
        logger.exception("copy validation failed: %s", e)
        return {"passed": False, "score": 0, "issues": [], "summary": str(e), "error": str(e)}
