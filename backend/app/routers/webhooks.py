from typing import Dict, Any, Optional
import logging

from fastapi import APIRouter, Header, HTTPException, Request

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


@router.post("/resend")
async def resend_webhook(request: Request) -> Dict[str, bool]:
    """Receive Resend webhooks (Svix signature verification)."""
    if not (getattr(settings, "RESEND_WEBHOOK_SECRET", None) or "").strip():
        raise HTTPException(
            status_code=503,
            detail="RESEND_WEBHOOK_SECRET not configured",
        )
    payload = await request.body()
    payload_str = payload.decode("utf-8")
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")
    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(status_code=400, detail="Missing Svix headers (svix-id, svix-timestamp, svix-signature)")
    from svix.webhooks import Webhook
    wh = Webhook(settings.RESEND_WEBHOOK_SECRET)
    try:
        evt = wh.verify(
            payload_str,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    logger.info(
        "resend_webhook_received",
        extra={
            "type": evt.get("type"),
            "id": evt.get("id"),
            "data": evt.get("data", {}),
        },
    )
    return {"ok": True}
