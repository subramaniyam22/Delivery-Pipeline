from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import AdminConfigResponse, AdminConfigUpdate
from app.deps import get_current_active_user
from app.services import config_service
from app.rbac import check_full_access
from typing import List

router = APIRouter(prefix="/admin/config", tags=["admin-config"])


@router.get("", response_model=List[AdminConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all configuration keys (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can access configuration"
        )
    
    configs = config_service.get_all_configs(db)
    return configs


@router.get("/{key}", response_model=AdminConfigResponse)
def get_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get configuration by key (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can access configuration"
        )
    
    config = config_service.get_config(db, key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    return config


@router.put("/{key}", response_model=AdminConfigResponse)
def update_config(
    key: str,
    data: AdminConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update configuration (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update configuration"
        )
    
    config = config_service.update_config(db, key, data.value_json, current_user)
    return config
