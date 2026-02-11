"""
Common seeding utilities: DB session, slugify, upsert_template.
"""
import os
import re
import sys
from contextlib import contextmanager
from typing import Any, Dict, Literal, Optional

# Run from backend directory so app is importable
if __name__ == "__main__" or (sys.path and "scripts" in sys.path[0]):
    _backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _backend not in sys.path:
        sys.path.insert(0, _backend)

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import TemplateRegistry


def slugify(name: str) -> str:
    """Convert name to slug: lowercase, alphanumeric and hyphens."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-") or "template"


def get_db() -> Session:
    """Return a DB session (caller must close or use as context)."""
    return SessionLocal()


def check_db_connection() -> None:
    """Verify database is reachable; exit with a clear message if not."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except OperationalError as e:
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "Connection refused" in msg or "could not connect" in msg.lower():
            print("Database not available. Start PostgreSQL (e.g. docker-compose up -d) or set DATABASE_URL.", file=sys.stderr)
            print("Example: DATABASE_URL=postgresql://user:pass@localhost:5432/dbname", file=sys.stderr)
        else:
            print(f"Database error: {msg}", file=sys.stderr)
        sys.exit(1)


@contextmanager
def db_session():
    """Context manager for a database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _find_existing(db: Session, slug: Optional[str], name: str, version: int):
    if slug:
        return db.query(TemplateRegistry).filter(
            TemplateRegistry.slug == slug,
            TemplateRegistry.version == version,
        ).first()
    return db.query(TemplateRegistry).filter(
        TemplateRegistry.name == name,
        TemplateRegistry.version == version,
    ).first()


def upsert_template(
    db: Session,
    tpl_dict: Dict[str, Any],
    mode: Literal["demo", "prod"] = "demo",
    force: bool = False,
) -> TemplateRegistry:
    """
    Insert or update a template. Uniqueness by (slug, version) or (name, version).
    - prod: only fill empty fields (thumbnail_url, preview_url, etc.); never overwrite structure.
    - demo + force: overwrite almost everything except id/created_at.
    - demo + no force: update only non-destructive fields.
    """
    slug = tpl_dict.get("slug")
    name = tpl_dict.get("name")
    version = int(tpl_dict.get("version", 1))
    existing = _find_existing(db, slug, name, version)

    # Resolve parent_template_id later if parent_template_slug given
    parent_template_slug = tpl_dict.pop("parent_template_slug", None)
    parent_template_version = tpl_dict.pop("parent_template_version", 1)

    if existing:
        if mode == "prod":
            # Only fill empty / non-destructive
            if not existing.preview_thumbnail_url and tpl_dict.get("preview_thumbnail_url"):
                existing.preview_thumbnail_url = tpl_dict["preview_thumbnail_url"]
            if not existing.preview_url and tpl_dict.get("preview_url"):
                existing.preview_url = tpl_dict["preview_url"]
            if tpl_dict.get("is_recommended") is not None:
                existing.is_recommended = bool(tpl_dict["is_recommended"])
            if tpl_dict.get("feature_tags_json") and not existing.feature_tags_json:
                existing.feature_tags_json = tpl_dict["feature_tags_json"]
            if tpl_dict.get("status") and (existing.status or "") not in ("published", "validated"):
                existing.status = tpl_dict.get("status", "published")
            db.flush()
            return existing

        if mode == "demo":
            if force:
                for key, value in tpl_dict.items():
                    if key in ("id", "created_at", "parent_template_slug", "parent_template_version"):
                        continue
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                for key in ("preview_thumbnail_url", "preview_url", "is_recommended", "feature_tags_json", "status"):
                    if key in tpl_dict and hasattr(existing, key):
                        setattr(existing, key, tpl_dict[key])
            db.flush()
            return existing

    # Insert new
    tpl_dict.setdefault("slug", slug or slugify(name))
    tpl_dict.setdefault("version", version)
    tpl_dict.setdefault("parent_template_slug", parent_template_slug)
    tpl_dict.setdefault("parent_template_version", parent_template_version)

    row = TemplateRegistry(
        slug=tpl_dict.get("slug"),
        name=tpl_dict.get("name"),
        description=tpl_dict.get("description"),
        source_type=tpl_dict.get("source_type", "ai"),
        intent=tpl_dict.get("intent") or tpl_dict.get("template_intent"),
        generator_prompt=tpl_dict.get("generator_prompt"),
        repo_url=tpl_dict.get("repo_url"),
        default_branch=tpl_dict.get("repo_branch") or tpl_dict.get("default_branch"),
        repo_path=tpl_dict.get("repo_path"),
        status=tpl_dict.get("status", "published"),
        is_active=tpl_dict.get("is_active", True),
        is_published=tpl_dict.get("is_published", True),
        is_default=tpl_dict.get("is_default", False),
        is_recommended=tpl_dict.get("is_recommended", False),
        category=tpl_dict.get("category"),
        style=tpl_dict.get("style"),
        feature_tags_json=tpl_dict.get("feature_tags_json") or [],
        features_json=tpl_dict.get("features_json") or tpl_dict.get("feature_tags_json") or [],
        pages_json=tpl_dict.get("pages_json") or [],
        required_inputs_json=tpl_dict.get("required_inputs_json") or [],
        optional_inputs_json=tpl_dict.get("optional_inputs_json") or [],
        default_config_json=tpl_dict.get("default_config_json") or {},
        rules_json=tpl_dict.get("rules_json") or [],
        validation_results_json=tpl_dict.get("validation_results_json") or {},
        version=tpl_dict.get("version", 1),
        changelog=tpl_dict.get("changelog"),
        preview_status=tpl_dict.get("preview_status", "ready"),
        preview_url=tpl_dict.get("preview_url"),
        preview_thumbnail_url=tpl_dict.get("preview_thumbnail_url") or tpl_dict.get("thumbnail_url"),
        preview_error=None,
        preview_last_generated_at=tpl_dict.get("preview_last_generated_at"),
    )
    db.add(row)
    db.flush()
    return row


def enforce_single_default(db: Session, default_slug: str = "residential-modern", default_version: int = 1) -> None:
    """Set is_default=False for all, then is_default=True only for the given slug+version."""
    for t in db.query(TemplateRegistry).filter(TemplateRegistry.is_default == True).all():
        t.is_default = False
    default_row = db.query(TemplateRegistry).filter(
        TemplateRegistry.slug == default_slug,
        TemplateRegistry.version == default_version,
    ).first()
    if default_row:
        default_row.is_default = True
    db.flush()
