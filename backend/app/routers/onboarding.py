from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.db import get_db
from app.models import User, Role, Project, OnboardingData, ProjectTask, ClientReminder, Stage, TaskStatus, TemplateRegistry, OnboardingReviewStatus
from app.schemas import (
    OnboardingDataCreate,
    OnboardingDataUpdate,
    OnboardingDataResponse,
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskResponse,
    ClientReminderCreate,
    ClientReminderCreate,
    ClientReminderResponse
)
from app.services.notification_service import notification_manager
from app.deps import get_current_active_user
from app.rbac import check_full_access
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import secrets
import logging
from app.config import Settings, settings

logger = logging.getLogger(__name__)
from app.services.email_service import send_client_reminder_email
from app.services.config_service import get_config
from app.services.storage import get_storage_backend
from app.services.onboarding_agent import validate_onboarding_submission

router = APIRouter(prefix="/projects", tags=["onboarding"])

# Predefined theme templates
THEME_TEMPLATES = [
    {
        "id": "modern-corporate",
        "name": "Modern Corporate",
        "description": "Clean, professional design for businesses",
        "preview_url": "https://placehold.co/600x400/2563eb/white?text=Modern+Corporate",
        "colors": {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#3b82f6"},
        "features": ["Hero section", "Services grid", "Team section", "Contact form"]
    },
    {
        "id": "creative-agency",
        "name": "Creative Agency",
        "description": "Bold, artistic design for creative teams",
        "preview_url": "https://placehold.co/600x400/7c3aed/white?text=Creative+Agency",
        "colors": {"primary": "#7c3aed", "secondary": "#5b21b6", "accent": "#a78bfa"},
        "features": ["Portfolio gallery", "Case studies", "Team carousel", "Animated sections"]
    },
    {
        "id": "ecommerce-starter",
        "name": "E-commerce Starter",
        "description": "Ready-to-use online store template",
        "preview_url": "https://placehold.co/600x400/059669/white?text=E-commerce",
        "colors": {"primary": "#059669", "secondary": "#047857", "accent": "#10b981"},
        "features": ["Product grid", "Shopping cart", "Checkout flow", "Reviews section"]
    },
    {
        "id": "saas-landing",
        "name": "SaaS Landing",
        "description": "Conversion-focused template for software products",
        "preview_url": "https://placehold.co/600x400/0ea5e9/white?text=SaaS+Landing",
        "colors": {"primary": "#0ea5e9", "secondary": "#0284c7", "accent": "#38bdf8"},
        "features": ["Feature comparison", "Pricing tables", "Testimonials", "FAQ section"]
    },
    {
        "id": "healthcare-professional",
        "name": "Healthcare Professional",
        "description": "Trust-building design for medical practices",
        "preview_url": "https://placehold.co/600x400/14b8a6/white?text=Healthcare",
        "colors": {"primary": "#14b8a6", "secondary": "#0d9488", "accent": "#2dd4bf"},
        "features": ["Services listing", "Doctor profiles", "Appointment booking", "Patient resources"]
    },
    {
        "id": "restaurant-menu",
        "name": "Restaurant & Menu",
        "description": "Appetizing design for food businesses",
        "preview_url": "https://placehold.co/600x400/dc2626/white?text=Restaurant",
        "colors": {"primary": "#dc2626", "secondary": "#b91c1c", "accent": "#f87171"},
        "features": ["Menu display", "Online ordering", "Reservations", "Gallery"]
    },
]

# Copy text pricing tiers
COPY_PRICING_TIERS = [
    {"words": 500, "price": 250, "description": "Basic - Up to 500 words (5 pages)"},
    {"words": 1000, "price": 450, "description": "Standard - Up to 1000 words (10 pages)"},
    {"words": 2000, "price": 800, "description": "Premium - Up to 2000 words (20 pages)"},
    {"words": 5000, "price": 1500, "description": "Enterprise - Up to 5000 words (50+ pages)"},
]

# Predefined tasks with linked fields for auto-completion
PREDEFINED_TASKS = {
    Stage.ONBOARDING: [
        {"title": "Collect client logo", "description": "High-resolution logo in PNG/SVG format", "order": 1, "linked_field": "logo"},
        {"title": "Gather website images", "description": "Hero images, product images, team photos", "order": 2, "linked_field": "images"},
        {"title": "Obtain copy text", "description": "Get written content or confirm custom copy", "order": 3, "linked_field": "copy_text"},
        {"title": "Confirm WCAG requirements", "description": "Document accessibility compliance level", "order": 4, "linked_field": "wcag"},
        {"title": "Collect privacy policy", "description": "Get privacy policy URL or text content", "order": 5, "linked_field": "privacy_policy"},
        {"title": "Define theme preferences", "description": "Select template or custom theme colors", "order": 6, "linked_field": "theme"},
        {"title": "Verify client contacts", "description": "Confirm all stakeholder contact information", "order": 7, "linked_field": "contacts"},
    ],
    Stage.ASSIGNMENT: [
        {"title": "Review project requirements", "description": "Analyze all onboarding documents", "order": 1, "linked_field": None},
        {"title": "Create task breakdown", "description": "Break down project into assignable tasks", "order": 2, "linked_field": None},
        {"title": "Assign team members", "description": "Match tasks with appropriate team members", "order": 3, "linked_field": None},
        {"title": "Set timeline", "description": "Define milestones and deadlines", "order": 4, "linked_field": None},
    ],
    Stage.BUILD: [
        {"title": "Setup development environment", "description": "Configure project infrastructure", "order": 1, "linked_field": None},
        {"title": "Implement core features", "description": "Build main functionality", "order": 2, "linked_field": None},
        {"title": "Apply styling and theme", "description": "Implement design system", "order": 3, "linked_field": None},
        {"title": "Integrate assets", "description": "Add logos, images, content", "order": 4, "linked_field": None},
        {"title": "Implement accessibility", "description": "Ensure WCAG compliance", "order": 5, "linked_field": None},
    ],
    Stage.TEST: [
        {"title": "Functional testing", "description": "Test all features work correctly", "order": 1, "linked_field": None},
        {"title": "Cross-browser testing", "description": "Verify compatibility", "order": 2, "linked_field": None},
        {"title": "Accessibility testing", "description": "Run WCAG compliance checks", "order": 3, "linked_field": None},
        {"title": "Performance testing", "description": "Check load times and optimization", "order": 4, "linked_field": None},
        {"title": "Security testing", "description": "Verify security measures", "order": 5, "linked_field": None},
    ],
    Stage.DEFECT_VALIDATION: [
        {"title": "Review reported defects", "description": "Analyze all bug reports", "order": 1, "linked_field": None},
        {"title": "Validate fixes", "description": "Confirm defects are resolved", "order": 2, "linked_field": None},
        {"title": "Regression testing", "description": "Ensure fixes don't break other features", "order": 3, "linked_field": None},
    ],
}

DEFAULT_REQUIRED_FIELDS = ["logo", "images", "copy_text", "wcag", "privacy_policy", "theme", "contacts"]


# S3 helper functions are now imported from app.services.storage_service


def resolve_required_fields(db: Session, project: Optional[Project]) -> List[str]:
    """Resolve required onboarding fields from admin config and project overrides."""
    required_fields = DEFAULT_REQUIRED_FIELDS

    config = get_config(db, "onboarding_minimum_requirements")
    if config and config.value_json:
        if isinstance(config.value_json, list):
            required_fields = config.value_json
        elif isinstance(config.value_json, dict):
            fields = config.value_json.get("fields")
            if isinstance(fields, list):
                required_fields = fields

    if project and project.allow_requirements_exceptions and project.minimum_requirements_override is not None:
        if isinstance(project.minimum_requirements_override, list):
            required_fields = project.minimum_requirements_override

    return required_fields

def check_field_completion(onboarding_data: OnboardingData, field: str) -> bool:
    """Check if a specific onboarding field is completed"""
    if field == "logo":
        return bool(onboarding_data.logo_url or onboarding_data.logo_file_path)
    elif field == "images":
        return bool(onboarding_data.images_json and len(onboarding_data.images_json) > 0)
    elif field == "copy_text":
        return bool(onboarding_data.copy_text or onboarding_data.use_custom_copy)
    elif field == "wcag":
        # User must explicitly confirm WCAG settings (not just default value)
        return bool(onboarding_data.wcag_confirmed)
    elif field == "privacy_policy":
        return bool(onboarding_data.privacy_policy_url or onboarding_data.privacy_policy_text)
    elif field == "theme":
        return bool(onboarding_data.selected_template_id or onboarding_data.theme_preference)
    elif field == "contacts":
        contacts = onboarding_data.contacts_json or []
        return any(c.get('is_primary') for c in contacts)
    return False


def auto_update_task_status(db: Session, project_id: UUID, onboarding_data: OnboardingData):
    """Auto-update task status based on filled onboarding fields"""
    tasks = db.query(ProjectTask).filter(
        ProjectTask.project_id == project_id,
        ProjectTask.stage == Stage.ONBOARDING,
        ProjectTask.linked_field.isnot(None)
    ).all()
    
    for task in tasks:
        if task.linked_field:
            is_complete = check_field_completion(onboarding_data, task.linked_field)
            if is_complete and task.status != TaskStatus.DONE:
                task.status = TaskStatus.DONE
                task.is_auto_completed = True
                task.completed_at = datetime.utcnow()
            elif not is_complete and task.is_auto_completed:
                task.status = TaskStatus.NOT_STARTED
                task.is_auto_completed = False
                task.completed_at = None
    
    db.commit()


def calculate_completion_percentage(onboarding_data: OnboardingData, required_fields: Optional[List[str]] = None) -> int:
    """Calculate the completion percentage based on filled fields"""
    fields = required_fields or DEFAULT_REQUIRED_FIELDS
    completed = sum(1 for f in fields if check_field_completion(onboarding_data, f))
    return int((completed / len(fields)) * 100) if fields else 100


def get_missing_fields(onboarding_data: OnboardingData, required_fields: Optional[List[str]] = None) -> List[str]:
    """Get list of missing onboarding fields"""
    missing = []
    field_labels = {
        "logo": "Company logo",
        "images": "Website images",
        "copy_text": "Copy text or custom copy request",
        "wcag": "WCAG compliance confirmation",
        "privacy_policy": "Privacy policy",
        "theme": "Theme/template selection",
        "contacts": "Primary contact information"
    }
    fields = required_fields or DEFAULT_REQUIRED_FIELDS
    for field in fields:
        label = field_labels.get(field, field)
        if not check_field_completion(onboarding_data, field):
            missing.append(label)
    return missing


def generate_client_token() -> str:
    """Generate a secure token for client access"""
    return secrets.token_urlsafe(32)


def schedule_next_reminder(db: Session, onboarding_data: OnboardingData):
    """Schedule next auto-reminder based on the configured interval"""
    if onboarding_data.auto_reminder_enabled and onboarding_data.completion_percentage < 100:
        hours = onboarding_data.reminder_interval_hours or 24
        onboarding_data.next_reminder_at = datetime.utcnow() + timedelta(hours=hours)
        db.commit()


async def send_auto_reminder(db: Session, project_id: UUID):
    """Background task to send auto reminder"""
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding or not onboarding.auto_reminder_enabled:
        return
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.current_stage != Stage.ONBOARDING:
        return
    
    required_fields = resolve_required_fields(db, project)
    missing_fields = get_missing_fields(onboarding, required_fields)
    if not missing_fields:
        return
    
    # Get primary contact
    primary_contact = None
    for contact in (onboarding.contacts_json or []):
        if contact.get('is_primary'):
            primary_contact = contact
            break
    
    if not primary_contact:
        return
    
    # Create reminder record
    message = f"""Dear {primary_contact.get('name', 'Client')},

This is a reminder to provide the missing information for project "{project.title}".

Missing items:
{chr(10).join('• ' + field for field in missing_fields)}

Please visit the onboarding form to complete these details:
{settings.FRONTEND_URL}/client-onboarding/{onboarding.client_access_token}

This information is required to move your project to the next stage.

Best regards,
Delivery Automation Suite Team"""
    
    reminder = ClientReminder(
        project_id=project_id,
        recipient_email=primary_contact.get('email'),
        recipient_name=primary_contact.get('name'),
        reminder_type="auto_reminder_24h",
        message=message,
        status="sent"
    )
    db.add(reminder)
    
    onboarding.last_reminder_sent = datetime.utcnow()
    onboarding.reminder_count = (onboarding.reminder_count or 0) + 1
    schedule_next_reminder(db, onboarding)
    
    db.commit()
    
    # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
    print(f"[AUTO-REMINDER] Sent to {primary_contact.get('email')} for project {project.title}")


def create_predefined_tasks_for_project(db: Session, project_id: UUID, stage: Stage, user_id: UUID = None):
    """Create predefined tasks for a project stage"""
    if stage not in PREDEFINED_TASKS:
        return []
    
    created_tasks = []
    for task_template in PREDEFINED_TASKS[stage]:
        existing = db.query(ProjectTask).filter(
            ProjectTask.project_id == project_id,
            ProjectTask.stage == stage,
            ProjectTask.title == task_template["title"],
            ProjectTask.is_predefined == True
        ).first()
        
        if not existing:
            task = ProjectTask(
                project_id=project_id,
                stage=stage,
                title=task_template["title"],
                description=task_template["description"],
                is_predefined=True,
                is_required=True,
                is_auto_completed=stage == Stage.ONBOARDING,  # Auto-complete for onboarding
                linked_field=task_template.get("linked_field"),
                order_index=task_template["order"],
                created_by_user_id=user_id
            )
            db.add(task)
            created_tasks.append(task)
    
    db.commit()
    return created_tasks


# ============= Static Data Endpoints =============

@router.get("/templates")
def get_theme_templates():
    """Get available theme templates"""
    return {"templates": THEME_TEMPLATES}


@router.get("/copy-pricing")
def get_copy_pricing():
    """Get copy text pricing tiers"""
    return {"pricing_tiers": COPY_PRICING_TIERS}


# ============= Onboarding Data Endpoints =============

@router.get("/{project_id}/onboarding-data", response_model=OnboardingDataResponse)
def get_onboarding_data(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get onboarding data for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    
    if not onboarding:
        # Only create onboarding data if project is in ONBOARDING stage or later
        # Don't create for SALES stage projects
        if project.current_stage == Stage.SALES:
            raise HTTPException(
                status_code=404, 
                detail="Onboarding data not available for projects in SALES stage"
            )
        
        # Create empty onboarding data with client token
        onboarding = OnboardingData(
            project_id=project_id,
            client_access_token=generate_client_token(),
            token_expires_at=datetime.utcnow() + timedelta(days=30),
            contacts_json=[],
            images_json=[],
            theme_colors_json={},
            custom_fields_json=[],
            requirements_json={},
            next_reminder_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(onboarding)
        db.commit()
        db.refresh(onboarding)
        
        # Create predefined tasks for onboarding
        create_predefined_tasks_for_project(db, project_id, Stage.ONBOARDING, current_user.id)
    
    return onboarding


@router.put("/{project_id}/onboarding-data", response_model=OnboardingDataResponse)
def update_onboarding_data(
    project_id: UUID,
    data: OnboardingDataUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update onboarding data for a project"""
    allowed_roles = [Role.CONSULTANT, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # HITL check: Only Admins can update by default. Others need require_manual_review=True
    if current_user.role != Role.ADMIN:
        if not project.require_manual_review:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manual updates are restricted. This project is being handled by the Onboarder Agent. Contact an Admin to enable Human-in-the-Loop (HITL) mode."
            )
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    
    if not onboarding:
        onboarding = OnboardingData(
            project_id=project_id,
            client_access_token=generate_client_token(),
            token_expires_at=datetime.utcnow() + timedelta(days=30),
            contacts_json=[],
            images_json=[],
            theme_colors_json={},
            custom_fields_json=[],
            requirements_json={}
        )
        db.add(onboarding)
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    if 'contacts' in update_data:
        onboarding.contacts_json = [c.model_dump() if hasattr(c, 'model_dump') else c for c in update_data['contacts']]
    if 'images' in update_data:
        onboarding.images_json = update_data['images']
    if 'theme_colors' in update_data:
        onboarding.theme_colors_json = update_data['theme_colors'] or {}
    if 'custom_fields' in update_data:
        onboarding.custom_fields_json = update_data['custom_fields']
    if 'requirements' in update_data:
        onboarding.requirements_json = update_data['requirements'] or {}
    
    # Update simple fields
    simple_fields = ['logo_url', 'logo_file_path', 'copy_text', 'use_custom_copy', 
                     'custom_copy_base_price', 'custom_copy_word_count', 'custom_copy_final_price',
                     'custom_copy_notes', 'wcag_compliance_required', 'wcag_level', 'wcag_confirmed',
                     'privacy_policy_url', 'privacy_policy_text', 'theme_preference',
                     'selected_template_id', 'auto_reminder_enabled']
    for field in simple_fields:
        if field in update_data:
            setattr(onboarding, field, update_data[field])
    if 'selected_template_id' in update_data and update_data.get('selected_template_id'):
        onboarding.theme_preference = update_data.get('selected_template_id')
    
    # Calculate completion percentage
    required_fields = resolve_required_fields(db, project)
    onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
    
    db.commit()

    try:
        from app.services.contract_service import create_or_update_contract
        create_or_update_contract(db, project_id, source="user:onboarding_update")
    except Exception as e:
        logger.warning("Contract sync after onboarding update failed: %s", e)
    try:
        from app.services.hitl_service import invalidate_pending_approvals_if_stale
        invalidate_pending_approvals_if_stale(db, project_id)
    except Exception as e:
        logger.warning("HITL invalidation after onboarding update failed: %s", e)
    try:
        from app.services.pipeline_orchestrator import auto_advance
        auto_advance(db, project_id, trigger_source="onboarding_updated")
    except Exception as e:
        logger.warning("Pipeline auto_advance after onboarding update failed: %s", e)

    # Auto-update task status based on filled fields
    auto_update_task_status(db, project_id, onboarding)
    
    # Trigger auto-advance if HITL is disabled (AI Agent Mode)
    if not project.require_manual_review:
        from app.services.onboarding_agent_service import OnboarderAgentService
        agent_service = OnboarderAgentService(db)
        # We can run this in background or synchronously here
        background_tasks.add_task(agent_service.check_and_automate_onboarding, project_id)
    
    db.refresh(onboarding)
    
    return onboarding


@router.post("/{project_id}/onboarding-data/remind")
def send_manual_reminder(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Manually trigger a reminder email to the client"""
    # Check permissions (Added SALES)
    if current_user.role not in [Role.ADMIN, Role.CONSULTANT, Role.PC, Role.MANAGER, Role.SALES]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding data not found")

    # Get primary contact or fallback to project client emails
    primary_contact = None
    recipient_email = None
    recipient_name = "Client"

    # 1. Try to find implicit primary contact in onboarding data
    for contact in (onboarding.contacts_json or []):
        if contact.get('is_primary'):
            primary_contact = contact
            break
    
    if primary_contact:
        recipient_email = primary_contact.get('email')
        recipient_name = primary_contact.get('name') or "Client"
    else:
        # 2. Fallback to Project Client Emails
        if project.client_email_ids:
            # client_email_ids is comma separated string
            emails = [e.strip() for e in project.client_email_ids.split(',') if e.strip()]
            if emails:
                recipient_email = emails[0]
                recipient_name = project.client_name or "Client"

    if not recipient_email:
        raise HTTPException(status_code=400, detail="No valid email found in primary contact or project client emails")

    # Construct message
    required_fields = resolve_required_fields(db, project)
    missing_fields = get_missing_fields(onboarding, required_fields)
    
    # Construct message
    
    # Re-instantiate settings locally to avoid module-level issues
    local_settings = Settings()
    frontend_url = local_settings.FRONTEND_URL
    
    access_token = onboarding.client_access_token
    link = f"{frontend_url}/client-onboarding/{access_token}"
    
    message = f"Hi {project.client_name},<br><br>Welcome aboard! We’ve reviewed the initial details for {project.title}, and everything looks on track so far.<br><br>To help us move faster and avoid back-and-forth later, could you complete the onboarding form below? This will give our team the clarity we need to set things up right from day one.<br><br>👉 Onboarding form:<br><a href='{link}'>{link}</a><br><br>If anything feels unclear, just use the chat option on the onboarding page. You’ll be connected to our team while you fill it out.<br><br>Once you’re done, we’ll review your inputs and come back with the next steps and timelines.<br><br>Excited to get started with you.<br><br>Warm regards,<br>Project Onboarding Team"

    # Record it
    try:
        reminder = ClientReminder(
            project_id=project_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            reminder_type="manual_reminder",
            message=message,
            status="sent"
        )
        db.add(reminder)
        
        onboarding.last_reminder_sent = datetime.utcnow()
        onboarding.reminder_count = (onboarding.reminder_count or 0) + 1
        
        db.commit()
    except Exception as db_exc:
        logger.error(f"Database error recording reminder: {db_exc}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_exc)}")
    
    # Send email (Real Implementation)
    try:
        # Use the module-level function imported at top of file
        # ensure allow fallbacks for sender name
        sender = f"{current_user.full_name} (via Delivery Automation Suite)" if hasattr(current_user, 'full_name') and current_user.full_name else "Delivery Automation Suite Team"
        
        # Now returns (success, message/error)
        email_success, email_msg = send_client_reminder_email(
            to_emails=[recipient_email],
            subject=f"Let’s get your project moving 🚀",
            message=message,
            project_title=project.title,
            sender_name="Project Onboarding Team",
            return_details=True
        )
        
        if email_success:
            logger.info(f"[MANUAL-REMINDER] Email sent successfully to {recipient_email}. Msg: {email_msg}")
            return {"success": True, "message": f"Reminder email result: {email_msg}"}
        else:
            logger.error(f"[MANUAL-REMINDER] Failed to send email to {recipient_email}. Error: {email_msg}")
            # We still return success regarding the DB record, but warn about email failure
            return {"success": True, "message": f"Reminder saved, but email failed: {email_msg}"}
            
    except Exception as e:
        logger.error(f"[MANUAL-REMINDER] Exception sending email: {str(e)}")
        # Don't fail the request if DB success, but inform user
        return {"success": True, "message": f"Reminder saved, but email failed: {str(e)}"}



@router.get("/{project_id}/onboarding-data/completion")
def get_completion_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get onboarding completion status and check if ready to advance"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    
    if not onboarding:
        return {
            "completion_percentage": 0,
            "can_auto_advance": False,
            "missing_fields": ["All fields are missing"],
            "completed_tasks": 0,
            "total_required_tasks": 7
        }
    
    required_fields = resolve_required_fields(db, project)
    completion = calculate_completion_percentage(onboarding, required_fields)
    missing_fields = get_missing_fields(onboarding, required_fields)
    
    # Auto-update tasks and count
    auto_update_task_status(db, project_id, onboarding)
    
    tasks = db.query(ProjectTask).filter(
        ProjectTask.project_id == project_id,
        ProjectTask.stage == Stage.ONBOARDING,
        ProjectTask.is_required == True
    ).all()
    
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    total_required_tasks = len(tasks)
    task_completion = (completed_tasks / total_required_tasks * 100) if total_required_tasks > 0 else 100
    
    # Can auto-advance if 90% complete
    can_auto_advance = completion >= 90 and task_completion >= 90
    
    return {
        "completion_percentage": completion,
        "task_completion_percentage": int(task_completion),
        "can_auto_advance": can_auto_advance,
        "missing_fields": missing_fields,
        "completed_tasks": completed_tasks,
        "total_required_tasks": total_required_tasks,
        "client_form_url": f"/client-onboarding/{onboarding.client_access_token}" if onboarding.client_access_token else None
    }


# ============= Client Access Endpoints (No Auth Required) =============

client_router = APIRouter(prefix="/client-onboarding", tags=["client-onboarding"])


@client_router.get("/{token}")
def get_client_onboarding_form(token: str, db: Session = Depends(get_db)):
    """Get onboarding form data for client (no auth required)"""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    if onboarding.token_expires_at and onboarding.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This link has expired. Please contact your project manager.")
    
    project = db.query(Project).filter(Project.id == onboarding.project_id).first()
    
    required_fields = resolve_required_fields(db, project)
    missing_fields = get_missing_fields(onboarding, required_fields)
    
    client_preview = None
    if project and hasattr(project, "client_preview_status"):
        client_preview = {
            "preview_url": getattr(project, "client_preview_url", None),
            "thumbnail_url": getattr(project, "client_preview_thumbnail_url", None),
            "status": getattr(project, "client_preview_status", "not_generated"),
        }
    client_wants_full_validation = _get_custom_field(onboarding, "client_wants_full_validation") if onboarding else None
    return {
        "project_title": project.title if project else "Unknown Project",
        "project_id": str(onboarding.project_id),
        "completion_percentage": onboarding.completion_percentage,
        "missing_fields": missing_fields,
        "submitted_at": onboarding.submitted_at,
        "missing_fields_eta_json": onboarding.missing_fields_eta_json,
        "client_preview": client_preview,
        "client_wants_full_validation": client_wants_full_validation,
        "data": {
            "logo_url": onboarding.logo_url,
            "logo_file_path": onboarding.logo_file_path,
            "images": onboarding.images_json,
            "copy_text": onboarding.copy_text,
            "use_custom_copy": onboarding.use_custom_copy,
            "custom_copy_base_price": onboarding.custom_copy_base_price,
            "custom_copy_word_count": onboarding.custom_copy_word_count,
            "custom_copy_final_price": onboarding.custom_copy_final_price,
            "wcag_compliance_required": onboarding.wcag_compliance_required,
            "wcag_level": onboarding.wcag_level,
            "wcag_confirmed": onboarding.wcag_confirmed,
            "privacy_policy_url": onboarding.privacy_policy_url,
            "privacy_policy_text": onboarding.privacy_policy_text,
            "selected_template_id": onboarding.selected_template_id,
            "theme_colors": onboarding.theme_colors_json,
            "contacts": onboarding.contacts_json,
            "requirements": onboarding.requirements_json,
            "submitted_at": onboarding.submitted_at,
            "missing_fields_eta_json": onboarding.missing_fields_eta_json,
        },
        "templates": get_active_templates(db),
        "copy_pricing": COPY_PRICING_TIERS,
    }

def get_active_templates(db: Session):
    """Return published TemplateRegistry templates for client onboarding (replaces ThemeTemplate)."""
    try:
        from uuid import UUID
        # Only show active AND (published status or is_published) templates to clients
        from sqlalchemy import or_
        db_templates = db.query(TemplateRegistry).filter(
            TemplateRegistry.is_active == True,
            or_(TemplateRegistry.status == "published", TemplateRegistry.is_published == True),
            TemplateRegistry.preview_status == "ready",
            TemplateRegistry.validation_status == "passed",
        ).all()
        # Prefer high-performing templates; hide deprecated (Prompt 9)
        db_templates = [t for t in db_templates if not getattr(t, "is_deprecated", False)]
        db_templates.sort(key=lambda t: (float((getattr(t, "performance_metrics_json", None) or {}).get("weighted_score") or 0)), reverse=True)
        if db_templates:
            out = []
            for t in db_templates:
                tid = str(t.id) if isinstance(t.id, UUID) else t.id
                # Build colors from default_config_json or placeholder for client UI
                colors = (t.default_config_json or {}).get("colors") if getattr(t, "default_config_json", None) else None
                if not colors or not isinstance(colors, dict):
                    colors = {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#3b82f6"}
                out.append({
                    "id": tid,
                    "name": t.name,
                    "description": t.description or "",
                    "preview_url": t.preview_url,
                    "preview_thumbnail_url": getattr(t, "preview_thumbnail_url", None),
                    "actual_web_url": t.preview_url,
                    "colors": colors,
                    "features": getattr(t, "feature_tags_json", None) or t.features_json or [],
                    "category": getattr(t, "category", None),
                    "style": getattr(t, "style", None),
                    "pages_json": getattr(t, "pages_json", None) or [],
                    "required_inputs_json": getattr(t, "required_inputs_json", None) or [],
                    "optional_inputs_json": getattr(t, "optional_inputs_json", None) or [],
                })
            return out
    except Exception:
        pass
    return []



@client_router.put("/{token}")
def update_client_onboarding_form(token: str, data: dict, db: Session = Depends(get_db)):
    """Update onboarding form data from client (no auth required)"""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    if onboarding.token_expires_at and onboarding.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This link has expired")
    
    # Update fields that client can modify
    client_updatable_fields = [
        'logo_url', 'images', 'copy_text', 'use_custom_copy',
        'custom_copy_word_count', 'custom_copy_final_price', 'custom_copy_notes',
        'wcag_compliance_required', 'wcag_level', 'wcag_confirmed', 'privacy_policy_url', 
        'privacy_policy_text', 'selected_template_id', 'theme_colors', 'contacts',
        'requirements'
    ]
    
    for field in client_updatable_fields:
        if field in data:
            if field == 'images':
                onboarding.images_json = data[field]
            elif field == 'theme_colors':
                onboarding.theme_colors_json = data[field]
            elif field == 'contacts':
                onboarding.contacts_json = data[field]
            elif field == 'requirements':
                onboarding.requirements_json = data[field] or {}
            else:
                setattr(onboarding, field, data[field])
            if field == 'selected_template_id' and data.get(field):
                onboarding.theme_preference = data.get(field)
    
    # Calculate completion
    project = db.query(Project).filter(Project.id == onboarding.project_id).first()
    required_fields = resolve_required_fields(db, project)
    onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
    
    db.commit()
    
    # Auto-update tasks
    auto_update_task_status(db, onboarding.project_id, onboarding)
    
    missing_fields = get_missing_fields(onboarding, required_fields)
    return {
        "success": True,
        "completion_percentage": onboarding.completion_percentage,
        "missing_fields": missing_fields
    }


def _run_client_preview_after_submit(project_id: UUID) -> None:
    """Background task: generate client website preview when AI approved and template selected."""
    from app.db import SessionLocal
    from app.jobs.client_preview import run_client_preview_pipeline
    session = SessionLocal()
    try:
        run_client_preview_pipeline(project_id, force=False, db=session)
    except Exception as e:
        logger.exception("Client preview generation failed after submit: %s", e)
    finally:
        session.close()


@client_router.post("/{token}/submit")
async def submit_client_onboarding_form(
    token: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Submit onboarding form and notify the assigned consultant with AI Review. When AI approves, generates client website preview."""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()

    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid or expired link")

    if onboarding.token_expires_at and onboarding.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This link has expired")

    project = db.query(Project).filter(Project.id == onboarding.project_id).first()

    missing_fields_eta = payload.get("missing_fields_eta", {})
    if isinstance(missing_fields_eta, dict):
        onboarding.missing_fields_eta_json = missing_fields_eta

    onboarding.submitted_at = datetime.utcnow()
    
    # --- AI REVIEW & HITL LOGIC ---
    try:
        # 1. Run AI Validation
        review_result = await validate_onboarding_submission(db, str(project.id), onboarding)
        ai_approved = review_result.get("approved", False)
        ai_feedback = review_result.get("feedback", "No feedback generated.")
        
        onboarding.ai_review_notes = ai_feedback
        
        # 2. Determine Status
        if ai_approved:
            # AI thinks it's good. Check if Manual Review is required.
            if project.require_manual_review:
                onboarding.review_status = OnboardingReviewStatus.WAITING_FOR_CONSULTANT
            else:
                # Auto-Approve!
                onboarding.review_status = OnboardingReviewStatus.APPROVED
                project.current_stage = Stage.ASSIGNMENT
        else:
            # AI flagged issues
            onboarding.review_status = OnboardingReviewStatus.NEEDS_CHANGES
            # Even if manual review is off, if AI fails it, we likely want a human to check?
            # Or strict reject? "Consultant can be considered as human in the loop".
            # Let's verify: if AI fails, it definitely needs human attention.
            if not project.require_manual_review:
                 # If full auto was expected but failed, fallback to consultant
                 onboarding.review_status = OnboardingReviewStatus.WAITING_FOR_CONSULTANT
    
    except Exception as e:
        logger.error(f"Error during AI review process: {e}")
        # Fallback to manual
        onboarding.review_status = OnboardingReviewStatus.WAITING_FOR_CONSULTANT
        onboarding.ai_review_notes = f"AI Review Failed: {str(e)}"

    db.commit()

    try:
        from app.services.contract_service import create_or_update_contract
        create_or_update_contract(db, project.id, source="user:onboarding_submit")
    except Exception as e:
        logger.warning("Contract sync after onboarding submit failed: %s", e)
    try:
        from app.services.hitl_service import invalidate_pending_approvals_if_stale
        invalidate_pending_approvals_if_stale(db, project.id)
    except Exception as e:
        logger.warning("HITL invalidation after onboarding submit failed: %s", e)
    try:
        from app.services.pipeline_orchestrator import auto_advance
        auto_advance(db, project.id, trigger_source="onboarding_saved")
    except Exception as e:
        logger.warning("Pipeline auto_advance after onboarding submit failed: %s", e)

    # When AI approved and client has selected a template, generate clickable website preview in background
    if ai_approved and (onboarding.selected_template_id or onboarding.theme_preference):
        background_tasks.add_task(_run_client_preview_after_submit, project.id)

    notification_sent = False
    recipients = []
    
    # 1. Determine Recipients
    if project.consultant_user_id:
        consultant = db.query(User).filter(User.id == project.consultant_user_id).first()
        if consultant:
            recipients.append(consultant)
    
    # Fallback to Managers if no consultant
    if not recipients:
        managers = db.query(User).filter(User.role == Role.MANAGER).all()
        recipients.extend(managers)

    # 2. Send Notifications
    if recipients:
        required_fields = resolve_required_fields(db, project)
        missing_fields = get_missing_fields(onboarding, required_fields)
        eta_lines = []
        if isinstance(missing_fields_eta, dict):
            for field, eta in missing_fields_eta.items():
                eta_lines.append(f"- {field}: {eta}")

        status_msg = f"Review Status: {onboarding.review_status.value}"
        if onboarding.review_status == OnboardingReviewStatus.APPROVED:
            status_msg += " (Auto-Approved by AI)"
        
        message = f"The client submitted the onboarding form.\n{status_msg}\nAI Feedback: {onboarding.ai_review_notes}"
        
        if missing_fields:
            message += "\n\nMissing information:\n" + "\n".join([f"- {f}" for f in missing_fields])
        if eta_lines:
            message += "\n\nClient provided ETA:\n" + "\n".join(eta_lines)

        email_addresses = [u.email for u in recipients if u.email]
        # if email_addresses:
        #     notification_sent = send_client_reminder_email(
        #         to_emails=email_addresses,
        #         subject=f"Client submitted onboarding: {project.title}",
        #         message=message,
        #         project_title=project.title,
        #         sender_name="Delivery Automation Suite"
        #     )
        
        # Send WS Notification
        for recipient in recipients:
             try:
                await notification_manager.send_personal_message({
                     "type": "URGENT_ALERT",
                     "project_id": str(project.id),
                     "project_title": project.title,
                     "message": f"Client submitted onboarding for {project.title}."
                 }, str(recipient.id), db)
             except Exception as e:
                 logger.error(f"Failed to send WS notif to {recipient.id}: {e}")

    return {"success": True, "notification_sent": notification_sent, "review_status": onboarding.review_status}


def _get_custom_field(onboarding: OnboardingData, name: str):
    """Get value from custom_fields_json list (items: {field_name, field_value, field_type})."""
    custom = onboarding.custom_fields_json or []
    if not isinstance(custom, list):
        return None
    for item in custom:
        if isinstance(item, dict) and item.get("field_name") == name:
            return item.get("field_value")
    return None


def _set_custom_field(db: Session, onboarding: OnboardingData, name: str, value: Any) -> None:
    """Set a named value in custom_fields_json list; merge or append."""
    custom = list(onboarding.custom_fields_json or [])
    if not isinstance(custom, list):
        custom = []
    found = False
    for i, item in enumerate(custom):
        if isinstance(item, dict) and item.get("field_name") == name:
            custom[i] = {**item, "field_value": value}
            found = True
            break
    if not found:
        custom.append({"field_name": name, "field_value": value, "field_type": "boolean"})
    onboarding.custom_fields_json = custom
    flag_modified(onboarding, "custom_fields_json")


@client_router.post("/{token}/full-validation-choice")
async def set_client_full_validation_choice(token: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Record client's Yes/No for proceeding with full validation, testing, SEO, accessibility, build & QA."""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    proceed = payload.get("proceed")
    if proceed not in (True, False):
        raise HTTPException(status_code=400, detail="payload.proceed must be true or false")
    _set_custom_field(db, onboarding, "client_wants_full_validation", proceed)
    db.commit()
    return {"success": True, "proceed": proceed}


@client_router.post("/{token}/upload-logo")
async def upload_client_logo(
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload logo file from client"""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/svg+xml', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PNG, JPEG, SVG, WEBP")
    
    content = await file.read()
    file_path_result = None
    
    try:
        storage = get_storage_backend()
        key = f"projects/{onboarding.project_id}/onboarding/logo/{file.filename}"
        stored = storage.save_bytes(key, content, file.content_type)
        onboarding.logo_url = stored.url
        onboarding.logo_file_path = stored.storage_key
        file_path_result = stored.url or stored.storage_key
            
        project = db.query(Project).filter(Project.id == onboarding.project_id).first()
        required_fields = resolve_required_fields(db, project)
        onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
        db.commit()
        
        auto_update_task_status(db, onboarding.project_id, onboarding)
        
        return {"success": True, "file_path": file_path_result}
    except Exception as e:
        logger.error(f"Logo upload failed for project {onboarding.project_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")


@client_router.post("/{token}/upload-image")
async def upload_client_image(
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload image file from client"""
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    content = await file.read()
    images = list(onboarding.images_json or [])
    file_path_result = None
    
    try:
        storage = get_storage_backend()
        key = f"projects/{onboarding.project_id}/onboarding/images/{file.filename}"
        stored = storage.save_bytes(key, content, file.content_type)
        images.append({"url": stored.url, "storage_key": stored.storage_key, "filename": file.filename, "type": "uploaded"})
        file_path_result = stored.url or stored.storage_key
            
        onboarding.images_json = images
        flag_modified(onboarding, "images_json")
        project = db.query(Project).filter(Project.id == onboarding.project_id).first()
        required_fields = resolve_required_fields(db, project)
        onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
        db.commit()
        
        auto_update_task_status(db, onboarding.project_id, onboarding)
        
        return {"success": True, "file_path": file_path_result, "images": images}
    except Exception as e:
        logger.error(f"Image upload failed for project {onboarding.project_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")


@client_router.delete("/{token}/image")
def delete_client_image(
    token: str,
    index: int = Query(...),
    db: Session = Depends(get_db)
):
    """Delete an uploaded image"""
    logger.info(f"Deletion request for image at index {index} with token {token}")
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        logger.warning(f"Invalid token for deletion: {token}")
        raise HTTPException(status_code=404, detail="Invalid link")
        
    try:
        images = list(onboarding.images_json or [])
        if 0 <= index < len(images):
            removed = images.pop(index)
            logger.info(f"Removing image: {removed}")
            onboarding.images_json = images
            flag_modified(onboarding, "images_json")
            
            # Recalculate completion
            project = db.query(Project).filter(Project.id == onboarding.project_id).first()
            required_fields = resolve_required_fields(db, project)
            onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
            
            db.commit()
            auto_update_task_status(db, onboarding.project_id, onboarding)
            
            return {"success": True, "images": images}
        else:
            logger.warning(f"Invalid image index {index} for project {onboarding.project_id}")
            raise HTTPException(status_code=400, detail="Invalid image index")
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@client_router.delete("/{token}/logo")
def delete_client_logo(
    token: str,
    db: Session = Depends(get_db)
):
    """Delete an uploaded logo"""
    logger.info(f"Deletion request for logo with token {token}")
    onboarding = db.query(OnboardingData).filter(OnboardingData.client_access_token == token).first()
    
    if not onboarding:
        logger.warning(f"Invalid token for deletion: {token}")
        raise HTTPException(status_code=404, detail="Invalid link")
        
    try:
        onboarding.logo_url = None
        onboarding.logo_file_path = None
        
        # Recalculate completion
        project = db.query(Project).filter(Project.id == onboarding.project_id).first()
        required_fields = resolve_required_fields(db, project)
        onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
        
        db.commit()
        auto_update_task_status(db, onboarding.project_id, onboarding)
        
        return {"success": True, "message": "Logo deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting logo: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============= Project Task Endpoints =============

@router.get("/{project_id}/project-tasks", response_model=List[ProjectTaskResponse])
def list_project_tasks(
    project_id: UUID,
    stage: Stage = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all tasks for a project with auto-updated status"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Auto-update onboarding tasks
    if project.current_stage == Stage.ONBOARDING:
        onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if onboarding:
            auto_update_task_status(db, project_id, onboarding)
    
    query = db.query(ProjectTask).filter(ProjectTask.project_id == project_id)
    if stage:
        query = query.filter(ProjectTask.stage == stage)
    
    tasks = query.order_by(ProjectTask.stage, ProjectTask.order_index).all()
    
    # Create predefined tasks if none exist
    if not tasks or (stage and not any(t.stage == stage for t in tasks)):
        target_stage = stage or project.current_stage
        create_predefined_tasks_for_project(db, project_id, target_stage, current_user.id)
        tasks = query.all()
    
    return tasks


@router.post("/{project_id}/project-tasks", response_model=ProjectTaskResponse, status_code=201)
def create_project_task(
    project_id: UUID,
    data: ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new custom task (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin and Manager can create tasks")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = ProjectTask(
        project_id=project_id,
        stage=data.stage,
        title=data.title,
        description=data.description,
        is_predefined=False,
        is_required=data.is_required,
        is_auto_completed=False,
        linked_field=None,
        assignee_user_id=data.assignee_user_id,
        due_date=data.due_date,
        order_index=data.order_index,
        created_by_user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{project_id}/project-tasks/{task_id}")
def delete_project_task(
    project_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a project task (Admin/Manager only, non-predefined tasks only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin and Manager can delete tasks")
    
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.is_predefined:
        raise HTTPException(status_code=400, detail="Cannot delete predefined tasks")
    
    db.delete(task)
    db.commit()
    
    return {"success": True, "message": "Task deleted"}


# ============= Client Reminder Endpoints =============

@router.post("/{project_id}/send-reminder", response_model=ClientReminderResponse)
def send_client_reminder(
    project_id: UUID,
    data: ClientReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a manual reminder to client"""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    
    # Add client form link to message if available
    message = data.message
    if onboarding and onboarding.client_access_token:
        message += f"\n\nComplete your onboarding form: {settings.FRONTEND_URL}/client-onboarding/{onboarding.client_access_token}"
    
    email_sent = send_client_reminder_email(
        to_emails=[data.recipient_email],
        subject=f"Onboarding Reminder: {project.title}",
        message=message,
        project_title=project.title,
        sender_name=current_user.name
    )

    reminder = ClientReminder(
        project_id=project_id,
        recipient_email=data.recipient_email,
        recipient_name=data.recipient_name,
        reminder_type=data.reminder_type,
        message=message,
        status="sent" if email_sent else "failed"
    )
    db.add(reminder)
    
    if onboarding:
        onboarding.last_reminder_sent = datetime.utcnow()
        onboarding.reminder_count = (onboarding.reminder_count or 0) + 1
    
    db.commit()
    db.refresh(reminder)
    
    print(f"[REMINDER] Sent to {data.recipient_email}: {message}")

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send reminder email")

    return reminder


@router.get("/{project_id}/reminders", response_model=List[ClientReminderResponse])
def list_reminders(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all reminders sent for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    reminders = db.query(ClientReminder).filter(
        ClientReminder.project_id == project_id
    ).order_by(ClientReminder.sent_at.desc()).all()
    
    return reminders


@router.post("/{project_id}/toggle-auto-reminder")
def toggle_auto_reminder(
    project_id: UUID,
    enabled: bool,
    interval_hours: Optional[int] = Query(None, description="Reminder interval in hours"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Enable/disable auto reminders with configurable interval"""
    allowed_roles = [Role.ADMIN, Role.MANAGER, Role.CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding data not found")
    
    # If enabling, check if already 100% complete
    # Logic to prevent enabling if 100% complete - REMOVED per user request
    # if enabled and onboarding.completion_percentage >= 100:
    #     return {
    #         "success": False, 
    #         "message": "Cannot enable reminders: Onboarding is already 100% complete.",
    #         "auto_reminder_enabled": False
    #     }

    onboarding.auto_reminder_enabled = enabled
    
    # Update interval if provided (allow any positive integer)
    if interval_hours and interval_hours > 0:
        onboarding.reminder_interval_hours = interval_hours
    
    if enabled:
        # Schedule next reminder based on interval
        hours = onboarding.reminder_interval_hours or 24
        onboarding.next_reminder_at = datetime.utcnow() + timedelta(hours=hours)
    else:
        onboarding.next_reminder_at = None
    
    db.commit()
    
    return {"success": True, "auto_reminder_enabled": enabled}


# ============= Auto-Advance Endpoint =============

@router.post("/{project_id}/check-auto-advance")
def check_and_auto_advance(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check if project can auto-advance"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.current_stage != Stage.ONBOARDING:
        return {"can_advance": False, "reason": "Auto-advance only for ONBOARDING stage"}
    
    onboarding = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if not onboarding:
        return {"can_advance": False, "reason": "No onboarding data found"}
    if not getattr(onboarding, "submitted_at", None):
        return {"can_advance": False, "reason": "Client has not submitted onboarding yet"}
    
    required_fields = resolve_required_fields(db, project)
    completion = calculate_completion_percentage(onboarding, required_fields)
    
    if completion >= 90:
        project.current_stage = Stage.ASSIGNMENT
        db.commit()
        
        create_predefined_tasks_for_project(db, project_id, Stage.ASSIGNMENT, current_user.id)
        
        return {
            "can_advance": True,
            "advanced": True,
            "new_stage": "ASSIGNMENT",
            "completion_percentage": completion
        }
    
    return {
        "can_advance": False,
        "advanced": False,
        "reason": f"Completion at {completion}% (need 90%)",
        "completion_percentage": completion
    }


# Register client router
router.include_router(client_router)
