"""
Capacity Management API Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from uuid import UUID
from pydantic import BaseModel, Field

from app.db import get_db
from app.models import User, Role, Region
from app.deps import get_current_active_user
from app.rbac import check_full_access
from app.services.capacity_service import (
    CapacityService, 
    CapacitySuggestionService,
    get_capacity_service,
    get_suggestion_service
)

router = APIRouter(prefix="/capacity", tags=["capacity"])


# ==================== Schemas ====================

class CapacityConfigUpdate(BaseModel):
    daily_hours: Optional[float] = None
    weekly_hours: Optional[float] = None
    buffer_percentage: Optional[float] = None
    is_active: Optional[bool] = None


class CapacityConfigResponse(BaseModel):
    id: str
    role: str
    region: Optional[str]
    daily_hours: float
    weekly_hours: float
    buffer_percentage: float
    is_active: bool


class UserCapacityResponse(BaseModel):
    user_id: str
    user_name: str
    role: str
    region: Optional[str]
    period_start: str
    period_end: str
    total_hours: float
    allocated_hours: float
    remaining_hours: float
    utilization_percentage: float
    active_projects: int
    capacity_status: Optional[str] = None
    is_recommended: Optional[bool] = None
    assignment_score: Optional[float] = None


class AllocationRequest(BaseModel):
    user_id: str
    project_id: str
    date: str  # ISO format
    hours: float
    workload_id: Optional[str] = None


class SuggestionFeedbackRequest(BaseModel):
    was_accepted: bool
    feedback_notes: Optional[str] = None
    actual_outcome: Optional[str] = None


class ManualInputRequest(BaseModel):
    input_type: str  # 'actual_hours', 'complexity', 'efficiency', 'feedback'
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    context: Optional[dict] = None


# ==================== Configuration Endpoints ====================

@router.get("/configs", response_model=List[CapacityConfigResponse])
def list_capacity_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all capacity configurations"""
    service = get_capacity_service(db)
    configs = service.list_capacity_configs()
    return [
        CapacityConfigResponse(
            id=str(c.id),
            role=c.role.value,
            region=c.region.value if c.region else None,
            daily_hours=c.daily_hours,
            weekly_hours=c.weekly_hours,
            buffer_percentage=c.buffer_percentage,
            is_active=c.is_active
        )
        for c in configs
    ]


@router.put("/configs/{config_id}", response_model=CapacityConfigResponse)
def update_capacity_config(
    config_id: UUID,
    updates: CapacityConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update capacity configuration (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update capacity configurations"
        )
    
    service = get_capacity_service(db)
    try:
        config = service.update_capacity_config(config_id, updates.model_dump(exclude_unset=True))
        return CapacityConfigResponse(
            id=str(config.id),
            role=config.role.value,
            region=config.region.value if config.region else None,
            daily_hours=config.daily_hours,
            weekly_hours=config.weekly_hours,
            buffer_percentage=config.buffer_percentage,
            is_active=config.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== User Capacity Endpoints ====================

@router.get("/users/{user_id}/summary")
def get_user_capacity_summary(
    user_id: UUID,
    weeks: int = Query(default=2, ge=1, le=8),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get capacity summary for a specific user"""
    service = get_capacity_service(db)
    try:
        return service.get_user_capacity_summary(user_id, weeks)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/available-users/{role}")
def get_available_users_for_role(
    role: str,
    min_hours: float = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available users for a specific role with capacity information"""
    try:
        role_enum = Role(role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    
    service = get_capacity_service(db)
    today = date.today()
    end_date = today + timedelta(weeks=2)
    
    return service.get_available_users_by_role(role_enum, today, end_date, min_hours)


@router.get("/team-overview")
def get_team_capacity_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get capacity overview for all active team members"""
    service = get_capacity_service(db)
    
    # Get all active users (excluding Admin and Manager)
    users = db.query(User).filter(
        User.is_active == True,
        User.is_archived == False,
        User.role.in_([Role.CONSULTANT, Role.PC, Role.BUILDER, Role.TESTER])
    ).all()
    
    overview = {
        "by_role": {},
        "by_region": {},
        "total_users": len(users),
        "total_available_hours": 0,
        "total_allocated_hours": 0,
        "generated_at": datetime.utcnow().isoformat()
    }
    
    for user in users:
        try:
            summary = service.get_user_capacity_summary(user.id, weeks=2)
            
            # By Role
            role = user.role.value
            if role not in overview["by_role"]:
                overview["by_role"][role] = {
                    "count": 0,
                    "total_hours": 0,
                    "allocated_hours": 0,
                    "remaining_hours": 0,
                    "users": []
                }
            overview["by_role"][role]["count"] += 1
            overview["by_role"][role]["total_hours"] += summary["total_hours"]
            overview["by_role"][role]["allocated_hours"] += summary["allocated_hours"]
            overview["by_role"][role]["remaining_hours"] += summary["remaining_hours"]
            overview["by_role"][role]["users"].append({
                "id": str(user.id),
                "name": user.name,
                "utilization": summary["utilization_percentage"],
                "remaining_hours": summary["remaining_hours"]
            })
            
            # By Region
            region = user.region.value if user.region else "UNASSIGNED"
            if region not in overview["by_region"]:
                overview["by_region"][region] = {
                    "count": 0,
                    "total_hours": 0,
                    "remaining_hours": 0
                }
            overview["by_region"][region]["count"] += 1
            overview["by_region"][region]["total_hours"] += summary["total_hours"]
            overview["by_region"][region]["remaining_hours"] += summary["remaining_hours"]
            
            # Totals
            overview["total_available_hours"] += summary["total_hours"]
            overview["total_allocated_hours"] += summary["allocated_hours"]
        except Exception as e:
            print(f"Error getting capacity for user {user.id}: {e}")
    
    # Calculate overall utilization
    if overview["total_available_hours"] > 0:
        overview["overall_utilization"] = round(
            (overview["total_allocated_hours"] / overview["total_available_hours"]) * 100, 1
        )
    else:
        overview["overall_utilization"] = 0
    
    return overview


# ==================== Allocation Endpoints ====================

@router.post("/allocate")
def allocate_capacity(
    allocation: AllocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Allocate capacity hours to a project"""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.PC]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, and PC can allocate capacity"
        )
    
    service = get_capacity_service(db)
    try:
        target_date = date.fromisoformat(allocation.date)
        result = service.allocate_capacity(
            user_id=UUID(allocation.user_id),
            project_id=UUID(allocation.project_id),
            target_date=target_date,
            hours=allocation.hours,
            workload_id=UUID(allocation.workload_id) if allocation.workload_id else None
        )
        return {
            "success": True,
            "allocation_id": str(result.id),
            "message": f"Allocated {allocation.hours}h on {allocation.date}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Suggestion Endpoints ====================

@router.get("/suggestions/{project_id}/{role}")
def get_assignment_suggestions(
    project_id: UUID,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get AI-powered assignment suggestions for a project and role"""
    try:
        role_enum = Role(role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    
    service = get_suggestion_service(db)
    try:
        return service.generate_assignment_suggestions(project_id, role_enum)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/suggestions/{suggestion_id}/feedback")
def record_suggestion_feedback(
    suggestion_id: UUID,
    feedback: SuggestionFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record feedback on a suggestion for AI learning"""
    service = get_suggestion_service(db)
    try:
        result = service.record_suggestion_feedback(
            suggestion_id=suggestion_id,
            was_accepted=feedback.was_accepted,
            feedback_notes=feedback.feedback_notes,
            actual_outcome=feedback.actual_outcome
        )
        return {
            "success": True,
            "message": "Feedback recorded successfully",
            "suggestion_id": str(result.id)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Manual Input Endpoints ====================

@router.post("/manual-input")
def record_manual_capacity_input(
    input_data: ManualInputRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Record manual capacity input for AI learning"""
    service = get_suggestion_service(db)
    
    role_enum = None
    region_enum = None
    
    if input_data.role:
        try:
            role_enum = Role(input_data.role.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {input_data.role}")
    
    if input_data.region:
        try:
            region_enum = Region(input_data.region.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {input_data.region}")
    
    result = service.record_manual_input(
        input_type=input_data.input_type,
        created_by_user_id=current_user.id,
        user_id=UUID(input_data.user_id) if input_data.user_id else None,
        project_id=UUID(input_data.project_id) if input_data.project_id else None,
        role=role_enum,
        region=region_enum,
        value_numeric=input_data.value_numeric,
        value_text=input_data.value_text,
        context=input_data.context
    )
    
    return {
        "success": True,
        "input_id": str(result.id),
        "message": f"Manual input recorded for AI learning"
    }


# ==================== Project Workload Endpoints ====================

@router.get("/projects/{project_id}/workload")
def get_project_workload_estimate(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get workload estimate for a project"""
    from app.models import Project
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    service = get_capacity_service(db)
    return service.estimate_project_workload(project)
