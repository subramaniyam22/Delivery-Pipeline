from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Tuple
from datetime import datetime
import os
import html
import copy
import uuid

from app.db import get_db
from app.db import SessionLocal
from app.deps import get_current_active_user
from app.models import TemplateRegistry, User, AuditLog
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse, SetRecommendedBody
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


# Preview generation: stubbed implementation. To plug real preview infra (e.g. headless browser,
# static export from framework), replace _build_preview_html and file write with your pipeline.
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
    q: Optional[str] = Query(None, description="Search by name/description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    style: Optional[str] = Query(None, description="Filter by style"),
    tag: Optional[str] = Query(None, description="Filter by feature tag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    query = db.query(TemplateRegistry)
    if q:
        q_like = f"%{q}%"
        query = query.filter(
            or_(
                TemplateRegistry.name.ilike(q_like),
                (TemplateRegistry.description or "").ilike(q_like),
            )
        )
    if status:
        query = query.filter(TemplateRegistry.status == status)
    if category:
        query = query.filter(TemplateRegistry.category == category)
    if style:
        query = query.filter(TemplateRegistry.style == style)
    if tag:
        query = query.filter(
            TemplateRegistry.feature_tags_json.op("@>")(cast([tag], JSONB))
        )
    return query.order_by(TemplateRegistry.created_at.desc()).all()


@router.get("/api/templates/demo-dataset")
def get_demo_dataset(
    key: str = Query(..., description="Demo dataset key (e.g. pmc_default_v1)"),
    current_user: User = Depends(get_current_active_user),
):
    """Return the JSON demo dataset for preview rendering. Admin/manager only."""
    _require_admin_manager(current_user)
    from app.services.demo_preview_data import get_demo_dataset_by_key
    data = get_demo_dataset_by_key(key)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Demo dataset not found for key: {key}")
    return data


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
        category=getattr(data, "category", None),
        style=getattr(data, "style", None),
        feature_tags_json=getattr(data, "feature_tags_json", None) or getattr(data, "features_json", None) or [],
        status=getattr(data, "status", None) or "draft",
        is_default=getattr(data, "is_default", False) or False,
        is_recommended=getattr(data, "is_recommended", False) or False,
        repo_path=getattr(data, "repo_path", None),
        pages_json=getattr(data, "pages_json", None) or [],
        required_inputs_json=getattr(data, "required_inputs_json", None) or [],
        optional_inputs_json=getattr(data, "optional_inputs_json", None) or [],
        default_config_json=getattr(data, "default_config_json", None) or {},
        rules_json=getattr(data, "rules_json", None) or [],
        validation_results_json=getattr(data, "validation_results_json", None) or {},
        version=getattr(data, "version", None) or 1,
        changelog=getattr(data, "changelog", None),
        parent_template_id=getattr(data, "parent_template_id", None),
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
    # If published template is edited, revert to draft
    content_keys = {"name", "description", "intent", "features_json", "pages_json", "required_inputs_json",
                    "optional_inputs_json", "default_config_json", "rules_json", "category", "style",
                    "feature_tags_json", "repo_url", "repo_path", "default_branch"}
    if (template.status == "published" or template.is_published) and content_keys.intersection(updates.keys()):
        updates["status"] = "draft"
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
    current_user: User = Depends(get_current_active_user),
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


def _run_validation_checks(template: TemplateRegistry) -> Tuple[bool, dict]:
    """Stub validation. Replace with Lighthouse/axe-core or other quality gates when integrated."""
    results = {}
    # Required: preview_status == "ready"
    preview_ok = (template.preview_status or "") == "ready"
    results["preview_ready"] = preview_ok
    # Required: pages_json contains at least one page
    pages = template.pages_json if isinstance(getattr(template, "pages_json", None), list) else []
    pages_ok = len(pages) >= 1
    results["has_pages"] = pages_ok
    # Required: pages contain home or contact OR any section with "cta"
    has_home_contact_or_cta = False
    for p in pages:
        if not isinstance(p, dict):
            continue
        slug = (p.get("slug") or "").lower()
        title = (p.get("title") or "").lower()
        if slug in ("home", "contact") or "home" in title or "contact" in title:
            has_home_contact_or_cta = True
            break
        for s in (p.get("sections") or []):
            if isinstance(s, dict) and "cta" in str(s).lower():
                has_home_contact_or_cta = True
                break
    if not pages:
        has_home_contact_or_cta = False
    results["home_or_contact_or_cta"] = has_home_contact_or_cta
    all_ok = preview_ok and pages_ok and has_home_contact_or_cta
    return all_ok, results


@router.post("/api/templates/{template_id}/duplicate", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def duplicate_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    source = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Template not found")
    # Create copy (exclude id, created_at; set status draft, is_default False)
    new_id = uuid.uuid4()
    template = TemplateRegistry(
        id=new_id,
        name=source.name + " (Copy)",
        repo_url=source.repo_url,
        default_branch=source.default_branch,
        meta_json=copy.deepcopy(source.meta_json or {}),
        description=source.description,
        features_json=copy.deepcopy(source.features_json or []),
        preview_url=None,
        source_type=source.source_type,
        intent=source.intent,
        preview_status="not_generated",
        preview_last_generated_at=None,
        preview_error=None,
        preview_thumbnail_url=source.preview_thumbnail_url,
        is_active=source.is_active,
        is_published=False,
        category=source.category,
        style=source.style,
        feature_tags_json=copy.deepcopy(getattr(source, "feature_tags_json", None) or source.features_json or []),
        status="draft",
        is_default=False,
        is_recommended=getattr(source, "is_recommended", False),
        repo_path=source.repo_path,
        pages_json=copy.deepcopy(getattr(source, "pages_json", None) or []),
        required_inputs_json=copy.deepcopy(getattr(source, "required_inputs_json", None) or []),
        optional_inputs_json=copy.deepcopy(getattr(source, "optional_inputs_json", None) or []),
        default_config_json=copy.deepcopy(getattr(source, "default_config_json", None) or {}),
        rules_json=copy.deepcopy(getattr(source, "rules_json", None) or []),
        validation_results_json={},
        version=getattr(source, "version", 1),
        changelog=None,
        parent_template_id=source.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_DUPLICATED",
            payload_json={"source_id": str(template_id), "new_id": str(template.id), "name": template.name},
        )
    )
    db.commit()
    return template


@router.post("/api/templates/{template_id}/validate", response_model=dict)
def validate_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    passed, results = _run_validation_checks(template)
    existing = getattr(template, "validation_results_json", None) or {}
    template.validation_results_json = dict(existing, **results, passed=passed)
    if passed:
        template.status = "validated"
    db.commit()
    db.refresh(template)
    return {"passed": passed, "results": results, "status": template.status}


@router.post("/api/templates/{template_id}/publish", response_model=TemplateResponse)
def publish_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if (getattr(template, "status", None) or "") != "validated":
        raise HTTPException(status_code=400, detail="Template must be validated before publish")
    if (template.preview_status or "") != "ready":
        raise HTTPException(status_code=400, detail="Preview must be ready before publish")
    # Enforce single default: clear other defaults
    for t in db.query(TemplateRegistry).filter(TemplateRegistry.is_default == True).all():
        t.is_default = False
    template.status = "published"
    template.is_published = True
    db.commit()
    db.refresh(template)
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_PUBLISHED",
            payload_json={"template_id": str(template.id), "name": template.name},
        )
    )
    db.commit()
    return template


@router.post("/api/templates/{template_id}/archive", response_model=TemplateResponse)
def archive_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.status = "archived"
    template.is_active = False
    if template.is_default:
        template.is_default = False
    db.commit()
    db.refresh(template)
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=current_user.id,
            action="TEMPLATE_ARCHIVED",
            payload_json={"template_id": str(template.id), "name": template.name},
        )
    )
    db.commit()
    return template


@router.post("/api/templates/{template_id}/set-default", response_model=TemplateResponse)
def set_default_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not template.is_published and (getattr(template, "status", None) or "") != "published":
        raise HTTPException(status_code=400, detail="Only published templates can be set as default")
    for t in db.query(TemplateRegistry).filter(TemplateRegistry.is_default == True).all():
        t.is_default = False
    template.is_default = True
    db.commit()
    db.refresh(template)
    return template


@router.post("/api/templates/{template_id}/set-recommended", response_model=TemplateResponse)
def set_recommended_template(
    template_id: str,
    body: SetRecommendedBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.is_recommended = body.value
    db.commit()
    db.refresh(template)
    return template
