from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.rate_limit import limiter, PUBLIC_RATE_LIMIT
from app.services.storage import get_storage_backend, LocalDiskStorage
from app.utils.signed_tokens import verify_signed_token
from app.models import Artifact
from uuid import UUID

router = APIRouter(prefix="/public/preview", tags=["preview"])


@router.get("/{token}")
@limiter.limit(PUBLIC_RATE_LIMIT)
def serve_preview_package(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    payload = verify_signed_token(token, purpose="preview")
    if not payload:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    project_id = payload.get("project_id")
    try:
        project_uuid = UUID(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid token")
    artifact = (
        db.query(Artifact)
        .filter(Artifact.project_id == project_uuid, Artifact.artifact_type == "preview_package")
        .order_by(Artifact.created_at.desc())
        .first()
    )
    if not artifact or not artifact.storage_key:
        raise HTTPException(status_code=404, detail="Preview package not found")
    storage = get_storage_backend()
    if not isinstance(storage, LocalDiskStorage):
        url = storage.get_url(artifact.storage_key, expires_seconds=900)
        if not url:
            raise HTTPException(status_code=404, detail="Preview unavailable")
        return RedirectResponse(url)
    data = storage.read_bytes(artifact.storage_key)
    return StreamingResponse(
        iter([data]),
        media_type=artifact.content_type or "application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
