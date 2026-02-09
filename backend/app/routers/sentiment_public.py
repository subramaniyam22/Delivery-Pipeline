from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ClientSentiment, Project, Role, User, Notification, AuditLog, OnboardingData, TemplateRegistry
from app.schemas import SentimentCreate, SentimentResponse
from app.utils.sentiment_tokens import verify_sentiment_token
from app.rate_limit import limiter, PUBLIC_RATE_LIMIT
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent
from uuid import UUID

router = APIRouter(prefix="/public/sentiment", tags=["sentiment"])


@router.get("/{token}")
@limiter.limit(PUBLIC_RATE_LIMIT)
def get_sentiment_form(token: str, request: Request, db: Session = Depends(get_db)):
    project_id = verify_sentiment_token(token)
    if not project_id:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    try:
        project_uuid = UUID(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": str(project.id), "project_title": project.title}


@router.post("/{token}", response_model=SentimentResponse)
@limiter.limit(PUBLIC_RATE_LIMIT)
def submit_sentiment(token: str, data: SentimentCreate, request: Request, db: Session = Depends(get_db)):
    project_id = verify_sentiment_token(token)
    if not project_id:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    try:
        project_uuid = UUID(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
    template_id = None
    template_name = None
    if onboarding:
        template_id = onboarding.selected_template_id or onboarding.theme_preference
        if template_id == "custom":
            template_id = None
        if template_id:
            try:
                template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
            except Exception:
                template = None
            if template:
                template_name = template.name

    sentiment = ClientSentiment(
        project_id=project.id,
        rating=data.rating,
        comment=data.comment,
        template_id=template_id,
        template_name=template_name,
        stage_at_delivery=project.current_stage.value if project.current_stage else None,
        created_by_type="client",
        created_by_user_id=None,
    )
    db.add(sentiment)
    db.add(
        AuditLog(
            project_id=project.id,
            actor_user_id=project.created_by_user_id,
            action="SENTIMENT_SUBMITTED",
            payload_json={"rating": data.rating, "comment": data.comment},
        )
    )
    db.commit()
    db.refresh(sentiment)

    admins = db.query(User).filter(User.role.in_([Role.ADMIN, Role.MANAGER])).all()
    for admin in admins:
        notification = Notification(
            user_id=admin.id,
            project_id=project.id,
            type="SENTIMENT",
            message=f"New client sentiment for {project.title}: {data.rating}/5",
            is_read=False,
        )
        db.add(notification)
        db.commit()
        event = WebSocketEvent.notification(notification.message, level="info", user_id=str(admin.id))
        try:
            import asyncio
            asyncio.run(manager.send_personal_message(event, str(admin.id)))
        except Exception:
            pass

    return sentiment
