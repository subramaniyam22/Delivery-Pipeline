from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import html

from app.db import get_db
from app.db import SessionLocal
from app.deps import get_current_active_user
from app.models import TemplateRegistry, User, AuditLog
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse
from app.config import settings
from app.rbac import require_admin_manager

router = APIRouter(tags=["templates"])


def _require_admin_manager(user: User) -> None:
    require_admin_manager(user)


def _build_preview_html(template: TemplateRegistry) -> str:
    name = html.escape(template.name or "Untitled Template")
    description = html.escape(template.description or "")
    intent = html.escape(template.intent or "")
    features = template.features_json or []
    feature_items = "\n".join([f"<li>{html.escape(item)}</li>" for item in features]) or "<li>No features listed</li>"
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} Preview</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      background: #f8fafc;
      color: #0f172a;
    }}
    .hero {{
      background: linear-gradient(135deg, #2563eb, #22d3ee);
      color: white;
      padding: 48px 32px;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      padding: 24px;
      margin-top: -32px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}
    .meta-item {{
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px;
      background: #f8fafc;
    }}
    h1 {{
      margin: 0 0 8px 0;
      font-size: 32px;
    }}
    h2 {{
      margin: 0 0 12px 0;
      font-size: 20px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
  </style>
</head>
<body>
  <div class="hero">
    <div class="container">
      <h1>{name}</h1>
      <p>{description}</p>
    </div>
  </div>
  <div class="container">
    <div class="card">
      <h2>Template Intent</h2>
      <p>{intent or "Intent not provided yet."}</p>
      <div class="meta">
        <div class="meta-item">
          <h2>Features</h2>
          <ul>
            {feature_items}
          </ul>
        </div>
        <div class="meta-item">
          <h2>Generated Preview</h2>
          <p>This preview is AI-generated and updates when you regenerate.</p>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


def _generate_template_preview(template_id: str) -> None:
    db = SessionLocal()
    try:
        template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            return
        preview_root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "generated_previews"
        )
        os.makedirs(preview_root, exist_ok=True)
        template_dir = os.path.join(preview_root, str(template.id))
        os.makedirs(template_dir, exist_ok=True)
        html_content = _build_preview_html(template)
        index_path = os.path.join(template_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as handle:
            handle.write(html_content)
        base_url = settings.BACKEND_URL or "http://localhost:8000"
        template.preview_url = f"{base_url}/previews/{template.id}/index.html"
        template.preview_status = "ready"
        template.preview_error = None
        template.preview_last_generated_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        if template_id:
            template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
            if template:
                template.preview_status = "failed"
                template.preview_error = str(exc)
                template.preview_last_generated_at = datetime.utcnow()
                db.commit()
    finally:
        db.close()


@router.get("/templates", response_model=List[TemplateResponse])
@router.get("/api/templates", response_model=List[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    return db.query(TemplateRegistry).order_by(TemplateRegistry.created_at.desc()).all()


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/api/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    source_type = (data.source_type or "ai").lower()
    if source_type not in ["ai", "git"]:
        raise HTTPException(status_code=400, detail="Invalid source_type")
    if source_type == "git" and not data.repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required for git templates")
    template = TemplateRegistry(
        name=data.name,
        repo_url=data.repo_url,
        default_branch=data.default_branch or ("main" if source_type == "git" else None),
        meta_json=data.meta_json or {},
        description=data.description,
        features_json=data.features_json or [],
        preview_url=data.preview_url,
        source_type=source_type,
        intent=data.intent,
        preview_status=data.preview_status or "not_generated",
        preview_last_generated_at=data.preview_last_generated_at,
        preview_error=data.preview_error,
        preview_thumbnail_url=data.preview_thumbnail_url,
        is_active=True if data.is_active is None else data.is_active,
        is_published=True if data.is_published is None else data.is_published,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_CREATED",
            payload_json={"template_id": str(template.id), "name": template.name},
        )
    )
    db.commit()
    return template


@router.get("/templates/{template_id}", response_model=TemplateResponse)
@router.get("/api/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
@router.put("/api/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    updates = data.model_dump(exclude_unset=True)
    if "source_type" in updates:
        source_type = str(updates["source_type"]).lower()
        if source_type not in ["ai", "git"]:
            raise HTTPException(status_code=400, detail="Invalid source_type")
        if source_type == "git" and not (updates.get("repo_url") or template.repo_url):
            raise HTTPException(status_code=400, detail="repo_url is required for git templates")
        updates["source_type"] = source_type
    for key, value in updates.items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    if "is_published" in updates:
        db.add(
            AuditLog(
                project_id=None,
                actor_user_id=current_user.id,
                action="TEMPLATE_PUBLISHED" if updates.get("is_published") else "TEMPLATE_UNPUBLISHED",
                payload_json={"template_id": str(template.id), "name": template.name},
            )
        )
        db.commit()
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_UPDATED",
            payload_json={"template_id": str(template.id), "updates": updates},
        )
    )
    db.commit()
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/api/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_DELETED",
            payload_json={"template_id": str(template_id), "name": template.name},
        )
    )
    db.commit()


@router.post("/api/templates/{template_id}/generate-preview")
def generate_template_preview(
    template_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.source_type == "git":
        raise HTTPException(status_code=400, detail="Preview generation is only supported for AI templates")
    template.preview_status = "generating"
    template.preview_error = None
    db.commit()
    background_tasks.add_task(_generate_template_preview, template_id)
    return {"preview_status": "generating"}
