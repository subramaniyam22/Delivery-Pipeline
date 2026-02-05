"""
WebSocket router for real-time updates.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent, EventType
from app.deps import get_current_user_from_token
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/notifications/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Usage:
        ws://localhost:8000/ws/notifications/{user_id}?token={jwt_token}
    """
    # Verify authentication
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    try:
        # Validate token (you can use get_current_user_from_token here)
        # For now, we'll accept the connection
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
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": manager.get_connection_count(),
        "connected_users": manager.get_user_count(),
        "project_subscriptions": len(manager.project_subscriptions)
    }
