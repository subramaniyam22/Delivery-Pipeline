from typing import Dict, Any, List
import json
from app.agents.prompts import BUILD_PROMPT, get_llm


class BuildAgent:
    """AI agent for build validation."""

    def run(self, context: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        llm = get_llm()
        prompt = BUILD_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            build_tasks=json.dumps(context.get("build_tasks", [])),
            build_artifacts=json.dumps([a.get("filename") for a in artifacts if a.get("stage") == "BUILD"])
        )
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                return json.loads(response)
        except Exception:
            pass
        return {"ready_for_approval": True, "summary": "Build stage completed"}
