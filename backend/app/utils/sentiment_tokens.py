from typing import Optional
from uuid import UUID

from app.config import settings
from app.utils.signed_tokens import generate_signed_token, verify_signed_token


def generate_sentiment_token(project_id: UUID, ttl_hours: Optional[int] = None) -> str:
    ttl = ttl_hours or settings.SENTIMENT_TOKEN_TTL_HOURS
    payload = {
        "project_id": str(project_id),
        "purpose": "sentiment",
    }
    return generate_signed_token(payload, int(ttl * 3600))


def verify_sentiment_token(token: str) -> Optional[str]:
    payload = verify_signed_token(token, purpose="sentiment")
    if not payload:
        return None
    return payload.get("project_id")
