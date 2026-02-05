"""
Soft delete service for projects.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
from app.models import Project, User
from app.custom_exceptions import NotFoundException, ForbiddenException
from typing import Optional


def soft_delete_project(
    db: Session,
    project_id: UUID,
    current_user: User
) -> Project:
    """
    Soft delete a project (mark as deleted without removing from database).
    
    Args:
        db: Database session
        project_id: ID of project to delete
        current_user: User performing the deletion
        
    Returns:
        Soft-deleted project
        
    Raises:
        NotFoundException: If project not found
        ForbiddenException: If project already deleted
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise NotFoundException(
            detail=f"Project {project_id} not found",
            resource_type="project"
        )
    
    if project.is_deleted:
        raise ForbiddenException(
            detail="Project is already deleted"
        )
    
    # Mark as deleted
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    project.deleted_by_user_id = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return project


def restore_project(
    db: Session,
    project_id: UUID,
    current_user: User
) -> Project:
    """
    Restore a soft-deleted project.
    
    Args:
        db: Database session
        project_id: ID of project to restore
        current_user: User performing the restoration
        
    Returns:
        Restored project
        
    Raises:
        NotFoundException: If project not found
        ForbiddenException: If project not deleted
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise NotFoundException(
            detail=f"Project {project_id} not found",
            resource_type="project"
        )
    
    if not project.is_deleted:
        raise ForbiddenException(
            detail="Project is not deleted"
        )
    
    # Restore
    project.is_deleted = False
    project.deleted_at = None
    project.deleted_by_user_id = None
    
    db.commit()
    db.refresh(project)
    
    return project


def permanently_delete_project(
    db: Session,
    project_id: UUID,
    current_user: User
) -> dict:
    """
    Permanently delete a project from database.
    Only allowed for soft-deleted projects.
    
    Args:
        db: Database session
        project_id: ID of project to permanently delete
        current_user: User performing the deletion
        
    Returns:
        Success message
        
    Raises:
        NotFoundException: If project not found
        ForbiddenException: If project not soft-deleted first
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise NotFoundException(
            detail=f"Project {project_id} not found",
            resource_type="project"
        )
    
    if not project.is_deleted:
        raise ForbiddenException(
            detail="Project must be soft-deleted before permanent deletion"
        )
    
    # Permanently delete
    db.delete(project)
    db.commit()
    
    return {"message": f"Project {project_id} permanently deleted"}


def get_deleted_projects(
    db: Session,
    skip: int = 0,
    limit: int = 50
) -> list[Project]:
    """
    Get all soft-deleted projects.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of soft-deleted projects
    """
    return db.query(Project).filter(
        Project.is_deleted == True
    ).offset(skip).limit(limit).all()
