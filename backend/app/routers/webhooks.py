from typing import Dict, Any, Optional
import logging

from fastapi import APIRouter, Header, HTTPException

from app.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/chat-logs")
async def receive_chat_log_webhook(
    payload: Dict[str, Any],
    x_webhook_secret: Optional[str] = Header(None)
) -> Dict[str, Any]:
    if settings.CHAT_LOG_WEBHOOK_SECRET:
        if x_webhook_secret != settings.CHAT_LOG_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    logger.info(f"Chat log webhook received: {payload}")
    return {"received": True}
