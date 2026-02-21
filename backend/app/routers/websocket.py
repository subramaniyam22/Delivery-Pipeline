"""
WebSocket router for real-time updates.
Token must be provided (query param, cookie, or Bearer header); server validates JWT
and ensures path user_id matches token so clients cannot subscribe as another user.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Cookie, Depends, HTTPException
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent, EventType
from app.deps import get_current_user_from_token, get_current_user
from app.db import SessionLocal
from app.models import Role
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/notifications/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None)  # Auto-read 'access_token' cookie
):
    """
    WebSocket endpoint for real-time notifications.
    Auth: token in query (?token=), cookie (access_token), or Authorization: Bearer.
    Path user_id must match the authenticated user (no 403 spam; validated server-side).
    """
    final_token = token or access_token
    if not final_token:
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            final_token = auth_header.split(" ")[1]

    if not final_token:
        logger.warning("WS connection rejected: no token")
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    db = SessionLocal()
    try:
        user = get_current_user_from_token(final_token, db)
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="Invalid or inactive user")
            return
        if str(user.id) != user_id:
            await websocket.close(code=1008, reason="Token user does not match path")
            return
    finally:
        db.close()

    try:
        await manager.connect(websocket, user_id)
        
        # Send welcome message
        welcome_event = WebSocketEvent.notification(
            f"Connected to real-time updates",
            level="success",
            user_id=user_id
        )
        await manager.send_personal_message(welcome_event, user_id)
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "subscribe_project":
                    project_id = message.get("project_id")
                    if project_id:
                        manager.subscribe_to_project(project_id, user_id)
                        response = WebSocketEvent.notification(
                            f"Subscribed to project updates",
                            level="info",
                            user_id=user_id
                        )
                        await manager.send_personal_message(response, user_id)
                
                elif message.get("type") == "unsubscribe_project":
                    project_id = message.get("project_id")
                    if project_id:
                        manager.unsubscribe_from_project(project_id, user_id)
                        response = WebSocketEvent.notification(
                            f"Unsubscribed from project updates",
                            level="info",
                            user_id=user_id
                        )
                        await manager.send_personal_message(response, user_id)
                
                elif message.get("type") == "ping":
                    # Respond to ping
                    pong = {"type": "pong", "timestamp": message.get("timestamp")}
                    await websocket.send_json(pong)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user_id}")
            except Exception as e:
                logger.error(f"Error processing message from user {user_id}: {e}")
                break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)


@router.get("/stats")
async def get_websocket_stats(current_user=Depends(get_current_user)):
    """Get WebSocket connection statistics (Admin/Manager only)."""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Admin or Manager required")
    return {
        "total_connections": manager.get_connection_count(),
        "connected_users": manager.get_user_count(),
        "project_subscriptions": len(manager.project_subscriptions)
    }
