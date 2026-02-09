from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import AdminConfigResponse, AdminConfigUpdate, PreviewStrategy
from app.deps import get_current_active_user
from app.services import config_service
from app.rbac import require_admin_manager
from typing import List, Optional

router = APIRouter(prefix="/admin/config", tags=["admin-config"])


@router.get("", response_model=List[AdminConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all configuration keys (Admin/Manager only)"""
    require_admin_manager(current_user)
    
    configs = config_service.get_all_configs(db)
    return configs


@router.get("/{key}", response_model=AdminConfigResponse)
def get_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get configuration by key (Admin/Manager only)"""
    require_admin_manager(current_user)
    
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
    current_user: User = Depends(get_current_active_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Update configuration (Admin/Manager only)"""
    require_admin_manager(current_user)

    if key == "preview_strategy":
        if not isinstance(data.value_json, str) or data.value_json not in {item.value for item in PreviewStrategy}:
            allowed = ", ".join(item.value for item in PreviewStrategy)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"preview_strategy must be one of: {allowed}",
            )

    expected_version = data.version
    if if_match:
        cleaned = if_match.replace('W/', '').replace('"', '').strip()
        if cleaned.isdigit():
            header_version = int(cleaned)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="If-Match must be an integer version.",
            )
        if expected_version is not None and expected_version != header_version:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="If-Match and payload version do not match.",
            )
        expected_version = header_version

    config = config_service.update_config(db, key, data.value_json, current_user, expected_version=expected_version)
    return config
