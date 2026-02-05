"""
Router for soft delete and bulk operations on projects.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, ProjectStatus
from app.deps import get_current_active_user
from app.services.soft_delete_service import (
    soft_delete_project,
    restore_project,
    permanently_delete_project,
    get_deleted_projects
)
from app.services.bulk_operations_service import (
    bulk_update_status,
    bulk_assign_team_member,
    bulk_archive_projects
)
from typing import List
from uuid import UUID
from pydantic import BaseModel


# Request schemas
class BulkStatusUpdateRequest(BaseModel):
    project_ids: List[UUID]
    new_status: ProjectStatus


class BulkAssignmentRequest(BaseModel):
    project_ids: List[UUID]
    role: str  # consultant, builder, tester, pc
    user_id: UUID


class BulkArchiveRequest(BaseModel):
    project_ids: List[UUID]


router = APIRouter(prefix="/projects", tags=["projects-bulk"])


# Soft Delete Endpoints
@router.delete("/{project_id}/soft", status_code=status.HTTP_200_OK)
def soft_delete_project_endpoint(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete a project (Admin/Manager only)"""
    return soft_delete_project(db, project_id, current_user)


@router.post("/{project_id}/restore", status_code=status.HTTP_200_OK)
def restore_project_endpoint(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Restore a soft-deleted project (Admin only)"""
    if current_user.role != Role.ADMIN:
        from app.custom_exceptions import ForbiddenException
        raise ForbiddenException(
            detail="Only Admins can restore deleted projects",
            required_role="ADMIN"
        )
    return restore_project(db, project_id, current_user)


@router.delete("/{project_id}/permanent", status_code=status.HTTP_200_OK)
def permanently_delete_project_endpoint(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Permanently delete a project (Admin only)"""
    if current_user.role != Role.ADMIN:
        from app.custom_exceptions import ForbiddenException
        raise ForbiddenException(
            detail="Only Admins can permanently delete projects",
            required_role="ADMIN"
        )
    return permanently_delete_project(db, project_id, current_user)


@router.get("/deleted", status_code=status.HTTP_200_OK)
def list_deleted_projects(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all soft-deleted projects (Admin/Manager only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        from app.custom_exceptions import ForbiddenException
        raise ForbiddenException(
            detail="Only Admins and Managers can view deleted projects",
            required_role="ADMIN or MANAGER"
        )
    return get_deleted_projects(db, skip, limit)


# Bulk Operations Endpoints
@router.post("/bulk/status", status_code=status.HTTP_200_OK)
def bulk_update_project_status(
    request: BulkStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk update project status (Admin/Manager only)"""
    return bulk_update_status(
        db,
        request.project_ids,
        request.new_status,
        current_user
    )


@router.post("/bulk/assign", status_code=status.HTTP_200_OK)
def bulk_assign_team_member_endpoint(
    request: BulkAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk assign team member to projects (Admin/Manager only)"""
    return bulk_assign_team_member(
        db,
        request.project_ids,
        request.role,
        request.user_id,
        current_user
    )


@router.post("/bulk/archive", status_code=status.HTTP_200_OK)
def bulk_archive_projects_endpoint(
    request: BulkArchiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk archive (soft delete) projects (Admin/Manager only)"""
    return bulk_archive_projects(
        db,
        request.project_ids,
        current_user
    )
