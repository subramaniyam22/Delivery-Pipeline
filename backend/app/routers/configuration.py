from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db
from app.deps import get_current_active_user
from app.models import ThemeTemplate, User, Role

router = APIRouter()

# --- Schemas ---
class TemplateCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    preview_url: Optional[str] = None
    colors_json: Optional[dict] = {}
    features_json: Optional[list] = []

class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    preview_url: Optional[str]
    colors_json: dict
    features_json: list
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True

# --- Endpoints ---

@router.get("/templates", response_model=List[TemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all active templates."""
    # Allow all authenticated users to see templates (Consultants need to see them too)
    return db.query(ThemeTemplate).filter(ThemeTemplate.is_active == True).all()

@router.post("/templates", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new theme template (Admin/Manager only)."""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    existing = db.query(ThemeTemplate).filter(ThemeTemplate.id == template.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template ID already exists")
    
    new_template = ThemeTemplate(
        id=template.id,
        name=template.name,
        description=template.description,
        preview_url=template.preview_url,
        colors_json=template.colors_json,
        features_json=template.features_json
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template

@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete a template (Admin/Manager only)."""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    template = db.query(ThemeTemplate).filter(ThemeTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Soft delete
    template.is_active = False
    db.commit()
    return {"success": True, "message": "Template deleted"}
