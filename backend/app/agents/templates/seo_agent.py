"""SEO agent: validates SEO relevancy of template (meta titles, descriptions, headings)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.agents.prompts import get_llm
from app.utils.llm import invoke_llm

logger = logging.getLogger(__name__)

SEO_VALIDATOR_SYSTEM = """You are an SEO validator for real estate and property management website templates.
You receive a blueprint JSON and validate:
1. Each page has seo.meta_title, seo.meta_description, seo.h1 that are present and non-empty.
2. Meta titles are 30-60 characters and descriptive.
3. Meta descriptions are 120-160 characters and include a clear value proposition.
4. H1s are unique per page and keyword-relevant for real estate/property management.
5. No duplicate meta titles or descriptions across pages.

You output ONLY valid JSON in this shape:
{
  "passed": true/false,
  "score": 0-100,
  "issues": [ { "path": "e.g. pages[2].seo", "message": "...", "suggestion": "..." } ],
  "summary": "One paragraph summary."
}
If you cannot comply, return {"error": "description"}."""

SEO_VALIDATOR_USER = """Validate the SEO (meta titles, descriptions, h1) of this blueprint for real estate/property management.
Industry: {industry}

Blueprint JSON:
{blueprint_json}

Output ONLY the JSON object (passed, score, issues, summary)."""


def validate_seo(blueprint_json: Dict[str, Any], industry: str = "real_estate") -> Dict[str, Any]:
    """Run SEO validation on blueprint. Returns { passed, score, issues, summary } or { error }."""
    try:
        llm = get_llm(task="analysis")
        user = SEO_VALIDATOR_USER.format(
            industry=industry,
            blueprint_json=json.dumps(blueprint_json, default=str)[:12000],
        )
        response = invoke_llm(llm, SEO_VALIDATOR_SYSTEM + "\n\n" + user)
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
        logger.exception("SEO validation failed: %s", e)
        return {"passed": False, "score": 0, "issues": [], "summary": str(e), "error": str(e)}
