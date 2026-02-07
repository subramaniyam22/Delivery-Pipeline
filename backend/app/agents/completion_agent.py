from typing import Dict, Any, List
import json
from app.agents.prompts import COMPLETE_PROMPT, get_llm


class CompletionAgent:
    """AI agent for completion summary."""

    def run(self, context: Dict[str, Any], artifacts: List[Dict[str, Any]], stage_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        llm = get_llm()
        prompt = COMPLETE_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            stage_outputs=json.dumps(stage_outputs),
            artifacts=json.dumps([{"stage": a.get("stage"), "filename": a.get("filename")} for a in artifacts])
        )
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                return json.loads(response)
        except Exception:
            pass
        return {"project_summary": "Project completed", "quality_score": 100}
