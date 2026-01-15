from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Project, Region, ProjectTask, SLAConfiguration
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    OnboardingUpdateRequest,
    StageStatusUpdateRequest,
    TeamAssignmentRequest
)
from app.deps import get_current_active_user
from app.services import project_service
from app.rbac import check_full_access, can_access_stage
from app.models import Stage, TaskStatus
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])


def calculate_project_health(project: Project, sla_configs: Dict[str, SLAConfiguration]) -> Dict[str, Any]:
    stage = project.current_stage.value
    sla_config = sla_configs.get(stage)

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

    return {
        "status": status,
        "days_in_stage": days_in_stage,
        "sla_days": sla_days,
        "warning_threshold_days": warning_days,
        "critical_threshold_days": critical_days,
        "remaining_days": remaining_days
    }


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project (Consultant/Admin/Manager)"""
    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Consultant, Admin, and Manager can create projects"
        )
    
    project = project_service.create_project(db, data, current_user)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all projects (all authenticated users)"""
    from sqlalchemy.orm import joinedload
    projects = db.query(Project).options(
        joinedload(Project.creator),
        joinedload(Project.consultant),
        joinedload(Project.pc),
        joinedload(Project.builder),
        joinedload(Project.tester)
    ).all()
    return projects


@router.get("/available-users/{role}")
def get_available_users_by_role(
    role: str,
    region: Optional[str] = Query(None, description="Filter by region (INDIA, US, PH)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all available users for a specific role, filtered by region for managers"""
    try:
        role_enum = Role(role.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    
    query = db.query(User).filter(
        User.role == role_enum,
        User.is_active == True,
        User.is_archived == False
    )
    
    # Manager can only see users from their own region
    if current_user.role == Role.MANAGER and current_user.region:
        query = query.filter(User.region == current_user.region)
    # PC can only see users from India region (for Builder/Tester assignment)
    elif current_user.role == Role.PC:
        if role_enum in [Role.BUILDER, Role.TESTER]:
            query = query.filter(User.region == Region.INDIA)
        else:
            # PC cannot assign Consultant or PC
            return []
    # Optional region filter
    elif region:
        try:
            region_enum = Region(region.upper())
            query = query.filter(User.region == region_enum)
        except ValueError:
            pass
    
    users = query.all()
    
    return [
        {"id": str(u.id), "name": u.name, "email": u.email, "region": u.region.value if u.region else None}
        for u in users
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get project details (all authenticated users)"""
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update project metadata (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update project metadata"
        )
    
    project = project_service.update_project(db, project_id, data, current_user)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.post("/{project_id}/onboarding/update")
def update_onboarding(
    project_id: UUID,
    data: OnboardingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update onboarding data (Consultant/Admin/Manager)"""
    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Consultant, Admin, and Manager can update onboarding"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Store onboarding data in project context (could be a separate table in production)
    # For MVP, we'll use the workflow context
    return {"success": True, "message": "Onboarding data updated"}


@router.post("/{project_id}/assignment/publish")
def publish_assignment(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Publish assignment plan (PC/Admin/Manager)"""
    allowed_roles = [Role.PC, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PC, Admin, and Manager can publish assignment"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.ASSIGNMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in ASSIGNMENT stage"
        )
    
    return {"success": True, "message": "Assignment plan published"}


@router.post("/{project_id}/build/status")
def update_build_status(
    project_id: UUID,
    data: StageStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update build status (Builder/Admin/Manager)"""
    allowed_roles = [Role.BUILDER, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Builder, Admin, and Manager can update build status"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.BUILD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in BUILD stage"
        )
    
    return {
        "success": True,
        "message": f"Build status updated to {data.status.value}",
        "notes": data.notes
    }


@router.get("/{project_id}/phase-summary")
def get_phase_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get task completion summary for each phase (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can access phase summaries"
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    stage_map: Dict[str, Dict[str, Any]] = {}

    for stage in Stage:
        stage_map[stage.value] = {
            "stage": stage.value,
            "total_tasks": 0,
            "completed_tasks": 0,
            "pending_tasks": 0,
            "completion_percentage": 0
        }

    for task in tasks:
        stage_key = task.stage.value
        stage_entry = stage_map.get(stage_key)
        if not stage_entry:
            continue
        stage_entry["total_tasks"] += 1
        if task.status == TaskStatus.DONE:
            stage_entry["completed_tasks"] += 1
        else:
            stage_entry["pending_tasks"] += 1

    for stage_entry in stage_map.values():
        total = stage_entry["total_tasks"]
        stage_entry["completion_percentage"] = int((stage_entry["completed_tasks"] / total) * 100) if total else 0

    sla_configs_list = db.query(SLAConfiguration).filter(SLAConfiguration.is_active == True).all()
    sla_configs = {c.stage: c for c in sla_configs_list}
    health_summary = calculate_project_health(project, sla_configs)

    return {
        "project_id": str(project.id),
        "current_stage": project.current_stage.value,
        "phase_summaries": list(stage_map.values()),
        "health": health_summary
    }


@router.post("/{project_id}/test/status")
def update_test_status(
    project_id: UUID,
    data: StageStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update test status (Tester/Admin/Manager)"""
    allowed_roles = [Role.TESTER, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Tester, Admin, and Manager can update test status"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.current_stage != Stage.TEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not in TEST stage"
        )
    
    return {
        "success": True,
        "message": f"Test status updated to {data.status.value}",
        "notes": data.notes
    }


@router.post("/{project_id}/complete/close")
def close_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Close project (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can close projects"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    from app.models import ProjectStatus
    project.status = ProjectStatus.COMPLETED
    project.current_stage = Stage.COMPLETE
    db.commit()
    
    return {"success": True, "message": "Project closed successfully"}


@router.post("/{project_id}/team/assign", response_model=ProjectResponse)
def assign_team(
    project_id: UUID,
    data: TeamAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign team members to a project with role-based restrictions:
    - Admin: Can assign anyone
    - Manager: Can only assign users from their own region
    - PC: Can only assign Builder and Tester for India region
    
    Assignment sequence: Consultant → PC → Builder → Tester
    """
    # Check basic role permission
    allowed_roles = [Role.PC, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, and PC can assign team members"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # PC can only assign Builder and Tester, and only for India region
    if current_user.role == Role.PC:
        if data.consultant_user_id or data.pc_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PC can only assign Builder and Tester"
            )
        # PC must be from India region to assign
        if current_user.region != Region.INDIA:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only India region PC can assign Builder and Tester"
            )
    
    # Helper function to check region restriction for managers
    def check_manager_region(user: User, role_name: str):
        if current_user.role == Role.MANAGER and current_user.region:
            if user.region != current_user.region:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Manager can only assign {role_name} from their own region ({current_user.region.value})"
                )
    
    # Helper function to check PC region restriction (India only for Builder/Tester)
    def check_pc_region(user: User, role_name: str):
        if current_user.role == Role.PC:
            if user.region != Region.INDIA:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"PC can only assign {role_name} from India region"
                )
    
    # ============ Sequential Assignment Validation ============
    # Consultant must be assigned first (if trying to assign Consultant, no checks needed)
    # PC can only be assigned after Consultant
    # Builder can only be assigned after PC
    # Tester can only be assigned after Builder
    
    # Validate Consultant assignment
    if data.consultant_user_id:
        consultant = db.query(User).filter(User.id == data.consultant_user_id).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Consultant not found")
        if consultant.role != Role.CONSULTANT:
            raise HTTPException(status_code=400, detail="Selected user is not a Consultant")
        check_manager_region(consultant, "Consultant")
        project.consultant_user_id = data.consultant_user_id
    
    # Validate PC assignment - requires Consultant to be assigned first
    if data.pc_user_id:
        if not project.consultant_user_id and not data.consultant_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consultant must be assigned before PC"
            )
        pc_user = db.query(User).filter(User.id == data.pc_user_id).first()
        if not pc_user:
            raise HTTPException(status_code=404, detail="PC user not found")
        if pc_user.role != Role.PC:
            raise HTTPException(status_code=400, detail="Selected user is not a PC")
        check_manager_region(pc_user, "PC")
        project.pc_user_id = data.pc_user_id
    
    # Validate Builder assignment - requires PC to be assigned first
    if data.builder_user_id:
        if not project.pc_user_id and not data.pc_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PC must be assigned before Builder"
            )
        builder = db.query(User).filter(User.id == data.builder_user_id).first()
        if not builder:
            raise HTTPException(status_code=404, detail="Builder not found")
        if builder.role != Role.BUILDER:
            raise HTTPException(status_code=400, detail="Selected user is not a Builder")
        check_manager_region(builder, "Builder")
        check_pc_region(builder, "Builder")
        project.builder_user_id = data.builder_user_id
    
    # Validate Tester assignment - requires Builder to be assigned first
    if data.tester_user_id:
        if not project.builder_user_id and not data.builder_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Builder must be assigned before Tester"
            )
        tester = db.query(User).filter(User.id == data.tester_user_id).first()
        if not tester:
            raise HTTPException(status_code=404, detail="Tester not found")
        if tester.role != Role.TESTER:
            raise HTTPException(status_code=400, detail="Selected user is not a Tester")
        check_manager_region(tester, "Tester")
        check_pc_region(tester, "Tester")
        project.tester_user_id = data.tester_user_id
    
    db.commit()
    db.refresh(project)
    
    return project


@router.get("/{project_id}/team")
def get_team_assignments(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get team assignments for a project
    Only Admin, Manager, and PC can view team assignments
    """
    # Check if user can view team assignments
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.PC]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, and PC can view team assignments"
        )
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    team = {}
    
    # Include can_assign flag to help frontend determine assignment permissions
    can_assign_all = current_user.role == Role.ADMIN
    can_assign_region = current_user.role == Role.MANAGER
    can_assign_builder_tester = current_user.role == Role.PC and current_user.region == Region.INDIA
    
    if project.consultant_user_id:
        consultant = db.query(User).filter(User.id == project.consultant_user_id).first()
        if consultant:
            team["consultant"] = {
                "id": str(consultant.id), 
                "name": consultant.name, 
                "email": consultant.email, 
                "role": consultant.role.value,
                "region": consultant.region.value if consultant.region else None
            }
    
    if project.pc_user_id:
        pc = db.query(User).filter(User.id == project.pc_user_id).first()
        if pc:
            team["pc"] = {
                "id": str(pc.id), 
                "name": pc.name, 
                "email": pc.email, 
                "role": pc.role.value,
                "region": pc.region.value if pc.region else None
            }
    
    if project.builder_user_id:
        builder = db.query(User).filter(User.id == project.builder_user_id).first()
        if builder:
            team["builder"] = {
                "id": str(builder.id), 
                "name": builder.name, 
                "email": builder.email, 
                "role": builder.role.value,
                "region": builder.region.value if builder.region else None
            }
    
    if project.tester_user_id:
        tester = db.query(User).filter(User.id == project.tester_user_id).first()
        if tester:
            team["tester"] = {
                "id": str(tester.id), 
                "name": tester.name, 
                "email": tester.email, 
                "role": tester.role.value,
                "region": tester.region.value if tester.region else None
            }
    
    return {
        "team": team,
        "permissions": {
            "can_assign_consultant": can_assign_all or can_assign_region,
            "can_assign_pc": can_assign_all or can_assign_region,
            "can_assign_builder": can_assign_all or can_assign_region or can_assign_builder_tester,
            "can_assign_tester": can_assign_all or can_assign_region or can_assign_builder_tester,
            "user_region": current_user.region.value if current_user.region else None
        },
        "assignment_sequence": {
            "consultant_assigned": project.consultant_user_id is not None,
            "pc_assigned": project.pc_user_id is not None,
            "builder_assigned": project.builder_user_id is not None,
            "tester_assigned": project.tester_user_id is not None,
            "next_to_assign": (
                "consultant" if not project.consultant_user_id else
                "pc" if not project.pc_user_id else
                "builder" if not project.builder_user_id else
                "tester" if not project.tester_user_id else
                "complete"
            )
        }
    }
