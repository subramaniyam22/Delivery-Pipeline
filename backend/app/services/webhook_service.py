import logging
from typing import Optional, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_chat_log_webhook(payload: Dict[str, Any]) -> None:
    url = settings.CHAT_LOG_WEBHOOK_URL
    if not url and settings.BACKEND_URL:
        url = f"{settings.BACKEND_URL.rstrip('/')}/api/webhooks/chat-logs"
    if not url:
        return

    headers = {"Content-Type": "application/json"}
    if settings.CHAT_LOG_WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = settings.CHAT_LOG_WEBHOOK_SECRET

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload, headers=headers)
    except Exception as exc:
        logger.warning(f"Chat log webhook failed: {exc}")
