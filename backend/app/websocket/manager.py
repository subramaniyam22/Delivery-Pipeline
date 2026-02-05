"""
WebSocket connection manager for real-time updates.
"""
import logging
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from uuid import UUID

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Active connections: {user_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Project subscriptions: {project_id: {user_id1, user_id2, ...}}
        self.project_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's WebSocket."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a user's WebSocket."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Remove from all project subscriptions
                for subscribers in self.project_subscriptions.values():
                    subscribers.discard(user_id)
        
        logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to a specific user (all their connections)."""
        if user_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, user_id)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
    
    def subscribe_to_project(self, project_id: str, user_id: str):
        """Subscribe user to project updates."""
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = set()
        
        self.project_subscriptions[project_id].add(user_id)
        logger.info(f"User {user_id} subscribed to project {project_id}")
    
    def unsubscribe_from_project(self, project_id: str, user_id: str):
        """Unsubscribe user from project updates."""
        if project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(user_id)
            
            # Clean up if no more subscribers
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        logger.info(f"User {user_id} unsubscribed from project {project_id}")
    
    async def notify_project_subscribers(self, project_id: str, message: dict):
        """Notify all users subscribed to a project."""
        if project_id in self.project_subscriptions:
            for user_id in self.project_subscriptions[project_id]:
                await self.send_personal_message(message, user_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_user_count(self) -> int:
        """Get number of connected users."""
        return len(self.active_connections)
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# Global connection manager instance
manager = ConnectionManager()
