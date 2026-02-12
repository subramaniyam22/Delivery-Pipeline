"""
Demo template seed: all 12 templates. Use SEED_FORCE=true to overwrite existing.
If SEED_MODE=demo, enqueues (and runs in-process) blueprint generation for each template when OPENAI_API_KEY is set.
"""
import os
import sys

# Ensure backend root is on path when run as python -m scripts.seed.seed_templates_demo
_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.db import SessionLocal
from app.models import TemplateRegistry, TemplateBlueprintJob
from scripts.seed.common import db_session, upsert_template, enforce_single_default
from scripts.seed.templates_catalog import get_templates_catalog


def _set_parent_ids(db):
    """Set parent_template_id for v2 templates after v1 exist."""
    v2_parents = [
        ("residential-modern", 2, "residential-modern", 1),
        ("corporate-property-manager", 2, "corporate-property-manager", 1),
    ]
    for child_slug, child_ver, parent_slug, parent_ver in v2_parents:
        parent = db.query(TemplateRegistry).filter(
            TemplateRegistry.slug == parent_slug,
            TemplateRegistry.version == parent_ver,
        ).first()
        child = db.query(TemplateRegistry).filter(
            TemplateRegistry.slug == child_slug,
            TemplateRegistry.version == child_ver,
        ).first()
        if parent and child:
            child.parent_template_id = parent.id
    db.flush()


def _enqueue_blueprints_for_demo(db):
    """If SEED_MODE=demo and OPENAI_API_KEY set, create and run blueprint job for each template."""
    if os.getenv("SEED_MODE", "").lower() != "demo":
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("SEED_MODE=demo but OPENAI_API_KEY not set; skipping blueprint generation.")
        return
    from app.jobs.template_blueprint import run_blueprint_job
    rows = db.query(TemplateRegistry).order_by(TemplateRegistry.slug, TemplateRegistry.version).all()
    for r in rows:
        job = TemplateBlueprintJob(
            template_id=r.id,
            status="queued",
            payload_json={"regenerate": False, "max_iterations": 3},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        print(f"  Running blueprint pipeline for: {r.name or r.slug}")
        run_blueprint_job(job.id)


def main():
    force = os.getenv("SEED_FORCE", "").lower() == "true"
    catalog = get_templates_catalog()
    with db_session() as db:
        for tpl in catalog:
            upsert_template(db, dict(tpl), mode="demo", force=force)
        _set_parent_ids(db)
        enforce_single_default(db, default_slug="residential-modern", default_version=1)
        # Blueprint generation when SEED_MODE=demo
        if os.getenv("SEED_MODE", "").lower() == "demo":
            _enqueue_blueprints_for_demo(db)
        # Summary
        rows = db.query(TemplateRegistry).order_by(TemplateRegistry.slug, TemplateRegistry.version).all()
        print("Demo templates seeded. Summary:")
        print(f"{'Name':<35} {'Slug':<28} {'Ver':<4} {'Status':<12} {'Default':<8} {'Recommended'}")
        print("-" * 95)
        for r in rows:
            print(f"{r.name or '':<35} {r.slug or '':<28} {r.version or 1:<4} {(r.status or ''):<12} {str(r.is_default):<8} {str(r.is_recommended)}")


if __name__ == "__main__":
    main()
