from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Stage, Artifact
from app.schemas import ArtifactResponse
from app.deps import get_current_active_user
from app.services import artifact_service
from app.rbac import check_full_access
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["artifacts"])


@router.post("/{project_id}/artifacts/upload", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_artifact(
    project_id: UUID,
    file: UploadFile = File(...),
    stage: Stage = Form(...),
    artifact_type: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload artifact file
    Role-based stage validation:
    - Admin/Manager can upload to any stage
    - Others can only upload to their allowed stages and only if it's the current stage
    """
    artifact = await artifact_service.upload_artifact(
        db=db,
        project_id=project_id,
        stage=stage,
        file=file,
        artifact_type=artifact_type,
        notes=notes,
        user=current_user
    )
    
    return artifact


@router.get("/{project_id}/artifacts", response_model=List[ArtifactResponse])
def list_artifacts(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all artifacts for a project (all authenticated users)"""
    artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()
    return artifacts


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete artifact (Admin/Manager or uploader only)"""
    success = artifact_service.delete_artifact(db, artifact_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    
    return None
