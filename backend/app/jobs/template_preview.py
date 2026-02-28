"""
Template preview pipeline: render from blueprint -> upload bundle + thumbnail -> update TemplateRegistry.
When template has build_source_type=s3_zip, build from ZIP and upload dist as preview (blueprint not required).
Runs in background task; uses preview_renderer, storage, thumbnail, site_builder.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import TemplateRegistry
from app.services.demo_preview_data import get_demo_dataset_by_key, generate_demo_preview_dataset
from app.services.preview_renderer import render_preview_assets
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
    """Unique prefix per template so previews don't overwrite each other (slug+version can collide)."""
    return f"templates/{template.id}"


# Map common ZIP image filenames (stem) to template image category keys (user may upload by category name).
# Includes internal-page names (amenities, gallery, feature, etc.) so Blueprint images load on every page.
_STEM_TO_CATEGORY_FALLBACK: Dict[str, str] = {
    "hero": "exterior",
    "careers": "people",
    "services": "lifestyle",
    "office": "interior",
    "placeholder": "exterior",
    "hero_placeholder": "exterior",
    "hero-placeholder": "exterior",
    "amenities": "lifestyle",
    "gallery": "exterior",
    "feature": "exterior",
    "about": "lifestyle",
    "contact": "lifestyle",
    "team": "people",
    "community": "exterior",
    "floorplan": "interior",
    "logo": "exterior",
}

# Match src="..." or url(...) pointing at relative or root-relative image paths (so we can replace with Blueprint-uploaded URLs).
# Matches /images/, images/, assets/img/, ./images/, etc. Excludes http(s): URLs.
_IMAGE_PATH_PATTERN = re.compile(
    r'(src=|url\()(\s*["\']?)((?!https?:)(?:\/)?(?:\.\/)?(?:assets\/)?(?:images?\/)?[^"\')\s]*\.(?:jpe?g|png|gif|webp|svg))(\s*["\']?)',
    re.IGNORECASE,
)
# Match data:image/... placeholders (common in Git-built templates: inline SVG/PNG placeholders).
_DATA_URI_IMAGE_PATTERN = re.compile(
    r'(src=|url\()(\s*["\']?)data:image/[^"\')\s]+(["\']?)',
    re.IGNORECASE,
)


def _first_blueprint_image_url(by_category: Dict[str, list]) -> Optional[str]:
    """Return first Blueprint image URL; prefer hero/exterior for main/hero slots."""
    for key in ("hero", "exterior", "interior", "lifestyle", "people", "neighborhood"):
        if key in by_category and by_category[key]:
            return by_category[key][0]
    for urls in by_category.values():
        if urls:
            return urls[0]
    return None


def _inject_template_images_into_zip_assets(
    assets: Dict[str, Any],
    template_images: Optional[Dict[str, list]] = None,
) -> None:
    """
    Replace local image references and data-URI placeholders with Blueprint-uploaded URLs (meta_json.images).
    When a category has multiple images, cycle through them (gallery-1 -> first, gallery-2 -> second, etc.)
    so inner pages show different images instead of the same one repeated.
    """
    if not template_images:
        return
    by_category: Dict[str, list] = {}
    for k, v in template_images.items():
        if not v:
            continue
        key = (k or "").strip().lower().replace(" ", "_")
        if key:
            by_category[key] = v if isinstance(v, list) else [v]

    first_url = _first_blueprint_image_url(by_category)
    # Per-category index so we cycle through multiple uploads (e.g. Gallery 1–6 get 6 different images)
    category_index: Dict[str, int] = {}

    def _pick_url(category_key: str, index_1based: Optional[int] = None) -> Optional[str]:
        urls = by_category.get(category_key)
        if not urls:
            return None
        if index_1based is not None and index_1based >= 1:
            return urls[(index_1based - 1) % len(urls)]
        idx = category_index.get(category_key, 0)
        category_index[category_key] = idx + 1
        return urls[idx % len(urls)]

    def _category_and_index_for_stem(stem: str) -> tuple[Optional[str], Optional[int]]:
        """Return (category_key, index_1based) for a filename stem. Handles hashed stems like gallery_1_a1b2c3d4."""
        index_from_stem = None
        mo = re.search(r"_(\d+)", stem)
        if mo:
            index_from_stem = int(mo.group(1))
        if stem in by_category and by_category[stem]:
            return stem, index_from_stem
        fallback = _STEM_TO_CATEGORY_FALLBACK.get(stem)
        if fallback and fallback in by_category and by_category[fallback]:
            return fallback, index_from_stem
        base_stem = re.sub(r"_\d+$", "", stem)
        if base_stem and base_stem != stem:
            if base_stem in by_category and by_category[base_stem]:
                return base_stem, index_from_stem
            fallback = _STEM_TO_CATEGORY_FALLBACK.get(base_stem)
            if fallback and fallback in by_category and by_category[fallback]:
                return fallback, index_from_stem
        # Git-built bundles use hashed names: gallery-1-abc123 -> stem gallery_1_abc123; match by prefix
        for known in ("gallery", "amenities", "feature", "hero", "exterior", "interior", "lifestyle", "people", "about", "contact", "team", "community", "floorplan", "logo"):
            if stem.startswith(known + "_") or stem == known:
                if known in by_category and by_category[known]:
                    return known, index_from_stem
                fb = _STEM_TO_CATEGORY_FALLBACK.get(known)
                if fb and fb in by_category and by_category[fb]:
                    return fb, index_from_stem
        return None, None

    def path_replacer(match: re.Match) -> str:
        prefix, quote1, path, quote2 = match.groups()
        stem = os.path.splitext(os.path.basename(path))[0].lower().replace(" ", "_").replace("-", "_")
        category_key, index_from_stem = _category_and_index_for_stem(stem)
        url = _pick_url(category_key, index_from_stem) if category_key else None
        if url is None and first_url:
            url = first_url
        if url and isinstance(url, str):
            return f"{prefix}{quote1}{url}{quote2}"
        return match.group(0)

    def data_uri_replacer(match: re.Match) -> str:
        prefix, quote1, _data_uri, quote2 = match.groups()
        if first_url:
            return f"{prefix}{quote1}{first_url}{quote2}"
        return match.group(0)

    for rel, content in list(assets.items()):
        if not isinstance(content, str):
            continue
        if not (rel.endswith(".html") or rel.endswith(".css") or rel.endswith(".js")):
            continue
        new_content = _IMAGE_PATH_PATTERN.sub(path_replacer, content)
        new_content = _DATA_URI_IMAGE_PATTERN.sub(data_uri_replacer, new_content)
        if new_content != content:
            assets[rel] = new_content


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

        build_source = getattr(template, "build_source_type", None)
        source_ref = getattr(template, "build_source_ref", None)
        source_type_attr = getattr(template, "source_type", None)
        repo_url = getattr(template, "repo_url", None)
        # Prefer Git when template has repo_url and is a Git template (avoids S3 NoSuchKey for GitHub templates with stale s3_zip ref)
        use_git_path = (build_source == "git" or (source_type_attr == "git" and repo_url)) and repo_url

        if use_git_path:
            # Preview from Git: clone repo, build site, upload dist as preview (no blueprint required)
            try:
                from app.runners.site_builder import clone_template, build_site, resolve_template_root
                with tempfile.TemporaryDirectory() as workdir:
                    repo_dir = clone_template(template, workdir)
                    template_root = resolve_template_root(repo_dir, template)
                    dist_path, _ = build_site(template_root)
                    dist_index = os.path.join(dist_path, "index.html")
                    if not os.path.isfile(dist_index):
                        raise RuntimeError("Template build did not produce dist/index.html")
                    assets = {}
                    for root, _dirs, files in os.walk(dist_path):
                        for f in files:
                            if ".." in f or f.startswith("."):
                                continue
                            abs_path = os.path.join(root, f)
                            rel = os.path.relpath(abs_path, dist_path).replace("\\", "/")
                            with open(abs_path, "rb") as fp:
                                content = fp.read()
                            if rel.endswith((".html", ".css", ".js", ".json", ".txt", ".xml", ".ico", ".svg")):
                                try:
                                    assets[rel] = content.decode("utf-8", errors="replace")
                                except Exception:
                                    assets[rel] = content
                            else:
                                assets[rel] = content
                    meta = getattr(template, "meta_json", None) or {}
                    if isinstance(meta.get("images"), dict):
                        zip_template_images = {k: v if isinstance(v, list) else [v] for k, v in meta["images"].items() if v}
                        _inject_template_images_into_zip_assets(assets, zip_template_images)
                    total_size = sum(len(c) if isinstance(c, bytes) else len(c.encode("utf-8")) for c in assets.values())
                    if total_size > PREVIEW_BUNDLE_MAX_BYTES:
                        template.preview_status = "failed"
                        template.preview_error = f"Built site size {total_size} exceeds max {PREVIEW_BUNDLE_MAX_BYTES}"
                        session.commit()
                        if acquired:
                            _preview_semaphore.release()
                        return {"status": "failed", "error": template.preview_error}
                    prefix = _template_prefix(template)
                    try:
                        delete_preview_bundle(prefix)
                    except Exception:
                        pass
                    preview_url = upload_preview_bundle(prefix, assets)
                thumbnail_bytes = None
                try:
                    thumbnail_bytes = generate_thumbnail(
                        blueprint_json={"meta": {"name": template.name, "category": getattr(template, "category", "") or ""}},
                        preview_url=preview_url,
                        title=template.name or "Preview",
                        subtitle="",
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
                logger.exception("Preview from Git failed: %s", e)
                template.preview_status = "failed"
                template.preview_error = str(e)
                template.preview_last_generated_at = datetime.utcnow()
                session.commit()
                if acquired:
                    _preview_semaphore.release()
                return {"status": "failed", "error": str(e)}

        elif build_source in ("s3_zip", "s3") and source_ref:
            # Preview from ZIP: build the template from its ZIP and upload dist as preview (no blueprint required)
            try:
                from app.runners.site_builder import clone_template, build_site, resolve_template_root
                with tempfile.TemporaryDirectory() as workdir:
                    repo_dir = clone_template(template, workdir)
                    template_root = resolve_template_root(repo_dir, template)
                    dist_path, _ = build_site(template_root)
                    dist_index = os.path.join(dist_path, "index.html")
                    if not os.path.isfile(dist_index):
                        raise RuntimeError("Template build did not produce dist/index.html")
                    assets = {}
                    for root, _dirs, files in os.walk(dist_path):
                        for f in files:
                            if ".." in f or f.startswith("."):
                                continue
                            abs_path = os.path.join(root, f)
                            rel = os.path.relpath(abs_path, dist_path).replace("\\", "/")
                            with open(abs_path, "rb") as fp:
                                content = fp.read()
                            if rel.endswith((".html", ".css", ".js", ".json", ".txt", ".xml", ".ico", ".svg")):
                                try:
                                    assets[rel] = content.decode("utf-8", errors="replace")
                                except Exception:
                                    assets[rel] = content
                            else:
                                assets[rel] = content
                    meta = getattr(template, "meta_json", None) or {}
                    if isinstance(meta.get("images"), dict):
                        zip_template_images = {k: v if isinstance(v, list) else [v] for k, v in meta["images"].items() if v}
                        _inject_template_images_into_zip_assets(assets, zip_template_images)
                    total_size = sum(len(c) if isinstance(c, bytes) else len(c.encode("utf-8")) for c in assets.values())
                    if total_size > PREVIEW_BUNDLE_MAX_BYTES:
                        template.preview_status = "failed"
                        template.preview_error = f"Built site size {total_size} exceeds max {PREVIEW_BUNDLE_MAX_BYTES}"
                        session.commit()
                        if acquired:
                            _preview_semaphore.release()
                        return {"status": "failed", "error": template.preview_error}
                    prefix = _template_prefix(template)
                    try:
                        delete_preview_bundle(prefix)
                    except Exception:
                        pass
                    preview_url = upload_preview_bundle(prefix, assets)
                thumbnail_bytes = None
                try:
                    thumbnail_bytes = generate_thumbnail(
                        blueprint_json={"meta": {"name": template.name, "category": getattr(template, "category", "") or ""}},
                        preview_url=preview_url,
                        title=template.name or "Preview",
                        subtitle="",
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
                logger.exception("Preview from ZIP failed: %s", e)
                template.preview_status = "failed"
                template.preview_error = str(e)
                template.preview_last_generated_at = datetime.utcnow()
                session.commit()
                if acquired:
                    _preview_semaphore.release()
                return {"status": "failed", "error": str(e)}

        blueprint = getattr(template, "blueprint_json", None)
        if not blueprint or not isinstance(blueprint, dict):
            template.preview_status = "failed"
            template.preview_error = "No blueprint. Generate blueprint first (or use a template created from ZIP)."
            session.commit()
            if acquired:
                _preview_semaphore.release()
            return {"status": "failed", "error": template.preview_error}
        demo_key = (template.default_config_json or {}).get("demo_dataset_key") if getattr(template, "default_config_json", None) else None
        demo_dataset = (get_demo_dataset_by_key(demo_key) if demo_key else None) or generate_demo_preview_dataset()
        template_images = None
        meta = getattr(template, "meta_json", None) or {}
        if isinstance(meta.get("images"), dict):
            # Normalize keys to lowercase so section image_prompt_category (e.g. exterior) always matches
            raw = {k: v if isinstance(v, list) else [v] for k, v in meta["images"].items() if v}
            template_images = {}
            for k, v in raw.items():
                key = (k or "").strip().lower().replace(" ", "_")
                if key:
                    template_images[key] = v
        # Multi-page preview: index.html + one .html per linked page (nav/footer); served via API proxy so all links work
        assets = render_preview_assets(blueprint, demo_dataset, template_images)
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
