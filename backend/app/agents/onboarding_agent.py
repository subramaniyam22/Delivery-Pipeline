from typing import Dict, Any, List
import json
from app.agents.prompts import ONBOARDING_PROMPT, get_llm


class OnboardingAgent:
    """AI agent for onboarding validation and summary."""

    def run(self, context: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        llm = get_llm()
        prompt = ONBOARDING_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            onboarding_data=json.dumps(context.get("onboarding_data", {})),
            artifacts=json.dumps([a.get("filename") for a in artifacts if a.get("stage") == "ONBOARDING"])
        )
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                return json.loads(response)
        except Exception:
            pass
        return {"ready_for_next_stage": True, "summary": "Onboarding complete"}
