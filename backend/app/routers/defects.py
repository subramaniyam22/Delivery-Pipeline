from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role
from app.schemas import DefectCreate, DefectResponse, DefectUpdate, DefectValidateRequest
from app.deps import get_current_active_user
from app.services import defect_service
from app.rbac import check_full_access
from typing import List
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["defects"])


@router.post("/{project_id}/defects/create-draft", response_model=DefectResponse, status_code=status.HTTP_201_CREATED)
def create_defect_draft(
    project_id: UUID,
    data: DefectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create defect draft (Tester/Admin/Manager)"""
    allowed_roles = [Role.TESTER, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Tester, Admin, and Manager can create defect drafts"
        )
    
    defect = defect_service.create_defect_draft(db, project_id, data, current_user)
    return defect


@router.get("/{project_id}/defects", response_model=List[DefectResponse])
def list_defects(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all defects for a project (all authenticated users)"""
    defects = defect_service.get_defects_by_project(db, project_id)
    return defects


@router.post("/{project_id}/defects/validate", response_model=DefectResponse)
def validate_defect(
    project_id: UUID,
    defect_id: UUID,
    data: DefectValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate defect (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can validate defects"
        )
    
    defect = defect_service.validate_defect(
        db, defect_id, data.validation_result, data.notes, current_user
    )
    
    if not defect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Defect not found"
        )
    
    return defect


@router.put("/defects/{defect_id}", response_model=DefectResponse)
def update_defect(
    defect_id: UUID,
    data: DefectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update defect (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update defects"
        )
    
    defect = defect_service.update_defect(db, defect_id, data, current_user)
    
    if not defect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Defect not found"
        )
    
    return defect
