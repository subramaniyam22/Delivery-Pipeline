"""SLA Configuration Router - Admin Only"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db
from app.deps import get_current_user
from app.models import User, Role, SLAConfiguration, Project, Stage


router = APIRouter(prefix="/sla", tags=["SLA Configuration"])


# ============== Schemas ==============

class SLAConfigBase(BaseModel):
    stage: str
    default_days: int
    warning_threshold_days: int
    critical_threshold_days: int
    description: Optional[str] = None


class SLAConfigCreate(SLAConfigBase):
    pass


class SLAConfigUpdate(BaseModel):
    default_days: Optional[int] = None
    warning_threshold_days: Optional[int] = None
    critical_threshold_days: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SLAConfigResponse(SLAConfigBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDelayStatus(BaseModel):
    project_id: UUID
    project_title: str
    client_name: str
    current_stage: str
    is_delayed: bool
    delay_reason: Optional[str]
    days_in_stage: int
    sla_days: int
    status: str  # "ON_TRACK", "WARNING", "CRITICAL", "DELAYED"


class ExecutiveDashboard(BaseModel):
    total_projects: int
    on_track_count: int
    warning_count: int
    critical_count: int
    delayed_count: int
    projects_by_stage: dict
    delayed_projects: List[ProjectDelayStatus]


# ============== Helper Functions ==============

def check_admin(current_user: User):
    """Verify user is admin"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access SLA configuration"
        )


def calculate_project_delay_status(project: Project, sla_configs: dict) -> ProjectDelayStatus:
    """Calculate delay status for a project"""
    stage = project.current_stage.value
    sla_config = sla_configs.get(stage)
    
    # Get phase start date
    phase_start = project.phase_start_dates.get(stage) if project.phase_start_dates else None
    if phase_start:
        start_date = datetime.fromisoformat(phase_start) if isinstance(phase_start, str) else phase_start
        days_in_stage = (datetime.utcnow() - start_date).days
    else:
        days_in_stage = 0
    
    sla_days = sla_config.default_days if sla_config else 7
    warning_days = sla_config.warning_threshold_days if sla_config else 2
    critical_days = sla_config.critical_threshold_days if sla_config else 1
    
    remaining_days = sla_days - days_in_stage
    
    if project.is_delayed or remaining_days < 0:
        status = "DELAYED"
    elif remaining_days <= critical_days:
        status = "CRITICAL"
    elif remaining_days <= warning_days:
        status = "WARNING"
    else:
        status = "ON_TRACK"
    
    return ProjectDelayStatus(
        project_id=project.id,
        project_title=project.title,
        client_name=project.client_name,
        current_stage=stage,
        is_delayed=project.is_delayed,
        delay_reason=project.delay_reason,
        days_in_stage=days_in_stage,
        sla_days=sla_days,
        status=status
    )


# ============== Endpoints ==============

@router.get("/configurations", response_model=List[SLAConfigResponse])
def get_sla_configurations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all SLA configurations (Admin only)"""
    check_admin(current_user)
    
    configs = db.query(SLAConfiguration).filter(
        SLAConfiguration.is_active == True
    ).all()
    
    return configs


@router.put("/configurations/{stage}", response_model=SLAConfigResponse)
def update_sla_configuration(
    stage: str,
    update_data: SLAConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update SLA configuration for a stage (Admin only)"""
    check_admin(current_user)
    
    config = db.query(SLAConfiguration).filter(
        SLAConfiguration.stage == stage.upper()
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail=f"SLA configuration for stage {stage} not found")
    
    if update_data.default_days is not None:
        config.default_days = update_data.default_days
    if update_data.warning_threshold_days is not None:
        config.warning_threshold_days = update_data.warning_threshold_days
    if update_data.critical_threshold_days is not None:
        config.critical_threshold_days = update_data.critical_threshold_days
    if update_data.description is not None:
        config.description = update_data.description
    if update_data.is_active is not None:
        config.is_active = update_data.is_active
    
    db.commit()
    db.refresh(config)
    
    return config


@router.get("/executive-dashboard", response_model=ExecutiveDashboard)
def get_executive_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get executive dashboard with project delay overview (Admin only)"""
    check_admin(current_user)
    
    # Get all active projects
    projects = db.query(Project).filter(
        Project.status.in_(["DRAFT", "ACTIVE"])
    ).all()
    
    # Get SLA configs
    sla_configs_list = db.query(SLAConfiguration).filter(
        SLAConfiguration.is_active == True
    ).all()
    sla_configs = {c.stage: c for c in sla_configs_list}
    
    # Calculate status for each project
    on_track = 0
    warning = 0
    critical = 0
    delayed = 0
    delayed_projects = []
    projects_by_stage = {}
    
    for project in projects:
        status = calculate_project_delay_status(project, sla_configs)
        
        if status.status == "ON_TRACK":
            on_track += 1
        elif status.status == "WARNING":
            warning += 1
            delayed_projects.append(status)
        elif status.status == "CRITICAL":
            critical += 1
            delayed_projects.append(status)
        elif status.status == "DELAYED":
            delayed += 1
            delayed_projects.append(status)
        
        # Count by stage
        stage = project.current_stage.value
        projects_by_stage[stage] = projects_by_stage.get(stage, 0) + 1
    
    # Sort delayed projects by severity
    severity_order = {"DELAYED": 0, "CRITICAL": 1, "WARNING": 2}
    delayed_projects.sort(key=lambda x: severity_order.get(x.status, 3))
    
    return ExecutiveDashboard(
        total_projects=len(projects),
        on_track_count=on_track,
        warning_count=warning,
        critical_count=critical,
        delayed_count=delayed,
        projects_by_stage=projects_by_stage,
        delayed_projects=delayed_projects
    )


@router.post("/mark-delayed/{project_id}")
def mark_project_delayed(
    project_id: UUID,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a project as delayed (Admin/Manager only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_delayed = True
    project.delay_reason = reason
    db.commit()
    
    return {"message": "Project marked as delayed", "project_id": str(project_id)}


@router.post("/resolve-delay/{project_id}")
def resolve_project_delay(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a delayed project as resolved (Admin/Manager only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_delayed = False
    project.delay_reason = None
    db.commit()
    
    return {"message": "Project delay resolved", "project_id": str(project_id)}
