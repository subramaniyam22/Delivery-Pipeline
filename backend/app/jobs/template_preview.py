"""
Template preview pipeline: render from blueprint -> upload bundle + thumbnail -> update TemplateRegistry.
Runs in background task; uses preview_renderer, storage, thumbnail services.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import TemplateRegistry
from app.services.demo_preview_data import get_demo_dataset_by_key, generate_demo_preview_dataset
from app.services.preview_renderer import render_preview_assets_single_page
from app.services.storage import (
    PREVIEW_BUNDLE_MAX_BYTES,
    upload_preview_bundle,
    upload_thumbnail,
    delete_preview_bundle,
)
from app.services.thumbnail import generate_thumbnail

logger = logging.getLogger(__name__)

PREVIEW_JOBS_CONCURRENCY = int(os.getenv("PREVIEW_JOBS_CONCURRENCY", "2"))
PREVIEW_JOB_TIMEOUT_SECONDS = int(os.getenv("PREVIEW_JOB_TIMEOUT_SECONDS", "120"))
_preview_semaphore = threading.Semaphore(PREVIEW_JOBS_CONCURRENCY)


def _template_prefix(template: TemplateRegistry) -> str:
    slug = (template.slug or "template").replace(" ", "-").lower()
    version = getattr(template, "version", None) or 1
    return f"templates/{slug}/v{version}"


def run_template_preview_pipeline(
    template_id: UUID,
    db: Session | None = None,
    skip_semaphore: bool = False,
) -> Dict[str, Any]:
    """
    Load template + blueprint, render assets, upload to storage, generate thumbnail, update template.
    On exception: set preview_status=failed, preview_error=str(e).
    When skip_semaphore=True (e.g. sync request), do not wait on global semaphore so the request can complete without blocking on other jobs.
    """
    acquired = False
    if not skip_semaphore:
        if not _preview_semaphore.acquire(blocking=True, timeout=PREVIEW_JOB_TIMEOUT_SECONDS):
            return {"status": "failed", "error": "Preview job concurrency timeout"}
        acquired = True
    session = db or SessionLocal()
    close = db is None
    try:
        template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            if acquired:
                _preview_semaphore.release()
            return {"status": "failed", "error": "Template not found"}
        blueprint = getattr(template, "blueprint_json", None)
        if not blueprint or not isinstance(blueprint, dict):
            template.preview_status = "failed"
            template.preview_error = "No blueprint. Generate blueprint first."
            session.commit()
            if acquired:
                _preview_semaphore.release()
            return {"status": "failed", "error": template.preview_error}
        demo_key = (template.default_config_json or {}).get("demo_dataset_key") if getattr(template, "default_config_json", None) else None
        demo_dataset = (get_demo_dataset_by_key(demo_key) if demo_key else None) or generate_demo_preview_dataset()
        template_images = None
        meta = getattr(template, "meta_json", None) or {}
        if isinstance(meta.get("images"), dict):
            template_images = {k: v if isinstance(v, list) else [v] for k, v in meta["images"].items() if v}
        # Single-page preview so one S3 URL works; nav links use #section-X and avoid AccessDenied on other .html keys
        assets = render_preview_assets_single_page(blueprint, demo_dataset, template_images)
        total_size = sum(
            len(c.encode("utf-8") if isinstance(c, str) else c)
            for c in assets.values()
        )
        if total_size > PREVIEW_BUNDLE_MAX_BYTES:
            template.preview_status = "failed"
            template.preview_error = f"Bundle size {total_size} exceeds max {PREVIEW_BUNDLE_MAX_BYTES}"
            session.commit()
            if acquired:
                _preview_semaphore.release()
            return {"status": "failed", "error": template.preview_error}
        prefix = _template_prefix(template)
        try:
            delete_preview_bundle(prefix)
        except Exception:
            pass
        try:
            preview_url = upload_preview_bundle(prefix, assets)
        except Exception as e:
            logger.exception("Upload preview bundle failed: %s", e)
            template.preview_status = "failed"
            template.preview_error = f"Upload failed: {e}"
            session.commit()
            if acquired:
                _preview_semaphore.release()
            return {"status": "failed", "error": str(e)}
        thumbnail_bytes = None
        try:
            thumbnail_bytes = generate_thumbnail(
                blueprint_json=blueprint,
                preview_url=preview_url,
                title=(blueprint.get("meta") or {}).get("name") or template.name,
                subtitle=(blueprint.get("meta") or {}).get("category") or "",
            )
        except Exception as e:
            logger.warning("Thumbnail generation failed (continuing): %s", e)
        thumbnail_url = None
        if thumbnail_bytes:
            try:
                thumbnail_url = upload_thumbnail(prefix, thumbnail_bytes)
            except Exception as e:
                logger.warning("Thumbnail upload failed: %s", e)
        template.preview_url = preview_url
        template.preview_thumbnail_url = thumbnail_url
        template.preview_status = "ready"
        template.preview_error = None
        template.preview_last_generated_at = datetime.utcnow()
        template.validation_status = "not_run"
        template.validation_hash = None
        session.commit()
        if acquired:
            _preview_semaphore.release()
        return {"status": "ready", "preview_url": preview_url, "thumbnail_url": thumbnail_url}
    except Exception as e:
        logger.exception("Preview pipeline failed: %s", e)
        if acquired:
            try:
                _preview_semaphore.release()
            except Exception:
                pass
        if session:
            try:
                template = session.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
                if template:
                    template.preview_status = "failed"
                    template.preview_error = str(e)
                    template.preview_last_generated_at = datetime.utcnow()
                    session.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}
    finally:
        if close and session:
            session.close()
