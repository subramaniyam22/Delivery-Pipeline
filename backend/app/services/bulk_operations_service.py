"""
Bulk operations service for efficient batch processing.
"""
from sqlalchemy.orm import Session
from uuid import UUID
from app.models import Project, ProjectStatus, User, Role
from app.custom_exceptions import ValidationException, ForbiddenException
from typing import List, Dict, Any
from datetime import datetime


def bulk_update_status(
    db: Session,
    project_ids: List[UUID],
    new_status: ProjectStatus,
    current_user: User
) -> Dict[str, Any]:
    """
    Update status for multiple projects at once.
    
    Args:
        db: Database session
        project_ids: List of project IDs to update
        new_status: New status to apply
        current_user: User performing the update
        
    Returns:
        Summary of updates
        
    Raises:
        ValidationException: If no projects found
        ForbiddenException: If user lacks permission
    """
    # Check permissions
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise ForbiddenException(
            detail="Only Admins and Managers can perform bulk updates",
            required_role="ADMIN or MANAGER"
        )
    
    # Find projects
    projects = db.query(Project).filter(
        Project.id.in_(project_ids),
        Project.is_deleted == False
    ).all()
    
    if not projects:
        raise ValidationException(
            detail="No valid projects found for update"
        )
    
    # Update all projects
    updated_count = 0
    for project in projects:
        project.status = new_status
        project.updated_at = datetime.utcnow()
        updated_count += 1
    
    db.commit()
    
    return {
        "updated_count": updated_count,
        "requested_count": len(project_ids),
        "new_status": new_status.value,
        "updated_by": current_user.name
    }


def bulk_assign_team_member(
    db: Session,
    project_ids: List[UUID],
    role: str,
    user_id: UUID,
    current_user: User
) -> Dict[str, Any]:
    """
    Assign a team member to multiple projects at once.
    
    Args:
        db: Database session
        project_ids: List of project IDs
        role: Role to assign (consultant, builder, tester, pc)
        user_id: ID of user to assign
        current_user: User performing the assignment
        
    Returns:
        Summary of assignments
    """
    # Check permissions
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise ForbiddenException(
            detail="Only Admins and Managers can perform bulk assignments"
        )
    
    # Validate role
    valid_roles = ['consultant', 'builder', 'tester', 'pc']
    if role not in valid_roles:
        raise ValidationException(
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            field="role"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValidationException(
            detail=f"User {user_id} not found",
            field="user_id"
        )
    
    # Find projects
    projects = db.query(Project).filter(
        Project.id.in_(project_ids),
        Project.is_deleted == False
    ).all()
    
    if not projects:
        raise ValidationException(
            detail="No valid projects found for assignment"
        )
    
    # Assign to all projects
    updated_count = 0
    role_field_map = {
        'consultant': 'consultant_user_id',
        'builder': 'builder_user_id',
        'tester': 'tester_user_id',
        'pc': 'pc_user_id'
    }
    
    field_name = role_field_map[role]
    for project in projects:
        setattr(project, field_name, user_id)
        project.updated_at = datetime.utcnow()
        updated_count += 1
    
    db.commit()
    
    return {
        "assigned_count": updated_count,
        "requested_count": len(project_ids),
        "role": role,
        "user_name": user.name,
        "assigned_by": current_user.name
    }


def bulk_archive_projects(
    db: Session,
    project_ids: List[UUID],
    current_user: User
) -> Dict[str, Any]:
    """
    Archive (soft delete) multiple projects at once.
    
    Args:
        db: Database session
        project_ids: List of project IDs to archive
        current_user: User performing the archival
        
    Returns:
        Summary of archived projects
    """
    # Check permissions
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise ForbiddenException(
            detail="Only Admins and Managers can perform bulk archive"
        )
    
    # Find projects
    projects = db.query(Project).filter(
        Project.id.in_(project_ids),
        Project.is_deleted == False
    ).all()
    
    if not projects:
        raise ValidationException(
            detail="No valid projects found for archival"
        )
    
    # Archive all projects
    archived_count = 0
    for project in projects:
        project.is_deleted = True
        project.deleted_at = datetime.utcnow()
        project.deleted_by_user_id = current_user.id
        archived_count += 1
    
    db.commit()
    
    return {
        "archived_count": archived_count,
        "requested_count": len(project_ids),
        "archived_by": current_user.name,
        "archived_at": datetime.utcnow().isoformat()
    }
