"""
Client preview pipeline: render from template blueprint + delivery contract,
upload to storage, update project client_preview_* fields.
Throttled; concurrency limited; never crashes worker loop.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional
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
        blueprint = getattr(template, "blueprint_json", None)
        if not blueprint or not isinstance(blueprint, dict):
            _client_preview_semaphore.release()
            project.client_preview_status = "failed"
            project.client_preview_error = "Template has no blueprint"
            session.commit()
            return {"status": "failed", "error": "Template has no blueprint"}
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
        session.commit()
        try:
            assets = render_client_preview_assets(blueprint, contract)
        except Exception as e:
            logger.exception("Client preview render failed: %s", e)
            project.client_preview_status = "failed"
            project.client_preview_error = str(e)
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
        project.client_preview_last_generated_at = datetime.utcnow()
        project.client_preview_hash = new_hash
        session.add(PipelineEvent(project_id=project_id, stage_key="3_build", event_type="CLIENT_PREVIEW_READY", details_json={"preview_url": preview_url}))
        session.commit()
        _client_preview_semaphore.release()
        return {"status": "ready", "preview_url": preview_url, "thumbnail_url": thumbnail_url}
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
                    session.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}
    finally:
        if close and session:
            session.close()
