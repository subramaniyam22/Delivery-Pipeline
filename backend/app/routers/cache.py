"""
Cache management and statistics endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.deps import get_current_active_user
from app.models import User, Role
from app.services.cache_service import cache_service
from app.utils.cache import invalidate_cache
from typing import Dict, Any

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats")
def get_cache_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get cache statistics (Admin only)."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view cache stats"
        )
    
    return cache_service.get_cache_stats()


@router.post("/invalidate/projects")
def invalidate_projects_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Invalidate all project caches (Admin only)."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can invalidate cache"
        )
    
    cache_service.invalidate_all_projects()
    return {"message": "Project caches invalidated"}


@router.post("/invalidate/users")
def invalidate_users_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Invalidate all user caches (Admin only)."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can invalidate cache"
        )
    
    invalidate_cache("user:*")
    return {"message": "User caches invalidated"}


@router.post("/invalidate/all")
def invalidate_all_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Invalidate all caches (Admin only - use with caution!)."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can invalidate cache"
        )
    
    invalidate_cache("*")
    return {"message": "All caches invalidated"}
