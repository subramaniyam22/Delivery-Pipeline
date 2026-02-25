from typing import Dict, List, Any, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


async def notify_human_consultant_request(project_id: str, project_title: str, db: Any) -> None:
    """
    Notify consultant (if assigned), all managers, and all admins that the client
    requested to talk to a human. Persists notifications and sends real-time WS.
    Always records an audit log so the request is visible on the project even when no recipients exist.
    """
    from app.models import Project, User, Role, AuditLog
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning("notify_human_consultant_request: project not found %s", project_id)
        return
    # Always record in audit log so managers/admins see it when they open the project
    try:
        db.add(AuditLog(
            project_id=project.id,
            actor_user_id=None,
            action="CLIENT_REQUESTED_HUMAN",
            payload_json={"project_title": project_title, "message": "Client requested to talk to a human consultant."},
        ))
        db.commit()
    except Exception as e:
        logger.error("Failed to write audit log for human consultant request: %s", e)
        if db:
            try:
                db.rollback()
            except Exception:
                pass
    recipient_ids: set = set()
    if project.consultant_user_id:
        recipient_ids.add(str(project.consultant_user_id))
    for user in db.query(User).filter(User.role == Role.MANAGER).all():
        recipient_ids.add(str(user.id))
    for user in db.query(User).filter(User.role == Role.ADMIN).all():
        recipient_ids.add(str(user.id))
    if not recipient_ids:
        logger.warning("No consultant, managers, or admins found for project %s – human request recorded in audit log only", project_id)
        return
    message = {
        "type": "URGENT_ALERT",
        "project_id": str(project_id),
        "project_title": project_title,
        "message": f"Client for {project_title} requested a human consultant.",
    }
    for user_id in recipient_ids:
        try:
            await notification_manager.send_personal_message(message, user_id, db)
        except Exception as e:
            logger.error("Failed to send human request notification to %s: %s", user_id, e)
        try:
            # Dashboard connects to /ws/notifications (websocket.manager), not notification_manager
            from app.websocket.manager import manager as ws_manager
            await ws_manager.send_personal_message(message, user_id)
        except Exception as e:
            logger.error("Failed to send human request via WS to %s: %s", user_id, e)
    logger.info("Sent human consultant request alert to %d recipient(s) for project %s", len(recipient_ids), project_id)


class NotificationConnectionManager:
    def __init__(self):
        # Map user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"Notification WS Connected: {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"Notification WS Disconnected: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str, db=None):
        # Persist if db session provided
        if db:
            try:
                from app.models import Notification
                new_notif = Notification(
                    user_id=user_id,
                    project_id=message.get("project_id"),
                    type=message.get("type", "INFO"),
                    message=message.get("message", ""),
                    is_read=False
                )
                db.add(new_notif)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to save notification to DB: {e}")

        # Send WS
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send Notification WS message to {user_id}: {e}")

notification_manager = NotificationConnectionManager()
