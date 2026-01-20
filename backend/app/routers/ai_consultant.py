from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.config import settings
from app.db import get_db
from app.models import ChatLog, Project
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging
import uuid
import re
import asyncio
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Consultant"])

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        # Map project_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WS Connected: {project_id}. Total clients: {len(self.active_connections[project_id])}")

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WS Disconnected: {project_id}")

    async def broadcast(self, message: dict, project_id: str):
        if project_id in self.active_connections:
            # Convert to JSON string for sending
            # Ensure datetime is serializable if present, but we construct dict manually usually
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message: {e}")

manager = ConnectionManager()

# --- Schemas ---
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    chat_history: Optional[List[Dict[str, str]]] = None

class ConsultantMessageRequest(BaseModel):
    project_id: str
    message: str

class ToggleAIRequest(BaseModel):
    project_id: str
    enabled: bool

# --- WebSocket Endpoint ---
@router.websocket("/ws/chat/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, project_id)
    try:
        while True:
            # We keep the connection open. Clients can send messages here too if we want full duplex.
            # For now, we mainly use it for receiving updates, but let's handle incoming just in case.
            # Or just wait for disconnect.
            data = await websocket.receive_text()
            # If client sends "ping", we can pong, but usually not needed.
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket, project_id)


@router.post("/consult")
async def consult_ai(request: ChatRequest, db: Session = Depends(get_db)):
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not found in settings")
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    
    project_id = request.context.get("project_id") if request.context else None
    
    # 1. Log User Message
    if project_id:
        try:
            uuid.UUID(str(project_id))
            # Log message
            new_log = ChatLog(project_id=project_id, sender="user", message=request.message)
            db.add(new_log)
            db.commit()
            db.refresh(new_log)
            
            # Broadcast User Message
            await manager.broadcast({
                "id": str(new_log.id),
                "sender": "user",
                "message": request.message,
                "created_at": new_log.created_at.isoformat()
            }, project_id)
            
            # Check if AI is enabled
            project = db.query(Project).filter(Project.id == project_id).first()
            if project and project.features_json:
                ai_enabled = project.features_json.get('ai_enabled', True)
                if not ai_enabled:
                    # AI is disabled (Consultant taken over)
                    return {"response": "", "action": "human_mode"}
                    
        except Exception as e:
            logger.error(f"Failed to log user chat: {e}")

    try:
        # Initialize Chat Client
        chat = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY, 
            model="gpt-4-turbo-preview",
            temperature=0.7
        )
        
        # System Prompt
        system_prompt = """You are an experienced and empathetic Digital Project Consultant named 'Consultant AI'. 
Your role is to guide clients through the onboarding process for their new website or software project.

IMPORTANT: HUMAN HANDOFF PROTOCOL
If the user specifically asks to speak to a "human", "person", "consultant", "manager", or expresses significant frustration that you cannot resolve, you MUST trigger the handoff protocol.
To do this, start your response with exactly: "ACTION_REQUEST_HUMAN|".
Then, provide a polite message confirming that you have notified the team and someone will reach out shortly.
Example: "ACTION_REQUEST_HUMAN|I understand. I have flagged this conversation for your assigned consultant, and they will review the chat and reach out to you directly."

Guidelines:
1. **Be Human**: Use natural, professional, yet warm language.
2. **Be Specific**: Tailor advice to their industry if known.
3. **Be Helpful**: Explain *why* info is needed.
4. **Short & Clear**: Concise limits.
5. **Context Aware**: Use provided form data.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
        ]
        
        # Inject Context
        if request.context:
            context_str = "Current Form Data:\n"
            for key, value in request.context.items():
                if value and key != "project_id":
                    context_str += f"- {key}: {value}\n"
            messages.append(SystemMessage(content=context_str))
            
        messages.append(HumanMessage(content=request.message))
        
        logger.info(f"Sending request to OpenAI: {request.message}")
        response = chat.invoke(messages)
        content = response.content
        logger.info("Received response from OpenAI")
        
        action = None
        
        # Check for Handoff Action
        if "ACTION_REQUEST_HUMAN|" in content:
            parts = content.split("ACTION_REQUEST_HUMAN|")
            action = "handoff"
            content = parts[1].strip() if len(parts) > 1 else "Request sent."
        
        # 2. Log Bot Response
        if project_id:
            try:
                new_bot_log = ChatLog(project_id=project_id, sender="bot", message=content)
                db.add(new_bot_log)
                db.commit()
                db.refresh(new_bot_log)
                
                # Broadcast Bot Message
                await manager.broadcast({
                    "id": str(new_bot_log.id),
                    "sender": "bot",
                    "message": content,
                    "created_at": new_bot_log.created_at.isoformat()
                }, project_id)
                
            except Exception as e:
                logger.error(f"Failed to log bot chat: {e}")
        
        return {"response": content, "action": action}
        
    except Exception as e:
        logger.error(f"Error in consult_ai: {str(e)}")
        return {"response": "I apologize, but I'm having trouble connecting to my knowledge base right now. Please try again later."}

@router.get("/chat-logs/{project_id}")
async def get_chat_logs(project_id: str, db: Session = Depends(get_db)):
    try:
        uuid.UUID(str(project_id))
        logs = db.query(ChatLog).filter(ChatLog.project_id == project_id).order_by(ChatLog.created_at.asc()).all()
        return [
            {
                "id": str(log.id),
                "sender": log.sender,
                "message": log.message,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Project ID")
    except Exception as e:
        logger.error(f"Error fetching chat logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat logs")

@router.post("/chat/send")
async def send_consultant_message(data: ConsultantMessageRequest, db: Session = Depends(get_db)):
    try:
        uuid.UUID(str(data.project_id))
        new_log = ChatLog(project_id=data.project_id, sender="consultant", message=data.message)
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        
        # Broadcast Consultant Message
        await manager.broadcast({
            "id": str(new_log.id),
            "sender": "consultant",
            "message": data.message,
            "created_at": new_log.created_at.isoformat()
        }, data.project_id)
        
        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Error sending consultant message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.post("/toggle-ai")
async def toggle_ai(data: ToggleAIRequest, db: Session = Depends(get_db)):
    try:
        project = db.query(Project).filter(Project.id == data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        feats = project.features_json or {}
        # Make sure it's a dict (JSONB can be list or other types technically)
        if not isinstance(feats, dict):
            feats = {}
            
        feats['ai_enabled'] = data.enabled
        project.features_json = feats
        flag_modified(project, "features_json")
        db.commit()
        return {"status": "updated", "ai_enabled": data.enabled}
    except Exception as e:
        logger.error(f"Error toggling AI: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle AI")

@router.get("/status/{project_id}")
async def get_ai_status(project_id: str, db: Session = Depends(get_db)):
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        feats = project.features_json or {}
        if not isinstance(feats, dict): feats = {}
        
        return {"ai_enabled": feats.get('ai_enabled', True)}
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI status")
