"""Project Management Router - Pause/Archive functionality"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db
from app.deps import get_current_user
from app.models import User, Role, Project, ProjectStatus


router = APIRouter(prefix="/project-management", tags=["Project Management"])


# ============== Schemas ==============

class PauseProjectRequest(BaseModel):
    reason: Optional[str] = None


class ArchiveProjectRequest(BaseModel):
    reason: Optional[str] = None


class ProjectStatusResponse(BaseModel):
    id: UUID
    title: str
    status: str
    paused_at: Optional[datetime]
    pause_reason: Optional[str]
    archived_at: Optional[datetime]
    archive_reason: Optional[str]
    message: str


# ============== Helper Functions ==============

def check_admin_or_consultant(current_user: User):
    """Verify user is admin or consultant"""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, or Consultant can manage project status"
        )


def can_manage_project(user: User, project: Project) -> bool:
    """Check if user can manage this project"""
    if user.role in [Role.ADMIN, Role.MANAGER]:
        return True
    if user.role == Role.CONSULTANT:
        return project.consultant_user_id == user.id or project.pc_user_id == user.id
    return False


# ============== Endpoints ==============

@router.post("/pause/{project_id}", response_model=ProjectStatusResponse)
def pause_project(
    project_id: UUID,
    request: PauseProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a project (Admin/Manager/Consultant)"""
    check_admin_or_consultant(current_user)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_manage_project(current_user, project):
        raise HTTPException(status_code=403, detail="You don't have permission to manage this project")
    
    if project.status == ProjectStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Project is already paused")
    
    if project.status in [ProjectStatus.ARCHIVED, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot pause a {project.status.value} project")
    
    project.status = ProjectStatus.PAUSED
    project.paused_at = datetime.utcnow()
    project.paused_by_user_id = current_user.id
    project.pause_reason = request.reason
    
    db.commit()
    db.refresh(project)
    
    return ProjectStatusResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        paused_at=project.paused_at,
        pause_reason=project.pause_reason,
        archived_at=project.archived_at,
        archive_reason=project.archive_reason,
        message="Project paused successfully"
    )


@router.post("/resume/{project_id}", response_model=ProjectStatusResponse)
def resume_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused project (Admin/Manager/Consultant)"""
    check_admin_or_consultant(current_user)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_manage_project(current_user, project):
        raise HTTPException(status_code=403, detail="You don't have permission to manage this project")
    
    if project.status != ProjectStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Project is not paused")
    
    project.status = ProjectStatus.ACTIVE
    project.paused_at = None
    project.paused_by_user_id = None
    project.pause_reason = None
    
    db.commit()
    db.refresh(project)
    
    return ProjectStatusResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        paused_at=project.paused_at,
        pause_reason=project.pause_reason,
        archived_at=project.archived_at,
        archive_reason=project.archive_reason,
        message="Project resumed successfully"
    )


@router.post("/archive/{project_id}", response_model=ProjectStatusResponse)
def archive_project(
    project_id: UUID,
    request: ArchiveProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a project (Admin/Manager/Consultant)"""
    check_admin_or_consultant(current_user)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not can_manage_project(current_user, project):
        raise HTTPException(status_code=403, detail="You don't have permission to manage this project")
    
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Project is already archived")
    
    project.status = ProjectStatus.ARCHIVED
    project.archived_at = datetime.utcnow()
    project.archived_by_user_id = current_user.id
    project.archive_reason = request.reason
    
    db.commit()
    db.refresh(project)
    
    return ProjectStatusResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        paused_at=project.paused_at,
        pause_reason=project.pause_reason,
        archived_at=project.archived_at,
        archive_reason=project.archive_reason,
        message="Project archived successfully"
    )


@router.post("/unarchive/{project_id}", response_model=ProjectStatusResponse)
def unarchive_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unarchive a project (Admin/Manager only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can unarchive projects"
        )
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != ProjectStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Project is not archived")
    
    project.status = ProjectStatus.ACTIVE
    project.archived_at = None
    project.archived_by_user_id = None
    project.archive_reason = None
    
    db.commit()
    db.refresh(project)
    
    return ProjectStatusResponse(
        id=project.id,
        title=project.title,
        status=project.status.value,
        paused_at=project.paused_at,
        pause_reason=project.pause_reason,
        archived_at=project.archived_at,
        archive_reason=project.archive_reason,
        message="Project unarchived successfully"
    )


@router.get("/archived", response_model=List[dict])
def get_archived_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all archived projects (Admin/Manager/Consultant)"""
    check_admin_or_consultant(current_user)
    
    if current_user.role in [Role.ADMIN, Role.MANAGER]:
        projects = db.query(Project).filter(
            Project.status == ProjectStatus.ARCHIVED
        ).all()
    else:
        # Consultant sees only their archived projects
        projects = db.query(Project).filter(
            Project.status == ProjectStatus.ARCHIVED,
            (Project.consultant_user_id == current_user.id) | 
            (Project.pc_user_id == current_user.id)
        ).all()
    
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "client_name": p.client_name,
            "archived_at": p.archived_at.isoformat() if p.archived_at else None,
            "archive_reason": p.archive_reason,
            "current_stage": p.current_stage.value
        }
        for p in projects
    ]


@router.get("/paused", response_model=List[dict])
def get_paused_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all paused projects (Admin/Manager/Consultant)"""
    check_admin_or_consultant(current_user)
    
    if current_user.role in [Role.ADMIN, Role.MANAGER]:
        projects = db.query(Project).filter(
            Project.status == ProjectStatus.PAUSED
        ).all()
    else:
        # Consultant sees only their paused projects
        projects = db.query(Project).filter(
            Project.status == ProjectStatus.PAUSED,
            (Project.consultant_user_id == current_user.id) | 
            (Project.pc_user_id == current_user.id)
        ).all()
    
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "client_name": p.client_name,
            "paused_at": p.paused_at.isoformat() if p.paused_at else None,
            "pause_reason": p.pause_reason,
            "current_stage": p.current_stage.value
        }
        for p in projects
    ]
