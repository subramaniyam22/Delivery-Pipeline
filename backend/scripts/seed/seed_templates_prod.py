"""
Prod template seed: 3 core templates only. Idempotent; never overwrites structure.
"""
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from scripts.seed.common import db_session, upsert_template, enforce_single_default
from scripts.seed.templates_catalog import get_templates_catalog
from app.models import TemplateRegistry

_CORE_SLUGS = {"residential-modern", "corporate-property-manager", "luxury-lifestyle"}


def main():
    catalog = get_templates_catalog()
    core = [t for t in catalog if t.get("slug") in _CORE_SLUGS and t.get("version") == 1]
    with db_session() as db:
        for tpl in core:
            upsert_template(db, dict(tpl), mode="prod", force=False)
        enforce_single_default(db, default_slug="residential-modern", default_version=1)
        rows = db.query(TemplateRegistry).filter(
            TemplateRegistry.slug.in_(_CORE_SLUGS),
            TemplateRegistry.version == 1,
        ).order_by(TemplateRegistry.slug).all()
        print("Prod templates seeded. Summary:")
        print(f"{'Name':<35} {'Slug':<28} {'Status':<12} {'Default':<8} {'Recommended'}")
        print("-" * 90)
        for r in rows:
            print(f"{r.name or '':<35} {r.slug or '':<28} {(r.status or ''):<12} {str(r.is_default):<8} {str(r.is_recommended)}")


if __name__ == "__main__":
    main()
