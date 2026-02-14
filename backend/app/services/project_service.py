from sqlalchemy.orm import Session
from app.models import Project, StageOutput, ProjectStatus, Stage, AuditLog
from app.schemas import ProjectCreate, ProjectUpdate
from app.agents.workflow_graph import execute_workflow_stage
from app.services.cache_service import cache_service
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


def _normalize_locations(value: Optional[str], names: Optional[List[str]]) -> List[str]:
    if names:
        return [item.strip() for item in names if isinstance(item, str) and item.strip()]
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]

def _record_stage_transition(
    project: Project,
    from_stage: Optional[Stage],
    to_stage: Optional[Stage],
    actor_user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    if from_stage == to_stage:
        return
    timestamp = datetime.utcnow().isoformat()
    history = project.stage_history or []
    history.append(
        {
            "from_stage": from_stage.value if from_stage else None,
            "to_stage": to_stage.value if to_stage else None,
            "at": timestamp,
            "actor_user_id": actor_user_id,
            "request_id": request_id,
        }
    )
    project.stage_history = history
    if to_stage:
        project.phase_start_dates = project.phase_start_dates or {}
        if not project.phase_start_dates.get(to_stage.value):
            project.phase_start_dates[to_stage.value] = timestamp


def record_stage_transition(
    project: Project,
    from_stage: Optional[Stage],
    to_stage: Optional[Stage],
    actor_user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    _record_stage_transition(project, from_stage, to_stage, actor_user_id, request_id)

def _is_sales_requirements_complete(
    title: Optional[str],
    client_name: Optional[str],
    pmc_name: Optional[str],
    location_names: Optional[List[str]],
    client_email_ids: Optional[str],
    project_type: Optional[str],
    description: Optional[str],
    priority: Optional[str],
) -> bool:
    return (
        bool(title and title.strip()) and
        bool(client_name and client_name.strip()) and
        bool(pmc_name and pmc_name.strip()) and
        bool(location_names) and
        bool(client_email_ids and client_email_ids.strip()) and
        bool(project_type and project_type.strip()) and
        bool(description and description.strip()) and
        bool(priority)
    )


def create_project(db: Session, data: ProjectCreate, user) -> Project:
    """Create a new project"""
    location_names = _normalize_locations(data.location, data.location_names)
    location_display = ", ".join(location_names) if location_names else data.location
    is_complete = _is_sales_requirements_complete(
        data.title,
        data.client_name,
        data.pmc_name,
        location_names,
        data.client_email_ids,
        data.project_type,
        data.description,
        data.priority,
    )
    moved_to_onboarding = False
    if data.status == ProjectStatus.DRAFT:
        status = ProjectStatus.DRAFT
        current_stage = Stage.SALES
    elif is_complete or data.status == ProjectStatus.ACTIVE:
        status = ProjectStatus.ACTIVE
        current_stage = Stage.ONBOARDING
        moved_to_onboarding = True
    else:
        status = data.status or ProjectStatus.DRAFT
        current_stage = Stage.SALES
    project = Project(
        title=data.title,
        client_name=data.client_name,
        description=data.description,
        priority=data.priority,
        status=status,
        current_stage=current_stage,
        created_by_user_id=user.id,
        # Sales Fields
        pmc_name=data.pmc_name,
        location=location_display,
        location_names=location_names or None,
        client_email_ids=data.client_email_ids,
        project_type=data.project_type,
        estimated_revenue_usd=getattr(data, "estimated_revenue_usd", None),
        manager_user_id=None # Manager assignment removed
    )
    _record_stage_transition(project, None, current_stage, str(user.id))
    if moved_to_onboarding:
        project.phase_start_dates = project.phase_start_dates or {}
        project.phase_start_dates[Stage.ONBOARDING.value] = datetime.utcnow().isoformat()
    
    # Auto-assign sales_user_id if creator is Sales
    from app.models import Role
    if user.role == Role.SALES:
        project.sales_user_id = user.id
    db.add(project)
    db.flush() # Flush to get project.id
    
    # Create audit log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="PROJECT_CREATED",
        payload_json={"title": data.title, "client_name": data.client_name}
    )
    db.add(audit)
    
    # Trigger Onboarder Agent validation only when onboarding starts
    if moved_to_onboarding:
        from app.services.onboarding_agent_service import OnboarderAgentService
        onboarding_service = OnboarderAgentService(db)
        onboarding_service.validate_initial_project_data(project.id)
    
    # Commit everything at once
    db.commit()
    db.refresh(project)
    
    # Invalidate project list cache
    cache_service.invalidate_all_projects()
    
    return project


def get_project(db: Session, project_id: UUID) -> Optional[Project]:
    """Get project by ID"""
    from sqlalchemy.orm import joinedload
    return db.query(Project).options(
        joinedload(Project.creator),
        joinedload(Project.sales_rep),
        joinedload(Project.manager_chk),
        joinedload(Project.consultant),
        joinedload(Project.pc),
        joinedload(Project.builder),
        joinedload(Project.tester),
        joinedload(Project.onboarding_data)
    ).filter(Project.id == project_id).first()


def update_project(db: Session, project_id: UUID, data: ProjectUpdate, user) -> Optional[Project]:
    """Update project metadata"""
    project = get_project(db, project_id)
    if not project:
        return None
    
    previous_stage = project.current_stage
    
    # Data for DB update (keep Enums as objects)
    update_data = data.model_dump(exclude_unset=True)
    if "location_names" in update_data or "location" in update_data:
        location_names = _normalize_locations(update_data.get("location"), update_data.get("location_names"))
        update_data["location_names"] = location_names or None
        update_data["location"] = ", ".join(location_names) if location_names else update_data.get("location")
    for key, value in update_data.items():
        setattr(project, key, value)

    normalized_locations = _normalize_locations(project.location, project.location_names)
    moved_to_onboarding = False
    if _is_sales_requirements_complete(
        project.title,
        project.client_name,
        project.pmc_name,
        normalized_locations,
        project.client_email_ids,
        project.project_type,
        project.description,
        project.priority,
    ):
        should_auto_advance = project.status != ProjectStatus.DRAFT
        if "status" in update_data and update_data.get("status") == ProjectStatus.ACTIVE:
            should_auto_advance = True
        if should_auto_advance and (project.status != ProjectStatus.ACTIVE or project.current_stage == Stage.SALES):
            project.status = ProjectStatus.ACTIVE
            project.current_stage = Stage.ONBOARDING
            moved_to_onboarding = True
    if previous_stage != project.current_stage:
        _record_stage_transition(project, previous_stage, project.current_stage, str(user.id))
        if previous_stage == Stage.SALES and project.current_stage == Stage.ONBOARDING:
            moved_to_onboarding = True
    
    # CACHE DISABLED FOR DEBUGGING
    # try:
    #     cache_service.invalidate_project(str(project.id))
    #     cache_service.invalidate_all_projects()
    # except Exception as e:
    #     print(f"Cache error: {e}")
    
    db.commit()
    db.refresh(project)
    
    if moved_to_onboarding:
        try:
            from app.services.onboarding_agent_service import OnboarderAgentService
            OnboarderAgentService(db).validate_initial_project_data(project.id)
        except Exception as e:
            print(f"[ONBOARDING_EMAIL] Failed to trigger onboarding email: {e}")
    
    # Create audit log (convert Enums to strings for JSON)
    json_payload = data.model_dump(mode='json', exclude_unset=True)
    
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="PROJECT_UPDATED",
        payload_json=json_payload
    )
    db.add(audit)
    db.commit()
    
    return project


def auto_advance_sales_if_complete(db: Session, project: Project) -> Project:
    normalized_locations = _normalize_locations(project.location, project.location_names)
    if project.current_stage != Stage.SALES:
        return project
    if project.status == ProjectStatus.DRAFT:
        return project
    if not _is_sales_requirements_complete(
        project.title,
        project.client_name,
        project.pmc_name,
        normalized_locations,
        project.client_email_ids,
        project.project_type,
        project.description,
        project.priority,
    ):
        return project

    project.status = ProjectStatus.ACTIVE
    project.current_stage = Stage.ONBOARDING
    _record_stage_transition(project, Stage.SALES, Stage.ONBOARDING, None)
    db.commit()
    db.refresh(project)

    try:
        from app.services.onboarding_agent_service import OnboarderAgentService
        OnboarderAgentService(db).validate_initial_project_data(project.id)
    except Exception as e:
        print(f"[ONBOARDING_EMAIL] Failed to trigger onboarding email: {e}")

    return project


def advance_workflow(db: Session, project_id: UUID, user, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Advance project workflow to next stage
    Executes LangGraph workflow and creates StageOutput
    """
    project = get_project(db, project_id)
    if not project:
        return {"error": "Project not found"}
    
    # Gather context for workflow
    artifacts = [
        {
            "stage": a.stage.value,
            "filename": a.filename,
            "type": a.type,
            "url": a.url
        }
        for a in project.artifacts
    ]
    
    defects = [
        {
            "id": str(d.id),
            "severity": d.severity.value,
            "status": d.status.value,
            "description": d.description,
            "external_id": d.external_id
        }
        for d in project.defects
    ]
    
    context = {
        "project_info": {
            "id": str(project.id),
            "title": project.title,
            "client_name": project.client_name,
            "priority": project.priority
        },
        "notes": notes
    }
    
    # Execute workflow stage
    result = execute_workflow_stage(
        project_id=str(project.id),
        current_stage=project.current_stage,
        context=context,
        artifacts=artifacts,
        defects=defects,
        human_gate=bool(getattr(project, "require_manual_review", False)),
        db=db
    )
    
    # Create StageOutput record
    stage_output = StageOutput(
        project_id=project.id,
        stage=project.current_stage,
        status=result["status"],
        summary=result["summary"],
        structured_output_json=result["structured_output"],
        required_next_inputs_json=result["required_next_inputs"]
    )
    db.add(stage_output)
    
    # Update project stage if successful
    if result["status"] == "SUCCESS":
        # Determine next stage
        stage_order = [
            Stage.ONBOARDING,
            Stage.ASSIGNMENT,
            Stage.BUILD,
            Stage.TEST,
            Stage.DEFECT_VALIDATION,
            Stage.COMPLETE
        ]
        
        current_idx = stage_order.index(project.current_stage)
        if current_idx < len(stage_order) - 1:
            previous_stage = project.current_stage
            project.current_stage = stage_order[current_idx + 1]
            project.status = ProjectStatus.ACTIVE
            _record_stage_transition(project, previous_stage, project.current_stage, str(user.id))
    
    project.updated_at = datetime.utcnow()
    db.commit()
    
    # Create audit log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="WORKFLOW_ADVANCED",
        payload_json={"from_stage": result["stage"], "status": result["status"]}
    )
    db.add(audit)
    db.commit()
    
    return result


def approve_build(db: Session, project_id: UUID, user, notes: Optional[str] = None) -> Dict[str, Any]:
    """Approve build stage (human-in-the-loop)"""
    project = get_project(db, project_id)
    if not project:
        return {"error": "Project not found"}
    
    if project.current_stage != Stage.BUILD:
        return {"error": "Project is not in BUILD stage"}
    
    # Execute workflow with human_gate=True
    artifacts = [
        {"stage": a.stage.value, "filename": a.filename, "type": a.type, "url": a.url}
        for a in project.artifacts
    ]
    
    context = {
        "project_info": {
            "id": str(project.id),
            "title": project.title,
            "client_name": project.client_name
        },
        "approval_notes": notes
    }
    
    result = execute_workflow_stage(
        project_id=str(project.id),
        current_stage=Stage.BUILD,
        context=context,
        artifacts=artifacts,
        defects=[],
        human_gate=False,
        db=db
    )
    
    # Create StageOutput
    stage_output = StageOutput(
        project_id=project.id,
        stage=Stage.BUILD,
        status=result["status"],
        summary=f"Build approved: {notes or 'No notes'}",
        structured_output_json=result["structured_output"],
        required_next_inputs_json=[]
    )
    db.add(stage_output)
    
    # Move to TEST stage
    previous_stage = project.current_stage
    project.current_stage = Stage.TEST
    _record_stage_transition(project, previous_stage, project.current_stage, str(user.id))
    project.updated_at = datetime.utcnow()
    db.commit()
    
    # Create audit log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="BUILD_APPROVED",
        payload_json={"notes": notes}
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": "Build approved, moved to TEST stage"}


def send_back(db: Session, project_id: UUID, target_stage: Stage, reason: str, user) -> Dict[str, Any]:
    """Send project back to a previous stage"""
    project = get_project(db, project_id)
    if not project:
        return {"error": "Project not found"}
    
    previous_stage = project.current_stage
    project.current_stage = target_stage
    _record_stage_transition(project, previous_stage, project.current_stage, str(user.id))
    project.updated_at = datetime.utcnow()
    db.commit()
    
    # Create audit log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="SENT_BACK",
        payload_json={"target_stage": target_stage.value, "reason": reason}
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"Project sent back to {target_stage.value}"}


def pause_project(db: Session, project_id: UUID, reason: str, user) -> Project:
    """Pause a project"""
    project = get_project(db, project_id)
    if not project:
        return None
        
    project.status = ProjectStatus.PAUSED
    project.paused_at = datetime.utcnow()
    project.paused_by_user_id = user.id
    project.pause_reason = reason
    
    # Audit Log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="PROJECT_PAUSED",
        payload_json={"reason": reason}
    )
    db.add(audit)
    db.commit()
    return project


def archive_project(db: Session, project_id: UUID, reason: str, user) -> Project:
    """Archive a project"""
    project = get_project(db, project_id)
    if not project:
        return None
        
    project.status = ProjectStatus.ARCHIVED
    project.archived_at = datetime.utcnow()
    project.archived_by_user_id = user.id
    project.archive_reason = reason
    
    # Audit Log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="PROJECT_ARCHIVED",
        payload_json={"reason": reason}
    )
    db.add(audit)
    db.commit()
    return project


def delete_project(db: Session, project_id: UUID, user) -> bool:
    """Delete a project (Hard delete for now, or check references)"""
    project = get_project(db, project_id)
    if not project:
        return False
        
    # Standard deletion - cascade delete usually handles related items if configured.
    # But for safety, we might just delete it.
    
    db.delete(project)
    
    # Audit is tricky if project is gone, maybe log system event or skip?
    # If purely hard delete, it's gone.
    
    db.commit()
    return True
