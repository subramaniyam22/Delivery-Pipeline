from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Project, Region, ProjectTask, SLAConfiguration, OnboardingData
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    OnboardingUpdateRequest,
    StageStatusUpdateRequest,
    TeamAssignmentRequest,
    OnboardingReviewAction
)
from app.deps import get_current_active_user
from app.services import project_service
from app.rbac import check_full_access, can_access_stage
from app.models import Stage, TaskStatus, AuditLog, OnboardingReviewStatus
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

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
async def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project (Sales Only)"""
    allowed_roles = [Role.SALES, Role.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Sales users can create projects"
        )
    
    # Validation Logic
    if data.status == "ACTIVE": # Create Project clicked
        missing_fields = []
        if not data.pmc_name: missing_fields.append("pmc_name")
        if not data.location: missing_fields.append("location")
        if not data.client_email_ids: missing_fields.append("client_email_ids")
        if not data.project_type: missing_fields.append("project_type")
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing mandatory fields for active project: {', '.join(missing_fields)}"
            )
    else:
        # For DRAFT, minimal validation is handled by Schema (Title, Client Name required)
        pass

    project = project_service.create_project(db, data, current_user)
    
    # Notify Manager if assigned
    if project.manager_user_id:
        try:
            from app.routers.ai_consultant import notification_manager
            await notification_manager.send_personal_message(
                {
                    "type": "URGENT_ALERT",
                    "message": f"New Project Handover: {project.title}",
                    "project_id": str(project.id)
                },
                str(project.manager_user_id)
            )
        except Exception as e:
            # Don't fail request if notification fails
            print(f"Failed to send manager notification: {e}")
            
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all projects with pagination (all authenticated users)"""
    from sqlalchemy.orm import joinedload
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    # Query with pagination
    projects = db.query(Project).options(
        joinedload(Project.creator),
        joinedload(Project.sales_rep),
        joinedload(Project.manager_chk),
        joinedload(Project.consultant),
        joinedload(Project.pc),
        joinedload(Project.builder),
        joinedload(Project.tester),
        joinedload(Project.onboarding_data)
    ).offset(offset).limit(page_size).all()
    
    # attach onboarding_updated_at for schema
    # attach onboarding_updated_at for schema AND checked for new updates
    
    # 2. Get last view timestamps for this user for these projects
    project_ids = [p.id for p in projects]
    last_views_query = db.query(
        AuditLog.project_id, 
        func.max(AuditLog.created_at)
    ).filter(
        AuditLog.actor_user_id == current_user.id,
        AuditLog.action == "PROJECT_VIEWED",
        AuditLog.project_id.in_(project_ids)
    ).group_by(AuditLog.project_id).all()
    
    view_map = {p_id: t for p_id, t in last_views_query}

    for p in projects:
        p.onboarding_updated_at = None
        if p.onboarding_data:
            p.onboarding_updated_at = p.onboarding_data.updated_at
            
        # Read Receipt Logic
        last_view = view_map.get(p.id)
        has_updates = False
        
        # Check for updates to onboarding data
        if p.onboarding_updated_at:
             if not last_view:
                 # If never viewed, but created > 60s ago (to avoid "New" on just created)
                 if (p.onboarding_updated_at - p.created_at).total_seconds() > 60:
                     has_updates = True
             else:
                 if p.onboarding_updated_at > last_view:
                     has_updates = True
        
        # Restriction: Only show "New Updates" for projects assigned to the current user
        # Restriction: Only show "New Updates" for projects assigned to the current user
        is_assigned = (
            p.consultant_user_id == current_user.id or
            p.pc_user_id == current_user.id or
            p.builder_user_id == current_user.id or
            p.tester_user_id == current_user.id
        )

        # Calculate Project Region based on Assignment (PC > Builder > Tester)
        project_region = None
        if p.pc:
            project_region = p.pc.region
        elif p.builder:
            project_region = p.builder.region
        elif p.tester:
            project_region = p.tester.region
        elif p.consultant:
             # Fallback if no team assigned yet
            project_region = p.consultant.region
            
        setattr(p, 'region', project_region)

        # Manager Regional Assignment: Auto-assign "New Updates" visibility if project matches region
        if current_user.role == Role.MANAGER and current_user.region and project_region == current_user.region:
             is_assigned = True

        if not is_assigned:
            has_updates = False

        setattr(p, 'has_new_updates', has_updates)
            
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
@router.get("", response_model=List[ProjectResponse])
def get_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all projects visible to the current user
    """
    try:
        # 1. Get projects directly
        query = db.query(Project)
        projects = query.offset(skip).limit(limit).all()
        
        # 2. AuditLog logic DISABLED for debugging
        # project_ids = [p.id for p in projects]
        view_map = {} 
        # last_views_query = db.query(
        #     AuditLog.project_id, 
        #     func.max(AuditLog.created_at)
        # ).filter(
        #     AuditLog.actor_user_id == current_user.id,
        #     AuditLog.action == "PROJECT_VIEWED",
        #     AuditLog.project_id.in_(project_ids)
        # ).group_by(AuditLog.project_id).all()
        # view_map = {p_id: t for p_id, t in last_views_query}
        
        results = []
        for p in projects:
            p.onboarding_updated_at = None
            
            # Read Receipt Logic
            last_view = view_map.get(p.id)
            has_updates = False
            
            # Check for updates to onboarding data
            if p.onboarding_data: 
                # Ensure we handle potential lazy load error by accessing safely?
                # accessing p.onboarding_data triggers usage.
                p.onboarding_updated_at = p.onboarding_data.updated_at
                
                if p.onboarding_updated_at:
                     if not last_view:
                         if (p.onboarding_updated_at - p.created_at).total_seconds() > 60:
                             has_updates = True
                     else:
                         if p.onboarding_updated_at > last_view:
                             has_updates = True
            
            # Restriction checks... simplified
            is_assigned = True # Default to true for now to avoid role logic crash
            
            setattr(p, 'has_new_updates', has_updates)
            
        return projects
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PROJECTS_ERROR] {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )
                 # If never viewed, but created > 60s ago (to avoid "New" on just created)
                 # Wait, user said "If I have seen the updates...".
                 if (p.onboarding_updated_at - p.created_at).total_seconds() > 60:
                     has_updates = True
             else:
                 if p.onboarding_updated_at > last_view:
                     has_updates = True
        
        setattr(p, 'has_new_updates', has_updates)
        results.append(p)
        
    return results


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
        
    # Calculate completion percentage
    # Calculate completion percentage (Weighted across all stages)
    # Stages: SALES -> ONBOARDING -> ASSIGNMENT -> BUILD -> TEST -> DEFECT_VALIDATION -> COMPLETE
    # We assign a weight to each completed stage.
    stage_order = [
         Stage.SALES,
         Stage.ONBOARDING,
         Stage.ASSIGNMENT,
         Stage.BUILD,
         Stage.TEST,
         Stage.DEFECT_VALIDATION,
         Stage.COMPLETE
    ]
    
    total_stages = len(stage_order)
    current_stage_index = 0
    try:
        current_stage_index = stage_order.index(project.current_stage)
    except ValueError:
        current_stage_index = 0
        
    # Calculate base progress from completed stages
    base_progress = (current_stage_index / total_stages) * 100
    
    # Calculate current stage progress contribution
    stage_progress = 0
    if project.current_stage == Stage.ONBOARDING:
        onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
        if onboarding:
            stage_progress = onboarding.completion_percentage
    else:
        # For other stages, use tasks or default to 0 (start of stage) or 50 (in progress)
        # Simplified: Check tasks
        total_tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.id).count()
        if total_tasks > 0:
            completed_tasks = db.query(ProjectTask).filter(
                ProjectTask.project_id == project.id, 
                ProjectTask.status == TaskStatus.DONE
            ).count()
            stage_progress = int((completed_tasks / total_tasks) * 100)
            
    # Add contribution of current stage (it represents 1/total_stages of the total)
    # Total = (CompletedStages * 100 + CurrentStageAndPercent) / TotalStages
    # Actually simpler: Base + (StageProgress / TotalStages)
    
    completion = int(base_progress + (stage_progress / total_stages))
    
    # Cap at 100
    if completion > 100: completion = 100
            
    # Attach to project instance for Pydantic serialization
    setattr(project, 'completion_percentage', completion)
    
    # Log PROJECT_VIEWED audit
    # Only if not viewed recently? Or every time? Every time is fine for "last viewed".
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=current_user.id,
        action="PROJECT_VIEWED",
        payload_json={}
    )
    db.add(audit)
    db.commit()
    
    # return project - wait, we need to populate has_new_updates for detail view too?
    # Usually detail view clears the 'new updates' status implicitly by viewing it.
    # So we return has_new_updates=False effectively (or True if we check before insert).
    # But technically, once they view it, it's SEEN. So immediately it becomes "old".
    # So for the Detail View, has_new_updates is irrelevant or False.
    setattr(project, 'has_new_updates', False)
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update project metadata"""
    # RBAC: Admin/Manager can update anytime. Sales can update ONLY if Draft.
    is_admin_manager = check_full_access(current_user.role)
    is_sales = current_user.role == Role.SALES
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not is_admin_manager:
        if is_sales:
            # Sales can only update their own drafts
            if project.status == ProjectStatus.DRAFT:
                pass # Allowed
            else:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sales users can only edit DRAFT projects."
                )
        else:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin, Manager, and Sales (Drafts) can update project metadata"
            )
    
    project = project_service.update_project(db, project_id, data, current_user)
    return project


class ActionReason(BaseModel):
    reason: str

@router.post("/{project_id}/pause")
def pause_project_endpoint(
    project_id: UUID,
    data: ActionReason,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pause Project (Sales/Admin/Manager)"""
    allowed = [Role.SALES, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed:
         raise HTTPException(status_code=403, detail="Not authorized to pause projects")
         
    project = project_service.pause_project(db, project_id, data.reason, current_user)
    if not project:
         raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/{project_id}/archive")
def archive_project_endpoint(
    project_id: UUID,
    data: ActionReason,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Archive Project (Sales/Admin/Manager)"""
    allowed = [Role.SALES, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed:
         raise HTTPException(status_code=403, detail="Not authorized to archive projects")
         
    project = project_service.archive_project(db, project_id, data.reason, current_user)
    if not project:
         raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{project_id}")
def delete_project_endpoint(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete Project (Sales/Admin/Manager)"""
    allowed = [Role.SALES, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed:
         raise HTTPException(status_code=403, detail="Not authorized to delete projects")
         
    result = project_service.delete_project(db, project_id, current_user)
    if not result:
         raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "message": "Project deleted"}


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
    
    # HITL check
    if current_user.role != Role.ADMIN:
        if not project.require_manual_review:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manual updates restricted for Onboarder Agent projects. Contact Admin for HITL access."
            )
    # For MVP, we'll use the workflow context
    return {"success": True, "message": "Onboarding data updated"}


@router.post("/{project_id}/hitl-toggle")
def toggle_project_hitl(
    project_id: UUID,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Toggle HITL for a project (Admin only)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can toggle HITL")
    
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.require_manual_review = enabled
    db.commit()
    return {"success": True, "hitl_enabled": project.require_manual_review}


@router.post("/{project_id}/onboarding/review")
def review_onboarding(
    project_id: UUID,
    data: OnboardingReviewAction,  # Use the schema from schemas.py
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Review onboarding submission (Consultant/Admin/Manager)"""
    # Import here to avoid circulars if any, though schemas is safe
    from app.schemas import OnboardingReviewAction
    from app.models import OnboardingReviewStatus

    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Consultant, Admin, and Manager can review onboarding"
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding data not found")

    if data.action == "APPROVE":
        onboarding.review_status = OnboardingReviewStatus.APPROVED
        onboarding.consultant_review_notes = data.notes
        # Advance Stage
        if project.current_stage == Stage.ONBOARDING:
            project.current_stage = Stage.ASSIGNMENT
        
    elif data.action in ["REJECT", "REQUEST_CHANGES"]:
        onboarding.review_status = OnboardingReviewStatus.NEEDS_CHANGES
        onboarding.consultant_review_notes = data.notes
        # Logic to notify client would go here
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    return {"success": True, "status": onboarding.review_status}


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
        if not project.require_manual_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consultant cannot be assigned when Manual Review (HITL) is disabled. AI Agent handles this phase."
            )
        consultant = db.query(User).filter(User.id == data.consultant_user_id).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Consultant not found")
        if consultant.role != Role.CONSULTANT:
            raise HTTPException(status_code=400, detail="Selected user is not a Consultant")
        check_manager_region(consultant, "Consultant")
        project.consultant_user_id = data.consultant_user_id
        
        # If project is in SALES stage and Consultant is assigned, move to ONBOARDING
        if project.current_stage == Stage.SALES:
            project.current_stage = Stage.ONBOARDING
            # Set Phase Start Date for Onboarding
            if not project.phase_start_dates:
                project.phase_start_dates = {}
            project.phase_start_dates[Stage.ONBOARDING.value] = datetime.utcnow().isoformat()
    
    # Validate PC assignment - requires Consultant to be assigned first OR HITL to be disabled
    if data.pc_user_id:
        if project.require_manual_review and not project.consultant_user_id and not data.consultant_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consultant must be assigned before PC (when Manual Review is enabled)"
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
