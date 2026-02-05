from sqlalchemy.orm import Session
from app.models import Project, StageOutput, ProjectStatus, Stage, AuditLog
from app.schemas import ProjectCreate, ProjectUpdate
from app.agents.workflow_graph import execute_workflow_stage
from app.services.cache_service import cache_service
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


def create_project(db: Session, data: ProjectCreate, user) -> Project:
    """Create a new project"""
    project = Project(
        title=data.title,
        client_name=data.client_name,
        priority=data.priority,
        status=data.status or ProjectStatus.DRAFT,
        current_stage=Stage.ONBOARDING if data.status == ProjectStatus.ACTIVE else Stage.SALES,
        created_by_user_id=user.id,
        # Sales Fields
        pmc_name=data.pmc_name,
        location=data.location,
        client_email_ids=data.client_email_ids,
        project_type=data.project_type,
        manager_user_id=None # Manager assignment removed
    )
    
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
    
    # Trigger Onboarder Agent validation
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
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    project.updated_at = datetime.utcnow()
    
    # Invalidate cache BEFORE commit to prevent race condition
    cache_service.invalidate_project(str(project.id))
    cache_service.invalidate_all_projects()
    
    db.commit()
    db.refresh(project)
    
    # Create audit log
    audit = AuditLog(
        project_id=project.id,
        actor_user_id=user.id,
        action="PROJECT_UPDATED",
        payload_json=update_data
    )
    db.add(audit)
    db.commit()
    
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
        human_gate=False
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
            project.current_stage = stage_order[current_idx + 1]
            project.status = ProjectStatus.ACTIVE
    
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
        human_gate=True
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
    project.current_stage = Stage.TEST
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
    
    project.current_stage = target_stage
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
