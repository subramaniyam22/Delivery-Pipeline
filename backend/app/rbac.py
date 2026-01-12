from fastapi import HTTPException, status
from app.models import Role, Stage
from typing import List, Callable
from functools import wraps


# Permission mapping for each role
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "full_access": True,
        "manage_users": True,
        "manage_config": True,
        "approve_workflow": True,
        "all_stages": True,
    },
    Role.MANAGER: {
        "full_access": True,
        "manage_users": True,
        "manage_config": True,
        "approve_workflow": True,
        "all_stages": True,
    },
    Role.CONSULTANT: {
        "create_project": True,
        "view_all": True,
        "update_onboarding": True,
    },
    Role.PC: {
        "view_all": True,
        "manage_assignment": True,
        "allowed_stages": [Stage.ASSIGNMENT],
    },
    Role.BUILDER: {
        "view_project": True,
        "allowed_stages": [Stage.BUILD],
    },
    Role.TESTER: {
        "view_project": True,
        "allowed_stages": [Stage.TEST],
        "create_defects": True,
    },
}


def has_permission(user_role: Role, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return ROLE_PERMISSIONS.get(user_role, {}).get(permission, False)


def can_access_stage(user_role: Role, stage: Stage) -> bool:
    """Check if a role can access a specific stage"""
    perms = ROLE_PERMISSIONS.get(user_role, {})
    
    # Admin and Manager have access to all stages
    if perms.get("all_stages"):
        return True
    
    # Check if stage is in allowed stages
    allowed_stages = perms.get("allowed_stages", [])
    return stage in allowed_stages


def require_role(required_role: Role):
    """Dependency to require a specific role"""
    def dependency(current_user):
        if current_user.role != required_role and current_user.role not in [Role.ADMIN, Role.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return current_user
    return dependency


def require_any_role(required_roles: List[Role]):
    """Dependency to require any of the specified roles"""
    def dependency(current_user):
        if current_user.role not in required_roles and current_user.role not in [Role.ADMIN, Role.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in required_roles]}"
            )
        return current_user
    return dependency


def require_stage_permission(stage: Stage):
    """Dependency to require permission for a specific stage"""
    def dependency(current_user):
        if not can_access_stage(current_user.role, stage):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You don't have permission for stage: {stage.value}"
            )
        return current_user
    return dependency


def check_full_access(user_role: Role) -> bool:
    """Check if user has full access (Admin or Manager)"""
    return user_role in [Role.ADMIN, Role.MANAGER]


def check_can_manage_projects(user_role: Role) -> bool:
    """Check if user can manage projects (Admin, Manager, Consultant, PC, Tester)"""
    return user_role in [Role.ADMIN, Role.MANAGER, Role.CONSULTANT, Role.PC, Role.TESTER]


def check_admin_or_manager(current_user) -> bool:
    """Check if user is Admin or Manager (not a dependency, use get_admin_or_manager instead)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Manager role required."
        )
    return current_user


def get_admin_or_manager_dependency():
    """Create a dependency that requires Admin or Manager role"""
    from app.deps import get_current_user
    from fastapi import Depends
    
    async def _check(current_user = Depends(get_current_user)):
        if current_user.role not in [Role.ADMIN, Role.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admin or Manager role required."
            )
        return current_user
    
    return _check