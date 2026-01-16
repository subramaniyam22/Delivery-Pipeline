from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.db import get_db
from app.models import User, Role, Project, OnboardingData, ProjectTask, ClientReminder, Stage, TaskStatus
from app.schemas import (
    OnboardingDataCreate,
    OnboardingDataUpdate,
    OnboardingDataResponse,
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskResponse,
    ClientReminderCreate,
    ClientReminderResponse
)
from app.deps import get_current_active_user
from app.rbac import check_full_access
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import secrets
import os
from app.config import settings
from app.services.email_service import send_client_reminder_email
from app.services.config_service import get_config

router = APIRouter(prefix="/projects", tags=["onboarding"])

# Predefined theme templates
THEME_TEMPLATES = [
    {
        "id": "modern-corporate",
        "name": "Modern Corporate",
        "description": "Clean, professional design for businesses",
        "preview_url": "/templates/modern-corporate.png",
        "colors": {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#3b82f6"},
        "features": ["Hero section", "Services grid", "Team section", "Contact form"]
    },
    {
        "id": "creative-agency",
        "name": "Creative Agency",
        "description": "Bold, artistic design for creative teams",
        "preview_url": "/templates/creative-agency.png",
        "colors": {"primary": "#7c3aed", "secondary": "#5b21b6", "accent": "#a78bfa"},
        "features": ["Portfolio gallery", "Case studies", "Team carousel", "Animated sections"]
    },
    {
        "id": "ecommerce-starter",
        "name": "E-commerce Starter",
        "description": "Ready-to-use online store template",
        "preview_url": "/templates/ecommerce-starter.png",
        "colors": {"primary": "#059669", "secondary": "#047857", "accent": "#10b981"},
        "features": ["Product grid", "Shopping cart", "Checkout flow", "Reviews section"]
    },
    {
        "id": "saas-landing",
        "name": "SaaS Landing",
        "description": "Conversion-focused template for software products",
        "preview_url": "/templates/saas-landing.png",
        "colors": {"primary": "#0ea5e9", "secondary": "#0284c7", "accent": "#38bdf8"},
        "features": ["Feature comparison", "Pricing tables", "Testimonials", "FAQ section"]
    },
    {
        "id": "healthcare-professional",
        "name": "Healthcare Professional",
        "description": "Trust-building design for medical practices",
        "preview_url": "/templates/healthcare.png",
        "colors": {"primary": "#14b8a6", "secondary": "#0d9488", "accent": "#2dd4bf"},
        "features": ["Services listing", "Doctor profiles", "Appointment booking", "Patient resources"]
    },
    {
        "id": "restaurant-menu",
        "name": "Restaurant & Menu",
        "description": "Appetizing design for food businesses",
        "preview_url": "/templates/restaurant.png",
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
Delivery Pipeline Team"""
    
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
    
    # Auto-update task status based on filled fields
    auto_update_task_status(db, project_id, onboarding)
    
    db.refresh(onboarding)
    
    return onboarding


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
    
    return {
        "project_title": project.title if project else "Unknown Project",
        "project_id": str(onboarding.project_id),
        "completion_percentage": onboarding.completion_percentage,
        "missing_fields": missing_fields,
        "submitted_at": onboarding.submitted_at,
        "missing_fields_eta_json": onboarding.missing_fields_eta_json,
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
            "privacy_policy_url": onboarding.privacy_policy_url,
            "privacy_policy_text": onboarding.privacy_policy_text,
            "selected_template_id": onboarding.selected_template_id,
            "theme_colors": onboarding.theme_colors_json,
            "contacts": onboarding.contacts_json,
            "requirements": onboarding.requirements_json,
            "submitted_at": onboarding.submitted_at,
            "missing_fields_eta_json": onboarding.missing_fields_eta_json,
        },
        "templates": THEME_TEMPLATES,
        "copy_pricing": COPY_PRICING_TIERS,
    }


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
    
    return {"success": True, "completion_percentage": onboarding.completion_percentage}


@client_router.post("/{token}/submit")
def submit_client_onboarding_form(token: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Submit onboarding form and notify the assigned consultant"""
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
    db.commit()

    notification_sent = False
    if project and project.consultant_user_id:
        consultant = db.query(User).filter(User.id == project.consultant_user_id).first()
        if consultant:
            required_fields = resolve_required_fields(db, project)
            missing_fields = get_missing_fields(onboarding, required_fields)
            eta_lines = []
            if isinstance(missing_fields_eta, dict):
                for field, eta in missing_fields_eta.items():
                    eta_lines.append(f"- {field}: {eta}")

            message = "The client submitted the onboarding form."
            if missing_fields:
                message += "\n\nMissing information:\n" + "\n".join([f"- {f}" for f in missing_fields])
            if eta_lines:
                message += "\n\nClient provided ETA:\n" + "\n".join(eta_lines)

            notification_sent = send_client_reminder_email(
                to_emails=[consultant.email],
                subject=f"Client submitted onboarding: {project.title}",
                message=message,
                project_title=project.title,
                sender_name="Delivery Management"
            )

    return {"success": True, "notification_sent": notification_sent}


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
    
    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(onboarding.project_id), "logo")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    onboarding.logo_file_path = file_path
    project = db.query(Project).filter(Project.id == onboarding.project_id).first()
    required_fields = resolve_required_fields(db, project)
    onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
    db.commit()
    
    auto_update_task_status(db, onboarding.project_id, onboarding)
    
    return {"success": True, "file_path": file_path}


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
    
    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(onboarding.project_id), "images")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Add to images list
    images = list(onboarding.images_json or [])
    images.append({"file_path": file_path, "filename": file.filename, "type": "uploaded"})
    onboarding.images_json = images
    flag_modified(onboarding, "images_json")
    project = db.query(Project).filter(Project.id == onboarding.project_id).first()
    required_fields = resolve_required_fields(db, project)
    onboarding.completion_percentage = calculate_completion_percentage(onboarding, required_fields)
    db.commit()
    
    auto_update_task_status(db, onboarding.project_id, onboarding)
    
    return {"success": True, "file_path": file_path, "images": images}


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
    interval_hours: Optional[int] = Query(None, description="Reminder interval in hours (6, 12, or 24)"),
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
    
    onboarding.auto_reminder_enabled = enabled
    
    # Update interval if provided and valid
    if interval_hours and interval_hours in [6, 12, 24]:
        onboarding.reminder_interval_hours = interval_hours
    
    if enabled:
        # Schedule next reminder based on interval
        hours = onboarding.reminder_interval_hours or 24
        if onboarding.completion_percentage < 100:
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
