from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from typing import Any, List, Optional, Tuple
from datetime import datetime
import logging
import os
import html
import copy
import uuid

from app.db import get_db
from app.db import SessionLocal
from app.deps import get_current_active_user, get_current_user_for_preview
from app.models import TemplateRegistry, User, AuditLog, TemplateBlueprintJob, TemplateBlueprintRun, TemplateValidationJob, TemplateEvolutionProposal, ClientSentiment, Project, DeliveryOutcome
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse, SetRecommendedBody
from app.config import settings
from app.rbac import require_admin_manager
from app.services.storage import refresh_presigned_thumbnail_url, get_preview_storage_backend

router = APIRouter(tags=["templates"])


def _require_admin_manager(user: User) -> None:
    require_admin_manager(user)


def _normalize_template_meta_images(template: TemplateRegistry) -> None:
    """Ensure meta_json.images is category -> list of URLs so API always returns arrays (fixes legacy single string)."""
    if not getattr(template, "meta_json", None) or not isinstance(template.meta_json, dict):
        return
    images = template.meta_json.get("images")
    if not images or not isinstance(images, dict):
        return
    normalized = {}
    for k, v in images.items():
        if isinstance(v, list):
            normalized[k] = [u for u in v if u]
        else:
            normalized[k] = [v] if v else []
    template.meta_json = {**template.meta_json, "images": normalized}


def _display_error_message(error_code: Optional[str], error_message: Optional[str], error_details: Optional[str]) -> str:
    """Return a safe display message; normalize OPENAI 429/quota for old runs that stored the generic message."""
    msg = (error_message or "").strip()
    details = (error_details or "").lower()
    if error_code == "OPENAI_ERROR" and details and ("429" in details or "quota" in details or "insufficient_quota" in details or "ratelimit" in details):
        if not msg or msg == "Blueprint generation failed. See details.":
            return "OpenAI quota or rate limit exceeded. Check your plan and billing at platform.openai.com."
    return msg or "Blueprint generation failed. See details."


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


def _run_template_preview_pipeline(task_template_id: str) -> None:
    """Background task: run real preview pipeline (render + storage + thumbnail)."""
    from app.jobs.template_preview import run_template_preview_pipeline
    from uuid import UUID
    run_template_preview_pipeline(UUID(task_template_id))


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
    templates = query.order_by(TemplateRegistry.created_at.desc()).all()
    for t in templates:
        if getattr(t, "preview_thumbnail_url", None):
            t.preview_thumbnail_url = refresh_presigned_thumbnail_url(t.preview_thumbnail_url)
        _normalize_template_meta_images(t)
    return templates


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
    def _trunc(s: Optional[str], max_len: int) -> Optional[str]:
        if not s:
            return s
        return s[:max_len] if len(s) > max_len else s

    try:
        template = TemplateRegistry(
            name=(data.name or "Untitled Template")[:255],
            repo_url=_trunc(data.repo_url, 1000),
            default_branch=_trunc(data.default_branch or ("main" if source_type == "git" else None), 255),
            meta_json=data.meta_json if isinstance(getattr(data, "meta_json", None), dict) else {},
            description=data.description,
            features_json=data.features_json if isinstance(data.features_json, list) else [],
            preview_url=_trunc(data.preview_url, 1000),
            source_type=source_type[:20],
            intent=data.intent,
            preview_status=_trunc(data.preview_status or "not_generated", 30),
            preview_last_generated_at=data.preview_last_generated_at,
            preview_error=data.preview_error,
            preview_thumbnail_url=_trunc(data.preview_thumbnail_url, 1000),
            is_active=True if data.is_active is None else data.is_active,
            is_published=True if data.is_published is None else data.is_published,
            category=_trunc(getattr(data, "category", None), 50),
            style=_trunc(getattr(data, "style", None), 50),
            feature_tags_json=getattr(data, "feature_tags_json", None) or getattr(data, "features_json", None) or [],
            status=_trunc(getattr(data, "status", None) or "draft", 30),
            is_default=getattr(data, "is_default", False) or False,
            is_recommended=getattr(data, "is_recommended", False) or False,
            repo_path=_trunc(getattr(data, "repo_path", None), 1000),
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
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).exception("Create template failed: %s", e)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Template creation failed: {str(e)}")


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
    if getattr(template, "preview_thumbnail_url", None):
        template.preview_thumbnail_url = refresh_presigned_thumbnail_url(template.preview_thumbnail_url)
    _normalize_template_meta_images(template)
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


@router.get("/templates/{template_id}/references")
@router.get("/api/templates/{template_id}/references")
def get_template_references(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List projects and records that reference this template (for resolving 409 on delete)."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template_id_str = str(template_id)
    projects_using = db.query(Project.id, Project.title, Project.status).filter(
        Project.selected_template_id == template_id_str,
    ).all()
    delivery_outcomes = db.query(DeliveryOutcome.id, DeliveryOutcome.project_id).filter(
        DeliveryOutcome.template_registry_id == template.id,
    ).all()
    sentiments = db.query(ClientSentiment.id, ClientSentiment.project_id).filter(
        ClientSentiment.template_registry_id == template.id,
    ).all()
    blueprint_runs = db.query(TemplateBlueprintRun.id).filter(
        TemplateBlueprintRun.template_id == template.id,
    ).count()
    blueprint_jobs = db.query(TemplateBlueprintJob.id).filter(
        TemplateBlueprintJob.template_id == template.id,
    ).count()
    validation_jobs = db.query(TemplateValidationJob.id).filter(
        TemplateValidationJob.template_id == template.id,
    ).count()
    evolution_proposals = db.query(TemplateEvolutionProposal.id).filter(
        TemplateEvolutionProposal.template_id == template.id,
    ).count()
    def _proj_row(p) -> dict:
        pid, title, status = (p[0], p[1], p[2]) if hasattr(p, "__getitem__") else (getattr(p, "id", None), getattr(p, "title", None), getattr(p, "status", None))
        return {"id": str(pid), "title": title or "", "status": getattr(status, "value", str(status)) if status is not None else ""}
    def _outcome_row(d) -> dict:
        oid, proj_id = (d[0], d[1]) if hasattr(d, "__getitem__") else (getattr(d, "id", None), getattr(d, "project_id", None))
        return {"id": str(oid), "project_id": str(proj_id)}
    return {
        "template_id": template_id_str,
        "template_name": template.name,
        "projects": [_proj_row(p) for p in projects_using],
        "delivery_outcomes": [_outcome_row(d) for d in delivery_outcomes],
        "client_sentiments": [_outcome_row(s) for s in sentiments],
        "counts": {
            "template_blueprint_runs": blueprint_runs,
            "template_blueprint_jobs": blueprint_jobs,
            "template_validation_jobs": validation_jobs,
            "template_evolution_proposals": evolution_proposals,
        },
        "summary": (
            f"{len(projects_using)} project(s), {len(delivery_outcomes)} delivery outcome(s), {len(sentiments)} sentiment(s), "
            f"{blueprint_runs} blueprint run(s), {validation_jobs} validation job(s), {evolution_proposals} evolution proposal(s)"
        ),
    }


def _template_has_references(db: Session, template_id: str) -> Tuple[bool, dict]:
    """Return (has_refs, references_dict) for the given template (by id string)."""
    from uuid import UUID
    tid = UUID(template_id)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
    if not template:
        return False, {}
    projects_using = db.query(Project.id, Project.title, Project.status).filter(
        Project.selected_template_id == template_id,
    ).all()
    delivery_outcomes = db.query(DeliveryOutcome.id).filter(
        DeliveryOutcome.template_registry_id == tid,
    ).count()
    sentiments = db.query(ClientSentiment.id).filter(
        ClientSentiment.template_registry_id == tid,
    ).count()
    # Row/tuple: (id, title, status) - use index access for compatibility
    def _row_to_project(p) -> dict:
        pid, title, status = (p[0], p[1], p[2]) if hasattr(p, "__getitem__") else (getattr(p, "id", None), getattr(p, "title", None), getattr(p, "status", None))
        return {"id": str(pid), "title": title or "", "status": getattr(status, "value", str(status)) if status is not None else ""}
    refs = {
        "projects": [_row_to_project(p) for p in projects_using],
        "delivery_outcomes_count": delivery_outcomes,
        "client_sentiments_count": sentiments,
    }
    has = len(projects_using) > 0 or delivery_outcomes > 0 or sentiments > 0
    return has, refs


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/api/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    _require_admin_manager(current_user)
    try:
        from uuid import UUID
        tid = UUID(template_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Template not found")
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template_name = getattr(template, "name", None) or ""
    is_published = getattr(template, "is_published", False) or (getattr(template, "status", None) or "").lower() == "published"
    if is_published:
        try:
            has_refs, refs = _template_has_references(db, template_id)
        except Exception as e:
            logging.getLogger(__name__).exception("Template delete: failed to check references: %s", e)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Template could not be deleted: failed to check references. Please try again or contact support.",
            ) from e
        if has_refs:
            project_titles = [p.get("title", "") for p in refs.get("projects", [])]
            detail = {
                "message": "Published template cannot be deleted because it is referenced. Remove or change template selection on linked projects first.",
                "references": refs,
                "project_titles": project_titles,
            }
            raise HTTPException(status_code=409, detail=detail)
    # Clear project references (selected_template_id is a string column, not FK) so delete is not blocked
    try:
        db.query(Project).filter(Project.selected_template_id == str(template_id)).update(
            {Project.selected_template_id: None}, synchronize_session="fetch"
        )
    except Exception as clear_err:
        logging.getLogger(__name__).warning("Template delete: clear project refs: %s", clear_err)
    try:
        db.delete(template)
        db.add(
            AuditLog(
                project_id=None,
                actor_user_id=current_user.id,
                action="TEMPLATE_DELETED",
                payload_json={"template_id": str(template_id), "name": template_name},
            )
        )
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logging.getLogger(__name__).warning("Template delete integrity error: %s", e)
        try:
            has_refs, refs = _template_has_references(db, template_id)
        except Exception as ref_err:
            logging.getLogger(__name__).warning("Template delete: failed to get references after integrity error: %s", ref_err)
            refs = {}
        detail = {
            "message": "Template cannot be deleted because it is referenced by projects or other data. Remove those references first.",
            "references": refs,
        } if refs else "Template cannot be deleted due to database constraints."
        raise HTTPException(status_code=409, detail=detail) from e
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logging.getLogger(__name__).exception("Template delete unexpected error: %s", e)
        err_msg = (str(e) or type(e).__name__)[:200]
        raise HTTPException(
            status_code=500,
            detail=f"Template could not be deleted: {err_msg}",
        ) from e


def _template_preview_prefix(template: TemplateRegistry) -> str:
    """Same logic as template_preview._template_prefix for proxy consistency."""
    slug = (getattr(template, "slug", None) or "template")
    if isinstance(slug, str):
        slug = slug.replace(" ", "-").lower()[:64]
    else:
        slug = "template"
    version = getattr(template, "version", None) or 1
    return f"templates/{slug}/v{version}"


@router.get("/api/templates/{template_id}/preview")
@router.get("/api/templates/{template_id}/preview/{path:path}")
def serve_template_preview(
    template_id: str,
    path: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_for_preview),
):
    """Serve preview assets from storage. Auth via Bearer or ?access_token= for iframe; subresources (e.g. about.html) allowed when Referer is trusted."""
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if (template.preview_status or "") != "ready":
        raise HTTPException(status_code=404, detail="Preview not ready")
    file_path = (path or "").strip().lstrip("/") or "index.html"
    if ".." in file_path or any(seg.startswith(".") for seg in file_path.split("/")):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not file_path.endswith((".html", ".css", ".js")):
        file_path = file_path + ".html" if file_path and not file_path.endswith("/") else "index.html"
    prefix = _template_preview_prefix(template)
    key = f"{prefix.rstrip('/')}/{file_path}"
    try:
        backend = get_preview_storage_backend()
        body = backend.read_bytes(key)
    except Exception as e:
        logging.warning("Preview proxy read failed key=%s: %s", key, e)
        raise HTTPException(status_code=404, detail="Preview file not found")
    media_type = "text/html"
    if key.endswith(".css"):
        media_type = "text/css"
    elif key.endswith(".js"):
        media_type = "application/javascript"
    headers = {"Content-Security-Policy": "frame-ancestors *"}
    return Response(content=body, media_type=media_type, headers=headers)


@router.post("/api/templates/{template_id}/generate-preview")
def generate_template_preview(
    template_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    body: Optional[dict] = None,
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.source_type == "git":
        raise HTTPException(status_code=400, detail="Preview generation is only supported for AI templates")
    blueprint = getattr(template, "blueprint_json", None)
    if not blueprint or not isinstance(blueprint, dict):
        raise HTTPException(status_code=400, detail="Generate blueprint first")
    data = body or {}
    force = data.get("force", False)
    if not force and (template.preview_status or "") == "ready" and getattr(template, "blueprint_hash", None):
        existing_hash = getattr(template, "blueprint_hash", None)
        if existing_hash:
            raise HTTPException(status_code=409, detail="Preview already up-to-date")
    template.preview_status = "generating"
    template.preview_error = None
    db.commit()
    background_tasks.add_task(_run_template_preview_pipeline, template_id)
    return {"preview_status": "generating"}


@router.post("/api/templates/{template_id}/preview/reset")
def reset_template_preview(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Clear stuck 'generating' preview status so the template can be retried or deleted. Admin/Manager only."""
    _require_admin_manager(current_user)
    try:
        from uuid import UUID
        tid = UUID(template_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Template not found")
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.preview_status = "not_generated"
    template.preview_error = None
    db.commit()
    return {"preview_status": "not_generated"}


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    body: Optional[dict] = None,
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body or {}
    force = data.get("force", False)
    job = TemplateValidationJob(
        template_id=uuid.UUID(template_id),
        status="queued",
        payload_json={"force": force},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    from app.jobs.template_validation import run_validation_job
    if background_tasks:
        background_tasks.add_task(run_validation_job, job.id)
    return {"job_id": str(job.id), "template_id": template_id}


@router.get("/api/templates/{template_id}/validation-job")
def get_template_validation_job(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)
    job = (
        db.query(TemplateValidationJob)
        .filter(TemplateValidationJob.template_id == template_id)
        .order_by(TemplateValidationJob.created_at.desc())
        .first()
    )
    if not job:
        return {"job_id": None, "status": None}
    return {
        "job_id": str(job.id),
        "status": job.status,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_text": job.error_text,
        "result_json": job.result_json,
    }


@router.post("/api/templates/{template_id}/validate-copy", response_model=dict)
def validate_template_copy(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Run copy agent: validate accuracy and relevancy of template copy. Result stored in meta_json.copy_validation."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    blueprint = getattr(template, "blueprint_json", None) or {}
    if not blueprint:
        raise HTTPException(status_code=400, detail="Generate blueprint first")
    meta = dict(template.meta_json or {})
    industry = (meta.get("industry") or "real_estate").strip() or "real_estate"
    from app.agents.templates.copy_agent import validate_copy
    result = validate_copy(blueprint, industry=industry)
    meta["copy_validation"] = result
    template.meta_json = meta
    db.commit()
    db.refresh(template)
    return result


@router.post("/api/templates/{template_id}/validate-seo", response_model=dict)
def validate_template_seo(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Run SEO agent: validate meta titles, descriptions, h1. Result stored in meta_json.seo_validation."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    blueprint = getattr(template, "blueprint_json", None) or {}
    if not blueprint:
        raise HTTPException(status_code=400, detail="Generate blueprint first")
    meta = dict(template.meta_json or {})
    industry = (meta.get("industry") or "real_estate").strip() or "real_estate"
    from app.agents.templates.seo_agent import validate_seo
    result = validate_seo(blueprint, industry=industry)
    meta["seo_validation"] = result
    template.meta_json = meta
    db.commit()
    db.refresh(template)
    return result


FIX_BLUEPRINT_SYSTEM = """You are an expert at diagnosing template validation and build failures. You will receive a list of validation "failed_reasons" (error messages from Lighthouse, Axe, Playwright, or other tools). Your job is to respond in JSON with these keys:
- plain_language_summary: 2-4 sentences for a non-technical person explaining what went wrong and what they can do next (e.g. "The validation failed because the preview environment is missing some tools. Your template content is fine. Ask your technical team to install the tools below, or you can continue editing the blueprint and re-run validation after the environment is fixed.")
- technical_details: Optional. A short technical explanation (for developers).
- code_snippets: Optional. List of objects with "title" and "code" (string). Only include if the fix involves running a command or changing config (e.g. npm install -g lighthouse, playwright install). Use markdown code blocks in "code" if helpful.
- interim_actions: Optional. List of short bullet strings (what to do in the meantime).

Respond only with valid JSON, no markdown wrapper."""


@router.get("/api/templates/{template_id}/fix-blueprint-suggestions", response_model=dict)
def get_fix_blueprint_suggestions(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Use AI to suggest how to fix validation/blueprint errors. Returns plain-language summary, optional technical details and code snippets."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    vr = getattr(template, "validation_results_json", None) or {}
    failed = vr.get("failed_reasons")
    if not failed or not isinstance(failed, list):
        return {
            "plain_language_summary": "No validation failures were found for this template. If you are seeing errors in the UI, try running validation again.",
            "technical_details": None,
            "code_snippets": [],
            "interim_actions": [],
        }
    errors_text = "\n".join(f"- {r}" for r in failed[:20])
    user_prompt = f"Validation failed with these reasons:\n{errors_text}\n\nProvide the JSON response as specified."
    try:
        from app.agents.prompts import get_llm
        from app.utils.llm import invoke_llm
        import json
        llm = get_llm(task="analysis")
        raw = invoke_llm(llm, FIX_BLUEPRINT_SYSTEM + "\n\n" + user_prompt)
        content = raw.content if hasattr(raw, "content") else str(raw)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()
        out = json.loads(content)
        return {
            "plain_language_summary": out.get("plain_language_summary") or "We couldn't generate a summary. Please share the failed reasons with your technical team.",
            "technical_details": out.get("technical_details"),
            "code_snippets": out.get("code_snippets") if isinstance(out.get("code_snippets"), list) else [],
            "interim_actions": out.get("interim_actions") if isinstance(out.get("interim_actions"), list) else [],
        }
    except Exception as e:
        logging.warning("Fix blueprint suggestions LLM failed: %s", e)
        fallback = []
        for r in failed:
            r_lower = (r or "").lower()
            if "lighthouse" in r_lower and "not found" in r_lower:
                fallback.append({"title": "Install Lighthouse", "code": "npm install -g lighthouse"})
            elif "playwright" in r_lower and "install" in r_lower:
                fallback.append({"title": "Install Playwright browsers", "code": "playwright install"})
            elif "executable" in r_lower and "chromium" in r_lower:
                fallback.append({"title": "Install Playwright browsers", "code": "playwright install"})
        return {
            "plain_language_summary": "Validation failed due to missing or misconfigured tools in the build environment (e.g. Lighthouse or browser drivers). Your template content may be fine. Ask your technical team to install the required tools in the deployment environment; see technical details below.",
            "technical_details": "\n".join(failed[:10]),
            "code_snippets": fallback[:5],
            "interim_actions": ["Re-run validation after the environment is updated.", "You can continue editing the blueprint in the meantime."],
        }


IMAGE_PROMPT_CATEGORIES = {"exterior", "interior", "lifestyle", "people", "neighborhood"}


@router.post("/api/templates/{template_id}/images", response_model=dict)
async def upload_template_image(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    file: UploadFile = File(...),
    section_key: str = Form("general"),
):
    """Upload an image for a template section. section_key can be: exterior, interior, lifestyle, people, neighborhood, or any label. URL stored in meta_json.images."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    key_label = (section_key or "general").strip().lower().replace(" ", "_") or "general"
    content_type = file.content_type or "image/png"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    ext = "png"
    if "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
    elif "webp" in content_type:
        ext = "webp"
    elif "gif" in content_type:
        ext = "gif"
    storage_key = f"templates/{template_id}/images/{key_label}/{uuid.uuid4().hex}.{ext}"
    try:
        backend = get_preview_storage_backend()
        body = await file.read()
        if len(body) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image must be under 10MB")
        backend.save_bytes(storage_key, body, content_type=content_type)
        url = backend.get_url(storage_key, expires_seconds=7 * 24 * 3600)
        if not url:
            url = getattr(backend, "public_base_url", "") and f"{backend.public_base_url.rstrip('/')}/{storage_key}" or ""
    except Exception as e:
        logging.getLogger(__name__).exception("Template image upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Upload failed") from e
    meta = dict(template.meta_json or {})
    images = dict(meta.get("images") or {})
    if key_label not in images:
        images[key_label] = []
    if not isinstance(images[key_label], list):
        images[key_label] = [images[key_label]] if images[key_label] else []
    images[key_label].append(url)
    meta["images"] = images
    template.meta_json = meta
    db.commit()
    db.refresh(template)
    return {"url": url, "section_key": key_label, "stored_in": "meta_json.images"}


@router.post("/api/templates/{template_id}/images/batch", response_model=dict)
async def upload_template_images_batch(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    files: List[UploadFile] = File(...),
    section_key: str = Form("general"),
):
    """Upload multiple images for one category in one request (atomic). Avoids race when adding many per category."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    key_label = (section_key or "general").strip().lower().replace(" ", "_") or "general"
    meta = dict(template.meta_json or {})
    images = dict(meta.get("images") or {})
    if key_label not in images:
        images[key_label] = []
    if not isinstance(images[key_label], list):
        images[key_label] = [images[key_label]] if images[key_label] else []
    added: List[str] = []
    for file in files:
        if not file.filename and not file.content_type:
            continue
        content_type = file.content_type or "image/png"
        if not content_type.startswith("image/"):
            continue
        ext = "png"
        if "jpeg" in content_type or "jpg" in content_type:
            ext = "jpg"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"
        storage_key = f"templates/{template_id}/images/{key_label}/{uuid.uuid4().hex}.{ext}"
        try:
            backend = get_preview_storage_backend()
            body = await file.read()
            if len(body) > 10 * 1024 * 1024:
                continue
            backend.save_bytes(storage_key, body, content_type=content_type)
            url = backend.get_url(storage_key, expires_seconds=7 * 24 * 3600)
            if not url:
                url = getattr(backend, "public_base_url", "") and f"{backend.public_base_url.rstrip('/')}/{storage_key}" or ""
            images[key_label].append(url)
            added.append(url)
        except Exception as e:
            logging.getLogger(__name__).exception("Template image upload in batch failed: %s", e)
    meta["images"] = images
    template.meta_json = meta
    db.commit()
    db.refresh(template)
    return {"section_key": key_label, "added": len(added), "urls": added, "stored_in": "meta_json.images"}


@router.post("/api/templates/{template_id}/publish", response_model=TemplateResponse)
def publish_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    body: Optional[dict] = None,
):
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if (template.preview_status or "") != "ready":
        raise HTTPException(status_code=400, detail="Preview must be ready before publish")
    validation_status = getattr(template, "validation_status", None) or "not_run"
    if validation_status != "passed":
        raise HTTPException(status_code=400, detail="Validation must pass before publish. Run validation first.")
    if (getattr(template, "status", None) or "") != "validated":
        data = body or {}
        if not data.get("admin_override"):
            raise HTTPException(status_code=400, detail="Template must be validated (blueprint) before publish, or use admin_override")
        # Admin override: allow publish even if status != validated
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


@router.post("/api/templates/{template_id}/blueprint/generate")
def generate_template_blueprint(
    template_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    body: Optional[dict] = None,
):
    """Create a blueprint run (queued), enqueue worker, return run_id. Admin/Manager only."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body or {}
    regenerate = data.get("regenerate", False)
    max_iterations = int(data.get("max_iterations", 3))
    if regenerate:
        template.status = "draft"
    run = TemplateBlueprintRun(
        template_id=uuid.UUID(template_id),
        status="queued",
        schema_version="v1",
        model_used=settings.OPENAI_MODEL,
        attempt_number=1,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    template.blueprint_status = "queued"
    template.blueprint_last_run_id = run.id
    template.blueprint_updated_at = datetime.utcnow()
    db.commit()
    from app.services.job_queue import enqueue_job, JOB_TYPE_BLUEPRINT_GENERATE
    enqueue_job(
        JOB_TYPE_BLUEPRINT_GENERATE,
        payload={"run_id": str(run.id), "template_id": template_id, "regenerate": regenerate, "max_iterations": max_iterations},
        idempotency_key=str(run.id),
        db=db,
    )
    return {"run_id": str(run.id), "status": "queued"}


@router.post("/api/templates/{template_id}/generate-blueprint")
def generate_template_blueprint_legacy(
    template_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    body: Optional[dict] = None,
):
    """Legacy: enqueue blueprint generation. Redirects to new run-based flow."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body or {}
    regenerate = data.get("regenerate", False)
    run = TemplateBlueprintRun(
        template_id=uuid.UUID(template_id),
        status="queued",
        schema_version="v1",
        model_used=settings.OPENAI_MODEL,
        attempt_number=1,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    template.blueprint_status = "queued"
    template.blueprint_last_run_id = run.id
    template.blueprint_updated_at = datetime.utcnow()
    db.commit()
    from app.services.job_queue import enqueue_job, JOB_TYPE_BLUEPRINT_GENERATE
    job_id = enqueue_job(
        JOB_TYPE_BLUEPRINT_GENERATE,
        payload={"run_id": str(run.id), "template_id": template_id, "regenerate": regenerate, "max_iterations": (data.get("max_iterations") or 3)},
        idempotency_key=str(run.id),
        db=db,
    )
    return {"job_id": str(job_id), "run_id": str(run.id), "template_id": template_id}


@router.get("/api/templates/{template_id}/blueprint")
def get_template_blueprint(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return blueprint_json only. Admin/Manager only."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    blueprint = getattr(template, "blueprint_json", None)
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Blueprint not generated yet")
    return blueprint


@router.get("/api/templates/{template_id}/blueprint-job")
def get_template_blueprint_job(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return latest blueprint job for template (for polling). Prefer blueprint/status for run-based flow."""
    _require_admin_manager(current_user)
    job = (
        db.query(TemplateBlueprintJob)
        .filter(TemplateBlueprintJob.template_id == template_id)
        .order_by(TemplateBlueprintJob.created_at.desc())
        .first()
    )
    run = (
        db.query(TemplateBlueprintRun)
        .filter(TemplateBlueprintRun.template_id == template_id)
        .order_by(TemplateBlueprintRun.created_at.desc())
        .first()
    )
    if run:
        return {
            "job_id": str(job.id) if job else None,
            "run_id": str(run.id),
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_text": run.error_message,
            "error_code": run.error_code,
            "result_json": {"status": run.status, "blueprint_json": run.blueprint_json} if run.blueprint_json else job.result_json if job else None,
        }
    if not job:
        return {"job_id": None, "run_id": None, "status": None}
    return {
        "job_id": str(job.id),
        "run_id": None,
        "status": job.status,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_text": job.error_text,
        "result_json": job.result_json,
    }


@router.get("/api/templates/{template_id}/blueprint/status")
def get_template_blueprint_status(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return template blueprint status and latest run (for polling). Admin/Manager only."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    run = (
        db.query(TemplateBlueprintRun)
        .filter(TemplateBlueprintRun.template_id == template_id)
        .order_by(TemplateBlueprintRun.created_at.desc())
        .first()
    )
    latest_run = None
    if run:
        latest_run = {
            "run_id": str(run.id),
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error_message": _display_error_message(run.error_code, run.error_message, run.error_details),
            "schema_version": run.schema_version,
            "model_used": run.model_used,
        }
    bp_status = getattr(template, "blueprint_status", None) or ("ready" if template.blueprint_json else "idle")
    return {
        "template_id": template_id,
        "blueprint_status": bp_status,
        "latest_run": latest_run,
        "blueprint_preview": _blueprint_preview_summary(template.blueprint_json) if template.blueprint_json else None,
    }


def _blueprint_preview_summary(bp: Any) -> Optional[dict]:
    if not bp or not isinstance(bp, dict):
        return None
    pages = bp.get("pages") or []
    return {"pages_count": len(pages), "schema_version": bp.get("schema_version")}


@router.get("/api/templates/{template_id}/blueprint/runs")
def list_template_blueprint_runs(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List last 10 blueprint runs for template. Admin/Manager only."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    runs = (
        db.query(TemplateBlueprintRun)
        .filter(TemplateBlueprintRun.template_id == template_id)
        .order_by(TemplateBlueprintRun.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "template_id": template_id,
        "runs": [
            {
                "run_id": str(r.id),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error_message": _display_error_message(r.error_code, r.error_message, r.error_details),
                "model_used": r.model_used,
            }
            for r in runs
        ],
    }


@router.get("/api/blueprint-runs/{run_id}")
def get_blueprint_run_details(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Full run details including error_details and raw_output (admin only). Admin/Manager only."""
    _require_admin_manager(current_user)
    run = db.query(TemplateBlueprintRun).filter(TemplateBlueprintRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": str(run.id),
        "template_id": str(run.template_id),
        "status": run.status,
        "schema_version": run.schema_version,
        "model_used": run.model_used,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_code": run.error_code,
        "error_message": _display_error_message(run.error_code, run.error_message, run.error_details),
        "error_details": run.error_details,
        "raw_output": run.raw_output,
        "blueprint_json": run.blueprint_json,
        "attempt_number": run.attempt_number,
        "correlation_id": run.correlation_id,
    }


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


# ---------- Evolution proposals (Prompt 9) ----------
from datetime import timedelta
from app.agents.templates.evolution_agent import propose_template_improvements


@router.get("/api/templates/{template_id}/evolution-proposals")
def list_evolution_proposals(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List evolution proposals for a template (Admin/Manager)."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    proposals = (
        db.query(TemplateEvolutionProposal)
        .filter(TemplateEvolutionProposal.template_id == template_id)
        .order_by(TemplateEvolutionProposal.created_at.desc())
        .all()
    )
    return {
        "template_id": template_id,
        "proposals": [
            {
                "id": str(p.id),
                "proposal_json": p.proposal_json,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "rejection_reason": p.rejection_reason,
            }
            for p in proposals
        ],
    }


@router.post("/api/templates/{template_id}/propose-evolution")
def create_evolution_proposal(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new evolution proposal (rate limit: 1 per template per week). Admin/Manager."""
    _require_admin_manager(current_user)
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    from datetime import datetime
    week_ago = datetime.utcnow() - timedelta(weeks=1)
    recent = (
        db.query(TemplateEvolutionProposal)
        .filter(
            TemplateEvolutionProposal.template_id == template_id,
            TemplateEvolutionProposal.created_at >= week_ago,
        )
        .first()
    )
    if recent:
        raise HTTPException(
            status_code=429,
            detail="Rate limit: at most one evolution proposal per template per week",
        )
    metrics = getattr(template, "performance_metrics_json", None) or {}
    recent_feedback = []
    for s in db.query(ClientSentiment).filter(
        (ClientSentiment.template_registry_id == template.id) | (ClientSentiment.template_id == str(template.id)),
    ).order_by(ClientSentiment.submitted_at.desc()).limit(50):
        recent_feedback.append({
            "tags_json": getattr(s, "tags_json", None) or [],
            "rating": s.rating,
            "overall_score": getattr(s, "overall_score", None),
        })
    proposal_json = propose_template_improvements(
        str(template.id),
        getattr(template, "version", 1),
        metrics,
        recent_feedback,
    )
    prop = TemplateEvolutionProposal(
        template_id=template.id,
        proposal_json=proposal_json,
        status="pending",
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return {"id": str(prop.id), "proposal_json": proposal_json, "status": "pending"}


@router.post("/api/templates/{template_id}/evolve")
def evolve_template(
    template_id: str,
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve or reject an evolution proposal. On approve: clone template as new version, apply changes, enqueue preview+validation. Admin/Manager."""
    _require_admin_manager(current_user)
    proposal_id = body.get("proposal_id")
    approve = body.get("approve")
    rejection_reason = body.get("rejection_reason")
    if not proposal_id:
        raise HTTPException(status_code=400, detail="proposal_id required")
    template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    proposal = (
        db.query(TemplateEvolutionProposal)
        .filter(
            TemplateEvolutionProposal.id == proposal_id,
            TemplateEvolutionProposal.template_id == template_id,
            TemplateEvolutionProposal.status == "pending",
        )
        .first()
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or already reviewed")
    from datetime import datetime
    now = datetime.utcnow()
    proposal.reviewed_at = now
    proposal.reviewed_by_user_id = current_user.id
    if approve:
        # Clone as new version
        new_version = getattr(template, "version", 1) + 1
        new_id = uuid.uuid4()
        blueprint = copy.deepcopy(template.blueprint_json or {})
        # Attach evolution changes to meta for refinement
        if not isinstance(blueprint.get("meta"), dict):
            blueprint["meta"] = {}
        blueprint["meta"]["_evolution_applied"] = proposal.proposal_json.get("suggested_blueprint_changes") or []
        new_template = TemplateRegistry(
            id=new_id,
            slug=template.slug,
            name=template.name,
            repo_url=template.repo_url,
            default_branch=template.default_branch,
            meta_json=copy.deepcopy(template.meta_json or {}),
            description=template.description,
            features_json=copy.deepcopy(template.features_json or []),
            preview_url=None,
            source_type=template.source_type,
            intent=template.intent,
            preview_status="not_generated",
            preview_last_generated_at=None,
            preview_error=None,
            preview_thumbnail_url=None,
            is_active=True,
            is_published=False,
            category=template.category,
            style=template.style,
            feature_tags_json=copy.deepcopy(getattr(template, "feature_tags_json", None) or []),
            status="draft",
            is_default=False,
            is_recommended=False,
            version=new_version,
            parent_template_id=template.id,
            blueprint_json=blueprint,
            blueprint_schema_version=getattr(template, "blueprint_schema_version", 1),
        )
        db.add(new_template)
        proposal.status = "approved"
        db.commit()
        db.refresh(new_template)
        # Optional: mark old as deprecated
        template.is_deprecated = True
        db.commit()
        # Enqueue preview generation (blueprint already set)
        try:
            background_tasks.add_task(_run_template_preview_pipeline, str(new_template.id))
        except Exception:
            pass
        return {"message": "Evolution approved", "new_template_id": str(new_id), "new_version": new_version}
    else:
        proposal.status = "rejected"
        proposal.rejection_reason = rejection_reason or "Rejected by reviewer"
        db.commit()
        return {"message": "Proposal rejected"}
