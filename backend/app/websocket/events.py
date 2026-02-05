"""
WebSocket event types and handlers.
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    STAGE_CHANGED = "stage_changed"
    
    # Task events
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    
    # Comment events
    COMMENT_ADDED = "comment_added"
    
    # Notification events
    NOTIFICATION = "notification"
    ALERT = "alert"
    
    # System events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"


class WebSocketEvent:
    """WebSocket event builder."""
    
    @staticmethod
    def create_event(
        event_type: EventType,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a WebSocket event.
        
        Args:
            event_type: Type of event
            data: Event data
            user_id: Target user ID (optional)
            project_id: Related project ID (optional)
        
        Returns:
            Event dictionary
        """
        event = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            event["user_id"] = user_id
        
        if project_id:
            event["project_id"] = project_id
        
        return event
    
    @staticmethod
    def project_created(project_id: str, title: str, created_by: str) -> Dict[str, Any]:
        """Create project created event."""
        return WebSocketEvent.create_event(
            EventType.PROJECT_CREATED,
            {
                "project_id": project_id,
                "title": title,
                "created_by": created_by,
                "message": f"New project created: {title}"
            },
            project_id=project_id
        )
    
    @staticmethod
    def project_updated(project_id: str, title: str, updated_by: str, changes: Dict) -> Dict[str, Any]:
        """Create project updated event."""
        return WebSocketEvent.create_event(
            EventType.PROJECT_UPDATED,
            {
                "project_id": project_id,
                "title": title,
                "updated_by": updated_by,
                "changes": changes,
                "message": f"Project updated: {title}"
            },
            project_id=project_id
        )
    
    @staticmethod
    def stage_changed(project_id: str, title: str, old_stage: str, new_stage: str) -> Dict[str, Any]:
        """Create stage changed event."""
        return WebSocketEvent.create_event(
            EventType.STAGE_CHANGED,
            {
                "project_id": project_id,
                "title": title,
                "old_stage": old_stage,
                "new_stage": new_stage,
                "message": f"Project {title} moved from {old_stage} to {new_stage}"
            },
            project_id=project_id
        )
    
    @staticmethod
    def task_assigned(task_id: str, task_title: str, assigned_to: str, project_id: str) -> Dict[str, Any]:
        """Create task assigned event."""
        return WebSocketEvent.create_event(
            EventType.TASK_ASSIGNED,
            {
                "task_id": task_id,
                "task_title": task_title,
                "assigned_to": assigned_to,
                "project_id": project_id,
                "message": f"New task assigned: {task_title}"
            },
            user_id=assigned_to,
            project_id=project_id
        )
    
    @staticmethod
    def notification(message: str, level: str = "info", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create notification event."""
        return WebSocketEvent.create_event(
            EventType.NOTIFICATION,
            {
                "message": message,
                "level": level
            },
            user_id=user_id
        )
    
    @staticmethod
    def alert(message: str, severity: str = "warning", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create alert event."""
        return WebSocketEvent.create_event(
            EventType.ALERT,
            {
                "message": message,
                "severity": severity
            },
            user_id=user_id
        )
