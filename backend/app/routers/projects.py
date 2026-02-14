from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Project, Region, ProjectTask, SLAConfiguration, OnboardingData, ProjectStatus, ProjectConfig, Stage, StageOutput, TaskStatus, AuditLog, OnboardingReviewStatus, StageStatus, PipelineEvent, DeliveryOutcome
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    OnboardingUpdateRequest,
    StageStatusUpdateRequest,
    TeamAssignmentRequest,
    OnboardingReviewAction
)
from app.schemas import ProjectConfigUpdate, ProjectConfigResponse, StageOutputResponse, DeliveryOutcomeCreate, DeliveryOutcomeResponse
from app.deps import get_current_active_user
from app.services import project_service, artifact_service, config_service
from app.rbac import check_full_access, can_access_stage, require_admin_manager
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any
from uuid import UUID
import os
import uuid
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/projects", tags=["projects"])


class AutoAssignRequest(BaseModel):
    force: bool = False


class AssignmentOverrideRequest(BaseModel):
    role: str  # consultant | builder | tester
    user_id: UUID
    comment: Optional[str] = None


class GenerateClientPreviewRequest(BaseModel):
    force: bool = False


def _normalize_locations(value: Optional[str], names: Optional[List[str]]) -> List[str]:
    if names:
        return [item.strip() for item in names if isinstance(item, str) and item.strip()]
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


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
        if not data.title or not data.title.strip(): missing_fields.append("title")
        if not data.client_name or not data.client_name.strip(): missing_fields.append("client_name")
        if not data.pmc_name: missing_fields.append("pmc_name")
        if not _normalize_locations(data.location, data.location_names): missing_fields.append("location")
        if not data.client_email_ids: missing_fields.append("client_email_ids")
        if not data.project_type: missing_fields.append("project_type")
        if not data.description or not data.description.strip(): missing_fields.append("description")
        if not data.priority: missing_fields.append("priority")
        
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
            from app.services.notification_service import notification_manager
            await notification_manager.send_personal_message(
                {
                    "type": "URGENT_ALERT",
                    "message": f"New Project Handover: {project.title}",
                    "project_id": str(project.id)
                },
                str(project.manager_user_id),
                db
            )
        except Exception as e:
            # Don't fail request if notification fails
            print(f"Failed to send manager notification: {e}")
            
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    mine: bool = Query(False, description="Filter projects based on current user role"),
    assigned: bool = Query(False, description="Filter projects assigned to current user"),
    stage: Optional[str] = Query(None, description="Filter by current stage"),
    needs_assignment: bool = Query(False, description="Filter projects needing assignment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all projects with pagination (all authenticated users)"""
    from sqlalchemy.orm import joinedload
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    def _parse_stage(value: str) -> Stage:
        normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
        try:
            return Stage[normalized]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage: {value}"
            )

    query = db.query(Project).options(
        joinedload(Project.creator),
        joinedload(Project.sales_rep),
        joinedload(Project.manager_chk),
        joinedload(Project.consultant),
        joinedload(Project.pc),
        joinedload(Project.builder),
        joinedload(Project.tester),
        joinedload(Project.onboarding_data)
    )

    if stage:
        query = query.filter(Project.current_stage == _parse_stage(stage))

    if mine:
        if current_user.role == Role.CONSULTANT:
            query = query.filter(Project.consultant_user_id == current_user.id)
        elif current_user.role == Role.SALES:
            query = query.filter(Project.created_by_user_id == current_user.id)
        else:
            query = query.filter(or_(
                Project.consultant_user_id == current_user.id,
                Project.pc_user_id == current_user.id,
                Project.builder_user_id == current_user.id,
                Project.tester_user_id == current_user.id,
                Project.manager_user_id == current_user.id,
                Project.sales_user_id == current_user.id
            ))

    if assigned:
        query = query.filter(or_(
            Project.consultant_user_id == current_user.id,
            Project.pc_user_id == current_user.id,
            Project.builder_user_id == current_user.id,
            Project.tester_user_id == current_user.id,
            Project.manager_user_id == current_user.id,
            Project.sales_user_id == current_user.id
        ))

    if needs_assignment:
        query = query.filter(
            Project.current_stage == Stage.ASSIGNMENT,
            Project.pc_user_id.is_(None)
        )

    # Query with pagination
    projects = query.offset(offset).limit(page_size).all()
    
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
        if p.current_stage == Stage.SALES:
            p = project_service.auto_advance_sales_if_complete(db, p)
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
        
        for p in projects:
            if p.current_stage == Stage.SALES:
                p = project_service.auto_advance_sales_if_complete(db, p)
            p.onboarding_updated_at = None
            
            # Read Receipt Logic
            last_view = view_map.get(p.id)
            has_updates = False
            
            # Check for updates to onboarding data
            if p.onboarding_data:
                p.onboarding_updated_at = p.onboarding_data.updated_at
                
                if p.onboarding_updated_at:
                    if not last_view:
                        if (p.onboarding_updated_at - p.created_at).total_seconds() > 60:
                            has_updates = True
                    else:
                        if p.onboarding_updated_at > last_view:
                            has_updates = True
            
            # Restriction checks... simplified
            is_assigned = True  # Default to true for now to avoid role logic crash
            
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

    # Resolve HITL state (global + per-project)
    global_gates = {}
    try:
        global_config = config_service.get_config(db, "global_stage_gates_json")
        if global_config and global_config.value_json:
            global_gates = global_config.value_json or {}
    except Exception:
        global_gates = {}

    project_config = db.query(ProjectConfig).filter(ProjectConfig.project_id == project.id).first()
    project_gates = project_config.stage_gates_json if project_config and project_config.stage_gates_json else {}

    def _gate_active_for_stage(stage: Stage) -> bool:
        key = stage.value.lower()
        return bool(global_gates.get(key)) or bool(project_gates.get(key))

    hitl_enabled = bool(
        any(bool(v) for v in (global_gates or {}).values()) or
        any(bool(v) for v in (project_gates or {}).values())
    )

    pending_approvals: List[Dict[str, Any]] = []
    if project.current_stage and _gate_active_for_stage(project.current_stage):
        latest_output = (
            db.query(StageOutput)
            .filter(
                StageOutput.project_id == project.id,
                StageOutput.stage == project.current_stage,
            )
            .order_by(StageOutput.created_at.desc())
            .first()
        )
        if latest_output and latest_output.status == StageStatus.NEEDS_HUMAN:
            pending_approvals.append(
                {
                    "stage": project.current_stage.value,
                    "type": "hitl_gate",
                    "created_at": latest_output.created_at,
                    "approver_roles": ["ADMIN", "MANAGER"],
                }
            )

    setattr(project, "hitl_enabled", hitl_enabled)
    setattr(project, "pending_approvals", pending_approvals)
    setattr(project, "pending_approvals_count", len(pending_approvals))
    
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


@router.put("/{project_id}")
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
    
    # Validation Logic for moving to ACTIVE
    if data.status == ProjectStatus.ACTIVE:
        if isinstance(data.status, str):
             # pydantic handles enum conversion usually, but just in case
             pass
        
        # Check current values combined with update values
        pmc_name = data.pmc_name or project.pmc_name
        location = data.location or project.location
        location_names = data.location_names or project.location_names
        client_email_ids = data.client_email_ids or project.client_email_ids
        project_type = data.project_type or project.project_type
        title = data.title or project.title
        client_name = data.client_name or project.client_name
        description = data.description or project.description
        priority = data.priority or project.priority
        
        missing_fields = []
        if not title or not title.strip(): missing_fields.append("title")
        if not client_name or not client_name.strip(): missing_fields.append("client_name")
        if not pmc_name: missing_fields.append("pmc_name")
        if not _normalize_locations(location, location_names): missing_fields.append("location")
        if not client_email_ids: missing_fields.append("client_email_ids")
        if not project_type: missing_fields.append("project_type")
        if not description or not description.strip(): missing_fields.append("description")
        if not priority: missing_fields.append("priority")
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing mandatory fields for active project: {', '.join(missing_fields)}"
            )

    try:
        project = project_service.update_project(db, project_id, data, current_user)
        return {"status": "success", "id": str(project.id), "message": "Project updated successfully"}
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        print(f"Error updating project: {e}\n{trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


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
    """Toggle HITL for a project (Admin/Manager)"""
    require_admin_manager(current_user)
    
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
    """Review onboarding submission (Admin/Manager)"""
    # Import here to avoid circulars if any, though schemas is safe
    from app.schemas import OnboardingReviewAction
    from app.models import OnboardingReviewStatus

    require_admin_manager(current_user)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding data not found")

    if data.action == "APPROVE":
        onboarding.review_status = OnboardingReviewStatus.APPROVED
        onboarding.consultant_review_notes = data.notes
        # Advance Stage only if client has submitted onboarding (prevents moving before client shares info)
        if project.current_stage == Stage.ONBOARDING and getattr(onboarding, "submitted_at", None):
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
            "completion_percentage": 0,
            "started_at": project.phase_start_dates.get(stage.value) if project.phase_start_dates else None,
            "sla_risk": None
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
    if project.current_stage and project.current_stage.value in stage_map:
        stage_map[project.current_stage.value]["sla_risk"] = health_summary["status"]

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
    previous_stage = project.current_stage
    project.status = ProjectStatus.COMPLETED
    project.current_stage = Stage.COMPLETE
    project_service.record_stage_transition(project, previous_stage, project.current_stage, str(current_user.id))
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
            project_service.record_stage_transition(project, Stage.SALES, Stage.ONBOARDING, str(current_user.id))
    
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

    try:
        from app.services.contract_service import create_or_update_contract
        create_or_update_contract(db, project_id, source="user:assignment_update")
    except Exception:
        pass
    try:
        from app.services.hitl_service import invalidate_pending_approvals_if_stale
        invalidate_pending_approvals_if_stale(db, project_id)
    except Exception:
        pass
    try:
        from app.services.pipeline_orchestrator import auto_advance
        auto_advance(db, project_id, trigger_source="assignment_updated")
    except Exception:
        pass  # do not fail the request if autopilot advance fails

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


@router.post("/{project_id}/auto-assign")
def auto_assign_project(
    project_id: UUID,
    body: AutoAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Enqueue auto-assignment job (Admin/Manager only)."""
    require_admin_manager(current_user)
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    from app.jobs.queue import enqueue_job
    job_id = enqueue_job(
        project_id=project_id,
        stage=Stage.ASSIGNMENT,
        payload_json={"force": body.force},
        request_id=None,
        actor_user_id=current_user.id,
        db=db,
        requested_by="user",
        requested_by_user_id=current_user.id,
    )
    return {"message": "Auto-assignment job enqueued", "job_id": str(job_id)}


@router.get("/{project_id}/assignments")
def get_project_assignments(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return current consultant/builder/tester assignments and rationale (Admin/Manager/PC)."""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.PC]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin, Manager, and PC can view assignments")
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    team = {}
    for attr, key in [("consultant_user_id", "consultant"), ("builder_user_id", "builder"), ("tester_user_id", "tester")]:
        uid = getattr(project, attr)
        if uid:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                team[key] = {"id": str(u.id), "name": u.name, "email": u.email, "role": u.role.value}
    rationale = getattr(project, "assignment_rationale_json", None) or {}
    return {"team": team, "rationale": rationale}


@router.post("/{project_id}/assignments/override")
def override_assignment(
    project_id: UUID,
    body: AssignmentOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Override assignment for a role (Admin/Manager only). Updates counts, rationale, emits event, triggers auto_advance."""
    require_admin_manager(current_user)
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    role_map = {"consultant": "consultant_user_id", "builder": "builder_user_id", "tester": "tester_user_id"}
    if body.role not in role_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be consultant, builder, or tester")
    attr = role_map[body.role]
    new_user = db.query(User).filter(User.id == body.user_id).first()
    if not new_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    from app.jobs.auto_assignment import _dec_user_assignment_count, _inc_user_assignment_count
    from app.services.contract_service import create_or_update_contract
    from app.services.pipeline_orchestrator import auto_advance
    old_id = getattr(project, attr)
    _dec_user_assignment_count(db, old_id)
    setattr(project, attr, body.user_id)
    _inc_user_assignment_count(db, body.user_id)
    rationale = dict(getattr(project, "assignment_rationale_json", None) or {})
    role_key = body.role
    rationale[role_key] = {
        "user_id": str(body.user_id),
        "reasons": [body.comment or "Manual override"],
        "score": None,
        "auto_assigned": False,
        "overridden_by": str(current_user.id),
        "override_comment": body.comment,
    }
    project.assignment_rationale_json = rationale
    db.add(PipelineEvent(project_id=project_id, stage_key="2_assignment", event_type="ASSIGNMENT_OVERRIDDEN", details_json={"role": body.role, "user_id": str(body.user_id), "comment": body.comment}))
    try:
        create_or_update_contract(db, project_id, source="user:assignment_override")
    except Exception:
        pass
    db.commit()
    try:
        auto_advance(db, project_id, trigger_source="assignment_override")
    except Exception:
        pass
    return {"message": "Assignment overridden", "role": body.role, "user_id": str(body.user_id)}


@router.post("/{project_id}/generate-client-preview")
def generate_client_preview(
    project_id: UUID,
    body: GenerateClientPreviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Enqueue client preview pipeline (Admin/Manager only). Runs in background."""
    require_admin_manager(current_user)
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    def _run():
        from app.jobs.client_preview import run_client_preview_pipeline
        run_client_preview_pipeline(project_id, force=body.force)

    background_tasks.add_task(_run)
    return {"message": "Client preview generation started", "project_id": str(project_id)}


@router.get("/{project_id}/client-preview")
def get_client_preview(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return client preview url, thumbnail, status, last_generated_at, error."""
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    # Allow project members and Admin/Manager
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        if current_user.id not in (
            project.consultant_user_id,
            project.pc_user_id,
            project.builder_user_id,
            project.tester_user_id,
            project.manager_user_id,
            project.sales_user_id,
            project.created_by_user_id,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this project's preview")
    return {
        "preview_url": getattr(project, "client_preview_url", None),
        "thumbnail_url": getattr(project, "client_preview_thumbnail_url", None),
        "status": getattr(project, "client_preview_status", "not_generated"),
        "last_generated_at": project.client_preview_last_generated_at.isoformat() if getattr(project, "client_preview_last_generated_at", None) else None,
        "error": getattr(project, "client_preview_error", None),
    }


@router.post("/{project_id}/delivery-outcome", response_model=DeliveryOutcomeResponse, status_code=status.HTTP_201_CREATED)
def record_delivery_outcome(
    project_id: UUID,
    data: DeliveryOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Record delivery outcome for a project (Prompt 9). Admin/Manager or project members."""
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        if current_user.id not in (
            project.consultant_user_id,
            project.pc_user_id,
            project.builder_user_id,
            project.tester_user_id,
            project.manager_user_id,
            project.sales_user_id,
            project.created_by_user_id,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to record delivery outcome")
    outcome = DeliveryOutcome(
        project_id=project_id,
        template_registry_id=data.template_registry_id,
        cycle_time_days=data.cycle_time_days,
        defect_count=data.defect_count,
        reopened_defects_count=data.reopened_defects_count,
        on_time_delivery=data.on_time_delivery,
        final_quality_score=data.final_quality_score,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


@router.get("/{project_id}/config", response_model=ProjectConfigResponse)
def get_project_config(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can access project config"
        )
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    config = db.query(ProjectConfig).filter(ProjectConfig.project_id == project_id).first()
    if not config:
        config = ProjectConfig(project_id=project_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/{project_id}/config", response_model=ProjectConfigResponse)
def update_project_config(
    project_id: UUID,
    data: ProjectConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update project config"
        )
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    config = db.query(ProjectConfig).filter(ProjectConfig.project_id == project_id).first()
    if not config:
        config = ProjectConfig(project_id=project_id)
        db.add(config)

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


@router.get("/{project_id}/stage-outputs", response_model=List[StageOutputResponse])
def list_stage_outputs(
    project_id: UUID,
    stage: Optional[Stage] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    query = db.query(StageOutput).filter(StageOutput.project_id == project_id)
    if stage:
        query = query.filter(StageOutput.stage == stage)
    return query.order_by(StageOutput.created_at.desc()).all()


@router.post("/{project_id}/checklists/build", status_code=status.HTTP_201_CREATED)
async def upload_build_checklist(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [Role.ADMIN, Role.MANAGER, Role.BUILDER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, or Builder can upload build checklist"
        )
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Checklist exceeds 10MB limit")

    filename = os.path.basename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"checklist-build-{uuid.uuid4()}{ext or '.json'}"
    content = await file.read()

    artifact = artifact_service.create_artifact_from_bytes(
        db=db,
        project_id=project_id,
        stage=Stage.BUILD,
        filename=safe_name,
        content=content,
        artifact_type="checklist_build",
        uploaded_by_user_id=current_user.id,
        metadata_json={"original_filename": filename, "content_type": file.content_type},
    )
    return {"artifact_id": str(artifact.id), "filename": artifact.filename}


@router.post("/{project_id}/checklists/qa", status_code=status.HTTP_201_CREATED)
async def upload_qa_checklist(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [Role.ADMIN, Role.MANAGER, Role.TESTER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, or Tester can upload QA checklist"
        )
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Checklist exceeds 10MB limit")

    filename = os.path.basename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"checklist-qa-{uuid.uuid4()}{ext or '.json'}"
    content = await file.read()

    artifact = artifact_service.create_artifact_from_bytes(
        db=db,
        project_id=project_id,
        stage=Stage.TEST,
        filename=safe_name,
        content=content,
        artifact_type="checklist_qa",
        uploaded_by_user_id=current_user.id,
        metadata_json={"original_filename": filename, "content_type": file.content_type},
    )
    return {"artifact_id": str(artifact.id), "filename": artifact.filename}
