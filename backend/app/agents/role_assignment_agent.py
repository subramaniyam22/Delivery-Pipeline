"""
Role assignment re-ranking: optional AI assist when deterministic tie or high-risk.
Returns re-ranked candidate list with reasoning; fallback to deterministic order on failure.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def rerank_candidates(
    role: str,
    candidates: List[Dict[str, Any]],
    project_summary: str,
    use_ai: bool = True,
) -> List[Dict[str, Any]]:
    """
    Re-rank candidates (each has user_id, name, score, reasons).
    When use_ai and OpenAI available, call LLM to re-rank with reasoning.
    On failure or use_ai=False, return candidates unchanged (deterministic order).
    """
    if not candidates or not use_ai:
        return candidates
    try:
        from app.utils.llm import invoke_llm
        from app.agents.prompts import get_llm
        llm = get_llm(task="plan")
        prompt = f"""You are an assignment assistant. Given a list of candidates for role "{role}", re-rank them best-first. Consider workload balance and skills.
Project context: {project_summary[:500]}
Candidates (score, reasons):
{json.dumps([{"user_id": c.get("user_id"), "name": c.get("name"), "score": c.get("score"), "reasons": c.get("reasons", [])} for c in candidates[:5]], indent=2)}
Return valid JSON only: {{ "ranked_user_ids": ["uuid1", "uuid2", ...], "reasoning": "one sentence" }}
If order is fine as-is, return the same order."""
        response = invoke_llm(llm, prompt)
        if isinstance(response, str):
            data = json.loads(response)
            ranked_ids = data.get("ranked_user_ids") or []
            if ranked_ids:
                by_id = {str(c.get("user_id")): c for c in candidates}
                out = []
                for uid in ranked_ids:
                    if uid in by_id:
                        out.append(by_id[uid])
                        if "reasoning" not in out[-1]:
                            out[-1]["ai_reasoning"] = data.get("reasoning", "")
                for c in candidates:
                    if str(c.get("user_id")) not in ranked_ids:
                        out.append(c)
                return out
    except Exception as e:
        logger.warning("Role assignment re-rank failed: %s", e)
    return candidates
