from sqlalchemy.orm import Session
from app.models import Artifact, Project, Stage, Role
from app.rbac import can_access_stage, check_full_access
from fastapi import UploadFile, HTTPException
from typing import Optional
from uuid import UUID
import os
import shutil
from app.config import settings


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
    
    # Create artifact record
    from app.services.storage_service import s3_enabled, upload_bytes_to_s3
    
    file_url = None
    if s3_enabled():
        # Reset file pointer since we seeked earlier
        file.file.seek(0)
        content = file.file.read()
        key = f"projects/{project_id}/artifacts/{stage.value}/{file.filename}"
        file_url = upload_bytes_to_s3(content, key, file.content_type)
    else:
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(project_id), stage.value)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file locally
        file_path = os.path.join(upload_dir, file.filename)
        file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = file_path
    
    artifact = Artifact(
        project_id=project_id,
        stage=stage,
        type=artifact_type,
        filename=file.filename,
        url=file_url,
        notes=notes,
        uploaded_by_user_id=user.id
    )
    db.add(artifact)
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
    
    # Delete file from filesystem
    if os.path.exists(artifact.url):
        os.remove(artifact.url)
    
    # Delete database record
    db.delete(artifact)
    db.commit()
    
    return True
