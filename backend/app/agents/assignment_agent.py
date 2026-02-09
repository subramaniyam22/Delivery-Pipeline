from typing import Dict, Any
import json
from app.agents.prompts import ASSIGNMENT_PROMPT, get_llm
from app.utils.llm import invoke_llm
from app.utils.llm_cache import get_cached_plan, set_cached_plan


class AssignmentAgent:
    """AI agent for assignment planning."""

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        project_info = context.get("project_info", {})
        cached = None
        if project_info.get("id"):
            cached = get_cached_plan(str(project_info.get("id")), "assignment", context, [])
        if cached:
            return cached
        llm = get_llm(task="plan")
        prompt = ASSIGNMENT_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            onboarding_summary=context.get("onboarding_summary", ""),
            resources=json.dumps(context.get("available_resources", []))
        )
        try:
            response = invoke_llm(llm, prompt)
            if isinstance(response, str):
                plan = json.loads(response)
                if project_info.get("id"):
                    set_cached_plan(str(project_info.get("id")), "assignment", context, [], plan)
                return plan
        except Exception:
            pass
        return {"task_breakdown": [], "summary": "Assignment plan created"}
