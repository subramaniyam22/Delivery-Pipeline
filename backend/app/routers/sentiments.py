from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db import get_db
from app.deps import get_current_active_user
from app.models import ClientSentiment, Role, User, Project, OnboardingData, TemplateRegistry
from app.schemas import SentimentResponse

router = APIRouter(prefix="/sentiments", tags=["sentiments"])


@router.get("", response_model=List[SentimentResponse])
def list_sentiments(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Admin or Manager can view sentiments")
    from sqlalchemy.orm import joinedload
    query = db.query(ClientSentiment).options(joinedload(ClientSentiment.project))
    if project_id:
        query = query.filter(ClientSentiment.project_id == project_id)
    sentiments = query.order_by(ClientSentiment.submitted_at.desc()).all()

    results = []
    for sentiment in sentiments:
        project = sentiment.project
        template_id = sentiment.template_id
        template_name = sentiment.template_name

        if (not template_id or not template_name) and project:
            onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
            if onboarding:
                derived_id = onboarding.selected_template_id or onboarding.theme_preference
                if derived_id != "custom":
                    template_id = template_id or derived_id
            if template_id and not template_name:
                try:
                    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
                except Exception:
                    template = None
                if template:
                    template_name = template.name

        results.append(
            {
                "id": sentiment.id,
                "project_id": sentiment.project_id,
                "rating": sentiment.rating,
                "comment": sentiment.comment,
                "submitted_at": sentiment.submitted_at,
                "template_id": template_id,
                "template_name": template_name,
                "stage_at_delivery": sentiment.stage_at_delivery or (project.current_stage.value if project and project.current_stage else None),
                "created_by_user_id": sentiment.created_by_user_id,
                "created_by_type": sentiment.created_by_type,
                "project_title": project.title if project else None,
                "client_name": project.client_name if project else None,
            }
        )

    return results
