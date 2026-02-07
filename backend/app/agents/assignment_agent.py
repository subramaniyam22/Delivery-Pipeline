from typing import Dict, Any
import json
from app.agents.prompts import ASSIGNMENT_PROMPT, get_llm


class AssignmentAgent:
    """AI agent for assignment planning."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        llm = get_llm()
        prompt = ASSIGNMENT_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            onboarding_summary=context.get("onboarding_summary", ""),
            resources=json.dumps(context.get("available_resources", []))
        )
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                return json.loads(response)
        except Exception:
            pass
        return {"task_breakdown": [], "summary": "Assignment plan created"}
