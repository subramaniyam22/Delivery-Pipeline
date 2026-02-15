"""Client Management Router - Consultant Access"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.db import get_db
from app.deps import get_current_user
from app.models import User, Role, Project, ProjectStatus, ClientReminderLog, OnboardingData
from app.services.email_service import send_client_reminder_email


router = APIRouter(prefix="/client-management", tags=["Client Management"])


# ============== Schemas ==============

class ClientEmailUpdate(BaseModel):
    client_emails: List[EmailStr]
    client_primary_contact: Optional[str] = None
    client_company: Optional[str] = None


class ClientReminderRequest(BaseModel):
    project_id: UUID
    reminder_type: str  # "requirements_pending", "document_needed", "general"
    subject: str
    message: str
    send_to: Optional[List[EmailStr]] = None  # If not provided, sends to all client emails


class ClientReminderResponse(BaseModel):
    id: UUID
    project_id: UUID
    reminder_type: str
    sent_to: List[str]
    subject: str
    message: Optional[str]
    sent_at: datetime
    status: str

    class Config:
        from_attributes = True


class PendingRequirement(BaseModel):
    requirement_type: str
    description: str
    status: str
    due_date: Optional[str] = None


class ProjectClientInfo(BaseModel):
    project_id: UUID
    project_title: str
    client_name: str
    client_company: Optional[str]
    client_primary_contact: Optional[str]
    client_emails: List[str]
    pending_requirements: List[PendingRequirement]
    last_reminder_sent: Optional[datetime]


# ============== Helper Functions ==============

def check_consultant_or_above(current_user: User):
    """Verify user has consultant or higher access"""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.CONSULTANT, Role.PC]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Consultant role or higher required."
        )


def get_pending_requirements(project: Project, db: Session) -> List[PendingRequirement]:
    """Get pending requirements for a project"""
    pending = []

    onboarding = db.query(OnboardingData).filter(
        OnboardingData.project_id == project.id
    ).first()

    if onboarding:
        if not (onboarding.requirements_json and onboarding.requirements_json != {}):
            pending.append(PendingRequirement(
                requirement_type="Requirements",
                description="Client needs to provide project requirements",
                status="PENDING",
            ))
        if onboarding.custom_copy_notes is None and onboarding.use_custom_copy and onboarding.custom_copy_final_price is None:
            pending.append(PendingRequirement(
                requirement_type="Pricing",
                description="Client needs to confirm copy/pricing if using custom copy",
                status="PENDING",
            ))
        if not (onboarding.contacts_json and len(onboarding.contacts_json) > 0):
            pending.append(PendingRequirement(
                requirement_type="Contacts",
                description="Client needs to provide contact details",
                status="PENDING",
            ))
    else:
        pending.append(PendingRequirement(
            requirement_type="Onboarding",
            description="Client needs to complete onboarding",
            status="PENDING",
        ))

    return pending


# ============== Endpoints ==============

@router.get("/projects", response_model=List[ProjectClientInfo])
def get_projects_with_client_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects with client information (Consultant+). Includes DRAFT, ACTIVE, PAUSED, and COMPLETED so client communications can be managed for all relevant work."""
    check_consultant_or_above(current_user)
    
    statuses_for_client_mgmt = [
        ProjectStatus.DRAFT,
        ProjectStatus.ACTIVE,
        ProjectStatus.PAUSED,
        ProjectStatus.COMPLETED,
    ]
    # Get projects based on role
    if current_user.role in [Role.ADMIN, Role.MANAGER]:
        projects = db.query(Project).filter(
            Project.status.in_(statuses_for_client_mgmt)
        ).all()
    else:
        # Consultant/PC only sees their assigned projects
        projects = db.query(Project).filter(
            Project.status.in_(statuses_for_client_mgmt),
            (Project.consultant_user_id == current_user.id) | 
            (Project.pc_user_id == current_user.id)
        ).all()
    
    result = []
    for project in projects:
        # Get last reminder
        last_reminder = db.query(ClientReminderLog).filter(
            ClientReminderLog.project_id == project.id
        ).order_by(ClientReminderLog.sent_at.desc()).first()
        
        result.append(ProjectClientInfo(
            project_id=project.id,
            project_title=project.title,
            client_name=project.client_name,
            client_company=project.client_company,
            client_primary_contact=project.client_primary_contact,
            client_emails=project.client_emails or [],
            pending_requirements=get_pending_requirements(project, db),
            last_reminder_sent=last_reminder.sent_at if last_reminder else None
        ))
    
    return result


@router.put("/projects/{project_id}/client-emails")
def update_client_emails(
    project_id: UUID,
    client_data: ClientEmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update client email addresses for a project (Consultant+)"""
    check_consultant_or_above(current_user)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user has access to this project
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        if project.consultant_user_id != current_user.id and project.pc_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    project.client_emails = [str(email) for email in client_data.client_emails]
    if client_data.client_primary_contact:
        project.client_primary_contact = client_data.client_primary_contact
    if client_data.client_company:
        project.client_company = client_data.client_company
    
    db.commit()
    
    return {
        "message": "Client information updated",
        "client_emails": project.client_emails,
        "client_primary_contact": project.client_primary_contact,
        "client_company": project.client_company
    }


@router.post("/send-reminder", response_model=ClientReminderResponse)
def send_client_reminder(
    reminder: ClientReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send reminder email to client (Consultant+)"""
    check_consultant_or_above(current_user)
    
    project = db.query(Project).filter(Project.id == reminder.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user has access to this project
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        if project.consultant_user_id != current_user.id and project.pc_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    # Determine recipients
    recipients = reminder.send_to or project.client_emails
    if not recipients:
        raise HTTPException(status_code=400, detail="No client email addresses configured")
    
    # Send email (attempt)
    email_sent = send_client_reminder_email(
        to_emails=recipients,
        subject=reminder.subject,
        message=reminder.message,
        project_title=project.title,
        sender_name=current_user.name
    )
    
    # Log the reminder
    reminder_log = ClientReminderLog(
        project_id=project.id,
        reminder_type=reminder.reminder_type,
        sent_to=recipients,
        subject=reminder.subject,
        message=reminder.message,
        sent_by_user_id=current_user.id,
        status="SENT" if email_sent else "FAILED"
    )
    db.add(reminder_log)
    db.commit()
    db.refresh(reminder_log)
    
    return ClientReminderResponse(
        id=reminder_log.id,
        project_id=reminder_log.project_id,
        reminder_type=reminder_log.reminder_type,
        sent_to=reminder_log.sent_to,
        subject=reminder_log.subject,
        message=reminder_log.message,
        sent_at=reminder_log.sent_at,
        status=reminder_log.status
    )


@router.get("/reminders/{project_id}", response_model=List[ClientReminderResponse])
def get_project_reminders(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get reminder history for a project (Consultant+)"""
    check_consultant_or_above(current_user)
    
    reminders = db.query(ClientReminderLog).filter(
        ClientReminderLog.project_id == project_id
    ).order_by(ClientReminderLog.sent_at.desc()).all()
    
    return [
        ClientReminderResponse(
            id=r.id,
            project_id=r.project_id,
            reminder_type=r.reminder_type,
            sent_to=r.sent_to,
            subject=r.subject,
            message=r.message,
            sent_at=r.sent_at,
            status=r.status
        ) for r in reminders
    ]


@router.get("/pending-requirements/{project_id}", response_model=List[PendingRequirement])
def get_project_pending_requirements(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending requirements for a project (Consultant+)"""
    check_consultant_or_above(current_user)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return get_pending_requirements(project, db)
