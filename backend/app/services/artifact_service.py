from sqlalchemy.orm import Session
from app.models import Artifact, Project, Stage, Role, AuditLog
from app.rbac import can_access_stage, check_full_access
from fastapi import UploadFile, HTTPException
from typing import Optional, Dict, Any
from uuid import UUID
import os
from app.config import settings
from app.services.storage import get_storage_backend


def validate_stage_permission(project: Project, stage: Stage, user) -> bool:
    """
    Validate if user can upload artifacts to a specific stage
    Admin/Manager can upload to any stage
    Others can only upload to their allowed stages and only if it's the current stage
    """
    # Admin and Manager can upload to any stage
    if check_full_access(user.role):
        return True
    
    # Stage must match current project stage
    if project.current_stage != stage:
        return False
    
    # Check if user has access to this stage
    return can_access_stage(user.role, stage)


async def upload_artifact(
    db: Session,
    project_id: UUID,
    stage: Stage,
    file: UploadFile,
    artifact_type: str,
    notes: Optional[str],
    user
) -> Artifact:
    """Upload an artifact file"""
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate stage permission
    if not validate_stage_permission(project, stage, user):
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to upload artifacts to {stage.value} stage"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    storage = get_storage_backend()
    file.file.seek(0)
    content = file.file.read()
    storage_key = f"projects/{project_id}/artifacts/{stage.value}/{file.filename}"
    stored = storage.save_bytes(storage_key, content, file.content_type)
    
    artifact = Artifact(
        project_id=project_id,
        stage=stage,
        type=artifact_type,
        artifact_type=artifact_type,
        filename=file.filename,
        storage_key=stored.storage_key,
        url=stored.url or "",
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        checksum=stored.checksum,
        notes=notes,
        metadata_json={},
        uploaded_by_user_id=user.id
    )
    db.add(artifact)
    db.flush()
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=user.id,
            action="ARTIFACT_UPLOADED",
            payload_json={
                "artifact_id": str(artifact.id),
                "filename": file.filename,
                "stage": stage.value,
                "artifact_type": artifact_type,
            },
        )
    )
    db.commit()
    db.refresh(artifact)
    
    return artifact


def create_artifact_from_bytes(
    db: Session,
    project_id: UUID,
    stage: Stage,
    filename: str,
    content: bytes,
    artifact_type: str,
    uploaded_by_user_id: UUID,
    notes: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> Artifact:
    storage = get_storage_backend()
    storage_key = f"projects/{project_id}/artifacts/{stage.value}/{filename}"
    stored = storage.save_bytes(storage_key, content, "application/octet-stream")

    artifact = Artifact(
        project_id=project_id,
        stage=stage,
        type=artifact_type,
        artifact_type=artifact_type,
        filename=filename,
        storage_key=stored.storage_key,
        url=stored.url or "",
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        checksum=stored.checksum,
        notes=notes,
        metadata_json=metadata_json or {},
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(artifact)
    db.flush()
    db.add(
        AuditLog(
            project_id=project_id,
            actor_user_id=uploaded_by_user_id,
            action="ARTIFACT_UPLOADED",
            payload_json={
                "artifact_id": str(artifact.id),
                "filename": filename,
                "stage": stage.value,
                "artifact_type": artifact_type,
            },
        )
    )
    db.commit()
    db.refresh(artifact)
    return artifact


def delete_artifact(db: Session, artifact_id: UUID, user) -> bool:
    """Delete an artifact (Admin/Manager or uploader only)"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        return False
    
    # Check permission
    if not check_full_access(user.role) and artifact.uploaded_by_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this artifact"
        )
    
    storage = get_storage_backend()
    if artifact.storage_key:
        try:
            storage.delete(artifact.storage_key)
        except Exception:
            pass
    
    # Delete database record
    db.delete(artifact)
    db.commit()
    
    return True


def get_artifact_bytes(artifact: Artifact) -> bytes:
    storage = get_storage_backend()
    if artifact.storage_key:
        return storage.read_bytes(artifact.storage_key)
    if artifact.url and os.path.exists(artifact.url):
        with open(artifact.url, "rb") as handle:
            return handle.read()
    raise FileNotFoundError("Artifact storage not found")
