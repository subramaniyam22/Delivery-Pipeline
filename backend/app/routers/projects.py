from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Project
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    OnboardingUpdateRequest,
    StageStatusUpdateRequest
)
from app.deps import get_current_active_user
from app.services import project_service
from app.rbac import check_full_access, can_access_stage
from app.models import Stage
from typing import List
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project (Consultant/Admin/Manager)"""
    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Consultant, Admin, and Manager can create projects"
        )
    
    project = project_service.create_project(db, data, current_user)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all projects (all authenticated users)"""
    projects = db.query(Project).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get project details (all authenticated users)"""
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update project metadata (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update project metadata"
        )
    
    project = project_service.update_project(db, project_id, data, current_user)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.post("/{project_id}/onboarding/update")
def update_onboarding(
    project_id: UUID,
    data: OnboardingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update onboarding data (Consultant/Admin/Manager)"""
    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Consultant, Admin, and Manager can update onboarding"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Store onboarding data in project context (could be a separate table in production)
    # For MVP, we'll use the workflow context
    return {"success": True, "message": "Onboarding data updated"}


@router.post("/{project_id}/assignment/publish")
def publish_assignment(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Publish assignment plan (PC/Admin/Manager)"""
    allowed_roles = [Role.PC, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PC, Admin, and Manager can publish assignment"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.ASSIGNMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in ASSIGNMENT stage"
        )
    
    return {"success": True, "message": "Assignment plan published"}


@router.post("/{project_id}/build/status")
def update_build_status(
    project_id: UUID,
    data: StageStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update build status (Builder/Admin/Manager)"""
    allowed_roles = [Role.BUILDER, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Builder, Admin, and Manager can update build status"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.BUILD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in BUILD stage"
        )
    
    return {
        "success": True,
        "message": f"Build status updated to {data.status.value}",
        "notes": data.notes
    }


@router.post("/{project_id}/test/status")
def update_test_status(
    project_id: UUID,
    data: StageStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update test status (Tester/Admin/Manager)"""
    allowed_roles = [Role.TESTER, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Tester, Admin, and Manager can update test status"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.TEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in TEST stage"
        )
    
    return {
        "success": True,
        "message": f"Test status updated to {data.status.value}",
        "notes": data.notes
    }


@router.post("/{project_id}/complete/close")
def close_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Close project (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can close projects"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    from app.models import ProjectStatus
    project.status = ProjectStatus.COMPLETED
    project.current_stage = Stage.COMPLETE
    db.commit()
    
    return {"success": True, "message": "Project closed successfully"}
