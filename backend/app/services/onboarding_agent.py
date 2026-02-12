from sqlalchemy.orm import Session
from app.models import OnboardingData, Project, OnboardingReviewStatus
from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging
import json

logger = logging.getLogger(__name__)

async def validate_onboarding_submission(db: Session, project_id: str, onboarding_data: OnboardingData):
    """
    Validates the onboarding submission using AI to check for quality and completeness.
    Returns the result and updates the onboarding record directly if needed, 
    but primarily returns structured feedback.
    """
    try:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set. Skipping AI review.")
            return {
                "approved": True, 
                "reason": "AI Review skipped (API Key missing)", 
                "notes": "Automatic approval due to missing AI configuration."
            }

        # Fetch Project for context
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"approved": False, "reason": "Project not found"}

        # Construct Context from Onboarding Data
        reqs = onboarding_data.requirements_json or {}
        
        # Safe extraction of key fields
        brand_guide = reqs.get('brand_guidelines_details', 'Not provided')
        ref_sites = reqs.get('template_references', 'Not provided')
        colors = reqs.get('color_notes', reqs.get('color_selection', 'Not provided'))
        nav = reqs.get('navigation_notes', 'Not provided')
        copy_notes = reqs.get('copy_scope_notes', 'Not provided')
        
        # System Prompt
        system_prompt = """You are an expert Digital Project Manager reviewing a client's onboarding submission for a web design project.
        Your goal is to catch low-quality, incomplete, or gibberish inputs BEFORE the project moves to the team.
        
        Review the following inputs for:
        1. **Clarity**: Is the user intent clear?
        2. **Completeness**: Did they answer the prompt or just type "idk", "later", "n/a" where detail is needed?
        3. **Gibberish**: Look for "lorem ipsum", keyboard mashing, or placeholder text.
        
        Inputs to Review:
        - Brand Guidelines Details
        - Design References
        - Color Preferences
        - Navigation / Sitemap
        
        Return a JSON response:
        {
            "approved": boolean, // True if generally good quality. False if critical info is garbage/missing.
            "confidence": float, // 0.0 to 1.0
            "feedback": "Internal note for the consultant summarizing the quality...",
            "flagged_fields": ["field_name"] // List of fields with issues
        }
        """

        user_content = f"""
        Project Title: {project.title}
        Client: {project.client_name}
        
        Submission Data:
        - Brand Guidelines: {brand_guide}
        - Design References: {ref_sites}
        - Color Selection/Notes: {colors}
        - Navigation Notes: {nav}
        - Copy Scope Notes: {copy_notes}
        """

        model_kwargs = {"response_format": {"type": "json_object"}}
        if settings.OPENAI_MAX_TOKENS is not None:
            model_kwargs["max_tokens"] = settings.OPENAI_MAX_TOKENS
        chat = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            request_timeout=settings.OPENAI_TIMEOUT_SECONDS,
            model_kwargs=model_kwargs,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ]

        response = await chat.ainvoke(messages)
        result_json = json.loads(response.content)
        
        return result_json

    except Exception as e:
        logger.error(f"AI Onboarding Review Failed: {e}")
        return {
            "approved": True, 
            "reason": "AI Review Failed", 
            "notes": f"System error during review: {str(e)}"
        }
