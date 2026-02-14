"""
Blueprint schema v1 — strict, versioned, deterministic template structure.
"""
from typing import Any, Dict, List, Tuple

BLUEPRINT_SCHEMA_VERSION = 1

ALLOWED_SECTION_TYPES = {
    "hero", "trust_bar", "amenities_grid", "gallery_grid", "floorplan_cards",
    "location_map", "testimonials", "faq", "feature_split", "cta_banner",
    "contact_form", "pricing_table", "blog_teasers",
}
NAV_STYLES = {"topbar", "sidebar", "minimal"}
WCAG_TARGETS = {"A", "AA", "AAA"}


def _err(path: str, msg: str) -> str:
    return f"{path}: {msg}"


def validate_blueprint_v1(blueprint: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate blueprint against v1 schema. Returns (valid, list of error strings with field paths)."""
    errors: List[str] = []
    if not isinstance(blueprint, dict):
        return False, ["root: must be a dict"]

    # Accept integer 1, string "1" or "v1", or missing (treat as v1)
    sv = blueprint.get("schema_version")
    if sv not in (1, "1", "v1", None):
        errors.append(_err("schema_version", "must be 1"))
    elif sv is None or sv != 1:
        blueprint["schema_version"] = 1  # normalize for storage

    meta = blueprint.get("meta")
    if not isinstance(meta, dict):
        errors.append(_err("meta", "required object"))
    else:
        if not meta.get("name"):
            errors.append(_err("meta.name", "required"))
        if not meta.get("category"):
            errors.append(_err("meta.category", "required"))
        if not meta.get("style"):
            errors.append(_err("meta.style", "required"))

    tokens = blueprint.get("tokens")
    if not isinstance(tokens, dict):
        errors.append(_err("tokens", "required object"))
    else:
        for k in ("colors", "typography", "spacing"):
            if k not in tokens:
                errors.append(_err(f"tokens.{k}", "required"))

    nav = blueprint.get("navigation")
    if not isinstance(nav, dict):
        errors.append(_err("navigation", "required object"))
    else:
        if nav.get("style") not in NAV_STYLES:
            errors.append(_err("navigation.style", f"must be one of {NAV_STYLES}"))
        items = nav.get("items")
        if not isinstance(items, list):
            errors.append(_err("navigation.items", "required list"))

    footer = blueprint.get("footer")
    if not isinstance(footer, dict):
        errors.append(_err("footer", "required object"))

    pages = blueprint.get("pages")
    if not isinstance(pages, list):
        errors.append(_err("pages", "required list"))
    elif len(pages) == 0:
        errors.append(_err("pages", "at least one page required"))
    else:
        slugs = []
        has_home = False
        has_cta = False
        for i, p in enumerate(pages):
            if not isinstance(p, dict):
                errors.append(_err(f"pages[{i}]", "must be object"))
                continue
            slug = (p.get("slug") or "").strip()
            if not slug:
                errors.append(_err(f"pages[{i}].slug", "required"))
            slugs.append(slug)
            if slug == "home":
                has_home = True
            if not has_home and i == 0:
                has_home = True  # first page treated as home
            sections = p.get("sections") or []
            if not isinstance(sections, list):
                errors.append(_err(f"pages[{i}].sections", "required list"))
            elif len(sections) == 0:
                errors.append(_err(f"pages[{i}].sections", "at least one section required"))
            else:
                for j, sec in enumerate(sections):
                    if not isinstance(sec, dict):
                        continue
                    stype = sec.get("type")
                    if stype and stype not in ALLOWED_SECTION_TYPES:
                        errors.append(_err(f"pages[{i}].sections[{j}].type", f"allowed: {ALLOWED_SECTION_TYPES}"))
                    if stype in ("cta_banner", "hero"):
                        has_cta = True
        if not has_home:
            errors.append(_err("pages", "home page required (slug='home' or first page)"))
        if not has_cta:
            errors.append(_err("pages", "at least one CTA section required (cta_banner or hero with CTA)"))

        # Nav items link to existing pages
        if isinstance(nav, dict) and isinstance(nav.get("items"), list):
            for item in nav["items"]:
                if isinstance(item, dict) and item.get("href"):
                    href = (item.get("href") or "").strip().lstrip("/")
                    if href and href not in slugs and href != "#":
                        errors.append(_err("navigation.items", f"href '{href}' does not match any page slug"))

    forms = blueprint.get("forms")
    if not isinstance(forms, dict):
        errors.append(_err("forms", "required object"))
    lead = (forms or {}).get("lead") if isinstance(forms, dict) else {}
    contact_form = None
    for i, p in enumerate((pages or [])):
        if not isinstance(p, dict):
            continue
        for sec in (p.get("sections") or []):
            if isinstance(sec, dict) and sec.get("type") == "contact_form":
                contact_form = True
                break
    lead_enabled = isinstance(lead, dict) and lead.get("enabled")
    if not contact_form and not lead_enabled:
        errors.append(_err("forms", "contact_form section or lead form enabled required"))

    constraints = blueprint.get("constraints")
    if not isinstance(constraints, dict):
        errors.append(_err("constraints", "required object"))
    else:
        wcag = constraints.get("wcag_target")
        if wcag not in WCAG_TARGETS:
            errors.append(_err("constraints.wcag_target", f"must be one of {WCAG_TARGETS}"))

    return len(errors) == 0, errors
