from sqlalchemy.orm import Session
from app.models import Defect, DefectStatus
from app.schemas import DefectCreate, DefectUpdate
from typing import Optional, List
from uuid import UUID
from datetime import datetime


def create_defect_draft(db: Session, project_id: UUID, data: DefectCreate, user) -> Defect:
    """Create a defect draft"""
    defect = Defect(
        project_id=project_id,
        severity=data.severity,
        description=data.description,
        evidence_json=data.evidence_json or {},
        external_id=data.external_id,
        status=DefectStatus.DRAFT
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)
    return defect


def get_defects_by_project(db: Session, project_id: UUID) -> List[Defect]:
    """Get all defects for a project"""
    return db.query(Defect).filter(Defect.project_id == project_id).all()


def validate_defect(db: Session, defect_id: UUID, validation_result: str, notes: Optional[str], user) -> Optional[Defect]:
    """
    Validate a defect
    validation_result: VALID_DEFECT, INVALID_DEFECT, NEED_RETEST
    """
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        return None
    
    # Update defect status based on validation result
    if validation_result == "VALID_DEFECT":
        defect.status = DefectStatus.VALID
    elif validation_result == "INVALID_DEFECT":
        defect.status = DefectStatus.INVALID
    elif validation_result == "NEED_RETEST":
        defect.status = DefectStatus.RETEST
    
    # Add validation notes to evidence
    if notes:
        evidence = defect.evidence_json or {}
        evidence["validation_notes"] = notes
        evidence["validated_by"] = str(user.id)
        evidence["validated_at"] = datetime.utcnow().isoformat()
        defect.evidence_json = evidence
    
    defect.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(defect)
    return defect


def update_defect(db: Session, defect_id: UUID, data: DefectUpdate, user) -> Optional[Defect]:
    """Update a defect"""
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(defect, key, value)
    
    defect.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(defect)
    return defect
