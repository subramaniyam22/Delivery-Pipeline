"""
Project template instance: lock which template (and optional fallback) to use for build.
Clone template = client-specific copy; we record template_id per project for immutable build.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ProjectTemplateInstance, Project, TemplateRegistry


def ensure_template_instance(
    db: Session,
    project_id: UUID,
    template_id: Optional[UUID] = None,
) -> Optional[ProjectTemplateInstance]:
    """Create or update project template instance with selected template_id. Returns instance or None."""
    if not template_id:
        return None
    instance = db.query(ProjectTemplateInstance).filter(ProjectTemplateInstance.project_id == project_id).first()
    if instance:
        instance.template_id = template_id
        instance.updated_at = datetime.utcnow()
    else:
        instance = ProjectTemplateInstance(project_id=project_id, template_id=template_id)
        db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def get_template_id_for_build(db: Session, project_id: UUID) -> Optional[UUID]:
    """Return template_id to use for BUILD: from ProjectTemplateInstance or onboarding, with fallback if confirmed."""
    instance = db.query(ProjectTemplateInstance).filter(ProjectTemplateInstance.project_id == project_id).first()
    if instance and instance.template_id:
        template = db.query(TemplateRegistry).filter(TemplateRegistry.id == instance.template_id).first()
        if template and getattr(template, "is_active", True):
            return instance.template_id
        if instance.fallback_template_id and instance.fallback_confirmed_at:
            return instance.fallback_template_id
    from app.models import OnboardingData
    ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
    if ob and getattr(ob, "selected_template_id", None):
        try:
            tid = UUID(str(ob.selected_template_id))
            t = db.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
            if t and getattr(t, "is_active", True):
                return tid
        except (ValueError, TypeError):
            pass
    return None


def get_fallback_callout(project_id: UUID, db: Session) -> Optional[str]:
    """If project used fallback template with approval, return callout message."""
    instance = db.query(ProjectTemplateInstance).filter(ProjectTemplateInstance.project_id == project_id).first()
    if instance and instance.use_fallback_callout:
        return "A safe fallback template was used with your approval."
    return None


def confirm_fallback(
    db: Session,
    project_id: UUID,
    fallback_template_id: Optional[UUID] = None,
) -> Optional[ProjectTemplateInstance]:
    """Client confirmed use of fallback template. Sets fallback_template_id and fallback_confirmed_at. Returns instance."""
    instance = db.query(ProjectTemplateInstance).filter(ProjectTemplateInstance.project_id == project_id).first()
    if not instance:
        instance = ProjectTemplateInstance(project_id=project_id, template_id=None)
        db.add(instance)
        db.flush()
    if fallback_template_id:
        instance.fallback_template_id = fallback_template_id
    instance.fallback_confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(instance)
    return instance
