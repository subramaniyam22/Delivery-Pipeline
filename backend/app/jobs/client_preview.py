"""
Client preview pipeline: render from template blueprint + delivery contract,
upload to storage, update project client_preview_* fields.
Throttled; concurrency limited; never crashes worker loop.
Prefers blueprint path when template has blueprint (multi-page, client images); ZIP path injects client images into built HTML/CSS.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Project, ProjectContract, PipelineEvent, TemplateRegistry
from app.services.contract_service import get_contract, create_or_update_contract
from app.services.client_preview_renderer import render_client_preview_assets
from app.services.storage import (
    PREVIEW_BUNDLE_MAX_BYTES,
    upload_preview_bundle,
    upload_thumbnail,
)
from app.services.thumbnail import generate_thumbnail

logger = logging.getLogger(__name__)

# Map common built-site image stems to contract brand image list (use first N for categories)
_STEM_TO_CATEGORY = {"hero": "exterior", "careers": "people", "services": "lifestyle", "office": "interior"}


def _inject_client_images_into_dist(dist_path: str, contract: Dict[str, Any]) -> None:
    """Replace assets/img/* in HTML/CSS under dist_path with client-uploaded image URLs from contract. Modifies files in place."""
    ob = (contract or {}).get("onboarding") or {}
    brand = ob.get("brand") or {}
    images_json = brand.get("images") or []
    if not isinstance(images_json, list) or not images_json:
        return
    urls: List[str] = []
    for img in images_json[:12]:
        if isinstance(img, dict):
            u = img.get("url") or img.get("path")
            if u:
                urls.append(str(u))
        elif isinstance(img, str):
            urls.append(img)
    if not urls:
        return
    by_category: Dict[str, List[str]] = {cat: urls for cat in ("exterior", "interior", "lifestyle", "people", "neighborhood")}
    pattern = re.compile(
        r'(src=|url\()(\s*["\']?)(assets/img/[^"\')\s]+)(["\']?)',
        re.IGNORECASE,
    )

    def replacer(match: re.Match) -> str:
        prefix, quote1, path, quote2 = match.groups()
        stem = os.path.splitext(os.path.basename(path))[0].lower().replace(" ", "_")
        url = None
        if stem in by_category and by_category[stem]:
            url = by_category[stem][0]
        else:
            fallback = _STEM_TO_CATEGORY.get(stem)
            if fallback and fallback in by_category and by_category[fallback]:
                url = by_category[fallback][0]
        if url:
            return f"{prefix}{quote1}{url}{quote2}"
        return match.group(0)

    for root, _dirs, files in os.walk(dist_path):
        for name in files:
            if not (name.endswith(".html") or name.endswith(".css")):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                new_content = pattern.sub(replacer, content)
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
            except Exception as e:
                logger.warning("Inject client images into %s: %s", path, e)


CLIENT_PREVIEW_RATE_LIMIT_MINUTES = 5
CLIENT_PREVIEW_CONCURRENCY = int(os.getenv("CLIENT_PREVIEW_CONCURRENCY", "2"))
CLIENT_PREVIEW_TIMEOUT_SECONDS = int(os.getenv("CLIENT_PREVIEW_TIMEOUT_SECONDS", "120"))
_client_preview_semaphore = threading.Semaphore(CLIENT_PREVIEW_CONCURRENCY)


def run_client_preview_pipeline(
    project_id: UUID,
    force: bool = False,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Load project + contract + template blueprint; compute hash; if unchanged and not force, skip.
    Render client preview assets, upload bundle + thumbnail to projects/{id}/preview/v{version}/,
    persist URLs and status; emit CLIENT_PREVIEW_READY. On error set status=failed and store error.
    """
    if not _client_preview_semaphore.acquire(blocking=True, timeout=CLIENT_PREVIEW_TIMEOUT_SECONDS):
        return {"status": "failed", "error": "Client preview job concurrency timeout"}
    session = db or SessionLocal()
    close = db is None
    try:
        project = session.query(Project).filter(Project.id == project_id).first()
        if not project:
            _client_preview_semaphore.release()
            return {"status": "error", "error": "Project not found"}
        contract = get_contract(session, project_id)
        if not contract:
            try:
                create_or_update_contract(session, project_id, source="system:client_preview")
                contract = get_contract(session, project_id)
            except Exception as e:
                _client_preview_semaphore.release()
                project.client_preview_status = "failed"
                project.client_preview_error = f"Contract build failed: {e}"
                session.commit()
                return {"status": "failed", "error": project.client_preview_error}
        if not contract:
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "No delivery contract"
            session.commit()
            return {"status": "failed", "error": "No delivery contract"}
        ob = contract.get("onboarding") or {}
        if (ob.get("status") or "") != "submitted":
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "Onboarding not submitted"
            session.commit()
            return {"status": "failed", "error": "Onboarding not submitted"}
        template_id = (contract.get("template") or {}).get("selected_template_id") or ob.get("theme_preference")
        if not template_id:
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "No template selected"
            session.commit()
            return {"status": "failed", "error": "No template selected"}
        try:
            tid = UUID(str(template_id)) if template_id else None
        except (ValueError, TypeError):
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "Invalid template id"
            session.commit()
            return {"status": "failed", "error": "Invalid template id"}
        template = session.query(TemplateRegistry).filter(TemplateRegistry.id == tid).first()
        if not template:
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "Template not found"
            session.commit()
            return {"status": "failed", "error": "Template not found"}

        # Prefer blueprint path when template has blueprint: multi-page (index.html + slug.html) + client images
        blueprint = getattr(template, "blueprint_json", None)
        if blueprint and isinstance(blueprint, dict):
            # Blueprint path: multi-page, client images from contract
            blueprint_hash = getattr(template, "blueprint_hash", None) or hashlib.sha256(str(blueprint).encode()).hexdigest()[:16]
            pc = session.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
            contract_version = (pc.version or 1) if pc else 1
            new_hash = hashlib.sha256(f"{blueprint_hash}:{contract_version}".encode()).hexdigest()
            if not force and getattr(project, "client_preview_hash", None) == new_hash and getattr(project, "client_preview_status", None) == "ready":
                _client_preview_semaphore.release()
                return {"status": "skipped", "message": "Preview already up to date"}
            last_at = getattr(project, "client_preview_last_generated_at", None)
            if not force and last_at:
                try:
                    delta_sec = (datetime.utcnow() - last_at).total_seconds()
                    if delta_sec < CLIENT_PREVIEW_RATE_LIMIT_MINUTES * 60:
                        _client_preview_semaphore.release()
                        return {"status": "skipped", "message": "Rate limited"}
                except Exception:
                    pass
            project.client_preview_status = "generating"
            project.client_preview_error = None
            project.client_preview_started_at = datetime.utcnow()
            session.commit()
            try:
                assets = render_client_preview_assets(blueprint, contract)
            except Exception as e:
                logger.exception("Client preview render failed: %s", e)
                project.client_preview_status = "failed"
                project.client_preview_error = str(e)
                project.client_preview_started_at = None
                session.commit()
                _client_preview_semaphore.release()
                return {"status": "failed", "error": str(e)}
            total_size = sum(
                len(c.encode("utf-8") if isinstance(c, str) else c)
                for c in assets.values()
            )
            if total_size > PREVIEW_BUNDLE_MAX_BYTES:
                project.client_preview_status = "failed"
                project.client_preview_error = f"Bundle size {total_size} exceeds max {PREVIEW_BUNDLE_MAX_BYTES}"
                project.client_preview_started_at = None
                session.commit()
                _client_preview_semaphore.release()
                return {"status": "failed", "error": project.client_preview_error}
            prefix = f"projects/{project_id}/preview/v{contract_version}"
            try:
                preview_url = upload_preview_bundle(prefix, assets)
            except Exception as e:
                logger.exception("Client preview upload failed: %s", e)
                project.client_preview_status = "failed"
                project.client_preview_error = f"Upload failed: {e}"
                project.client_preview_started_at = None
                session.commit()
                _client_preview_semaphore.release()
                return {"status": "failed", "error": str(e)}
            thumbnail_url = None
            try:
                thumb_bytes = generate_thumbnail(
                    blueprint_json=blueprint,
                    preview_url=preview_url,
                    title=((contract.get("onboarding") or {}).get("primary_contact") or {}).get("company_name") or project.client_name or "Client Preview",
                    subtitle=project.title or "",
                )
                if thumb_bytes:
                    thumbnail_url = upload_thumbnail(prefix, thumb_bytes)
            except Exception as e:
                logger.warning("Client preview thumbnail failed: %s", e)
            project.client_preview_url = preview_url
            project.client_preview_thumbnail_url = thumbnail_url
            project.client_preview_status = "ready"
            project.client_preview_error = None
            project.client_preview_started_at = None
            project.client_preview_last_generated_at = datetime.utcnow()
            project.client_preview_hash = new_hash
            session.add(PipelineEvent(project_id=project_id, stage_key="3_build", event_type="CLIENT_PREVIEW_READY", details_json={"preview_url": preview_url}))
            session.commit()
            _client_preview_semaphore.release()
            return {"status": "ready", "preview_url": preview_url, "thumbnail_url": thumbnail_url}

        # S3 ZIP path (no blueprint): build from template zip, inject client images, upload
        build_source = getattr(template, "build_source_type", None)
        source_ref = getattr(template, "build_source_ref", None)
        if build_source in ("s3_zip", "s3") and source_ref:
            from app.services.storage import get_s3_assets_backend, upload_preview_site, get_preview_public_url
            from app.runners.site_builder import clone_template, build_site, _inject_client_contract
            import tempfile
            pc = session.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
            contract_version = (pc.version or 1) if pc else 1
            new_hash = hashlib.sha256(f"{source_ref}:{contract_version}".encode()).hexdigest()[:16]
            if not force and getattr(project, "client_preview_hash", None) == new_hash and getattr(project, "client_preview_status", None) == "ready":
                _client_preview_semaphore.release()
                return {"status": "skipped", "message": "Preview already up to date"}
            if not get_s3_assets_backend():
                _client_preview_semaphore.release()
                project.client_preview_status = "failed"
                project.client_preview_error = "S3 not configured for template zip preview"
                project.client_preview_started_at = None
                session.commit()
                return {"status": "failed", "error": project.client_preview_error}
            project.client_preview_status = "generating"
            project.client_preview_error = None
            project.client_preview_started_at = datetime.utcnow()
            session.commit()
            try:
                with tempfile.TemporaryDirectory() as workdir:
                    repo_dir = clone_template(template, workdir)
                    _inject_client_contract(repo_dir, contract)
                    dist_path, _ = build_site(repo_dir)
                    _inject_client_images_into_dist(dist_path, contract)
                    run_id = f"preview-{new_hash}"
                    upload_preview_site(str(project_id), run_id, dist_path)
                    preview_url = get_preview_public_url(str(project_id), run_id, "")
                project.client_preview_url = preview_url
                project.client_preview_thumbnail_url = None
                project.client_preview_status = "ready"
                project.client_preview_error = None
                project.client_preview_started_at = None
                project.client_preview_last_generated_at = datetime.utcnow()
                project.client_preview_hash = new_hash
                session.add(PipelineEvent(project_id=project_id, stage_key="3_build", event_type="CLIENT_PREVIEW_READY", details_json={"preview_url": preview_url}))
                session.commit()
                _client_preview_semaphore.release()
                return {"status": "ready", "preview_url": preview_url, "thumbnail_url": None}
            except Exception as e:
                logger.exception("Client preview (s3_zip) failed: %s", e)
                project.client_preview_status = "failed"
                project.client_preview_error = str(e)
                project.client_preview_started_at = None
                session.commit()
                _client_preview_semaphore.release()
                return {"status": "failed", "error": str(e)}

        _client_preview_semaphore.release()
        project.client_preview_status = "failed"
        project.client_preview_error = "Template has no blueprint and no ZIP source. Generate blueprint or use a template with upload."
        project.client_preview_started_at = None
        session.commit()
        return {"status": "failed", "error": project.client_preview_error}
    except Exception as e:
        logger.exception("Client preview pipeline failed: %s", e)
        try:
            _client_preview_semaphore.release()
        except Exception:
            pass
        if session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.client_preview_status = "failed"
                    project.client_preview_error = str(e)
                    project.client_preview_started_at = None
                    session.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}
    finally:
        if close and session:
            session.close()
