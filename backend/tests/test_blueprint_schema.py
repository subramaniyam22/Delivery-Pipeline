"""
Unit tests for blueprint schema v1 validation.
"""
import pytest
from app.templates.blueprint_schema_v1 import validate_blueprint_v1, BLUEPRINT_SCHEMA_VERSION


def _valid_blueprint_minimal() -> dict:
    return {
        "schema_version": 1,
        "meta": {
            "name": "Test Template",
            "category": "residential",
            "style": "modern",
            "tags": [],
            "generated_at": "2025-01-01T00:00:00Z",
            "generator": {"model": "gpt-4o-mini", "temperature": 0.2},
        },
        "tokens": {
            "colors": {"primary": "#2563eb", "secondary": "#1e40af", "background": "#fff", "text": "#0f172a", "accent": "#22d3ee"},
            "typography": {"fontFamily": "Inter", "scale": {"h1": 32, "h2": 24, "body": 16}},
            "spacing": {"sectionPadding": 48, "cardRadius": 12},
        },
        "navigation": {
            "style": "topbar",
            "items": [{"label": "Home", "href": "home"}, {"label": "Contact", "href": "contact"}],
        },
        "footer": {
            "sections": [{"title": "Links", "links": [{"label": "Home", "href": "home"}]}],
            "legal": {"privacy": True, "terms": True},
        },
        "pages": [
            {
                "slug": "home",
                "title": "Home",
                "sections": [
                    {"type": "hero", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "Hero"}},
                    {"type": "cta_banner", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "CTA"}},
                ],
            },
            {
                "slug": "contact",
                "title": "Contact",
                "sections": [
                    {"type": "contact_form", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "Contact form"}},
                ],
            },
        ],
        "forms": {
            "lead": {"enabled": False, "fields": [], "consentCheckbox": False},
        },
        "constraints": {
            "mobile_first": True,
            "wcag_target": "AA",
            "seo_basics": True,
        },
    }


def test_validate_blueprint_v1_valid():
    bp = _valid_blueprint_minimal()
    valid, errors = validate_blueprint_v1(bp)
    assert valid is True
    assert errors == []


def test_validate_blueprint_v1_wrong_schema_version():
    bp = _valid_blueprint_minimal()
    bp["schema_version"] = 2
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("schema_version" in e for e in errors)


def test_validate_blueprint_v1_not_dict():
    valid, errors = validate_blueprint_v1([])
    assert valid is False
    assert any("dict" in e for e in errors)


def test_validate_blueprint_v1_empty_pages():
    bp = _valid_blueprint_minimal()
    bp["pages"] = []
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("pages" in e and "at least one" in e for e in errors)


def test_validate_blueprint_v1_no_home():
    bp = _valid_blueprint_minimal()
    bp["pages"] = [{"slug": "other", "title": "Other", "sections": [{"type": "hero", "variant": "default", "content_slots": {}, "a11y": None}]}]
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("home" in e.lower() for e in errors)


def test_validate_blueprint_v1_no_cta():
    bp = _valid_blueprint_minimal()
    bp["pages"][0]["sections"] = [{"type": "trust_bar", "variant": "default", "content_slots": {}, "a11y": None}]
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("CTA" in e for e in errors)


def test_validate_blueprint_v1_invalid_section_type():
    bp = _valid_blueprint_minimal()
    bp["pages"][0]["sections"][0]["type"] = "invalid_section"
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("allowed" in e or "type" in e for e in errors)


def test_validate_blueprint_v1_no_contact_or_lead():
    bp = _valid_blueprint_minimal()
    bp["pages"] = [
        {"slug": "home", "title": "Home", "sections": [{"type": "hero", "variant": "default", "content_slots": {}, "a11y": None}, {"type": "cta_banner", "variant": "default", "content_slots": {}, "a11y": None}]},
    ]
    bp["forms"]["lead"]["enabled"] = False
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("contact" in e.lower() or "lead" in e.lower() for e in errors)


def test_validate_blueprint_v1_nav_href_mismatch():
    bp = _valid_blueprint_minimal()
    bp["navigation"]["items"].append({"label": "Missing", "href": "nonexistent"})
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("nonexistent" in e or "slug" in e for e in errors)


def test_validate_blueprint_v1_missing_wcag_target():
    bp = _valid_blueprint_minimal()
    bp["constraints"]["wcag_target"] = "X"
    valid, errors = validate_blueprint_v1(bp)
    assert valid is False
    assert any("wcag" in e.lower() for e in errors)


def test_validate_blueprint_v1_first_page_treated_as_home():
    bp = _valid_blueprint_minimal()
    bp["pages"][0]["slug"] = "landing"
    bp["pages"][0]["title"] = "Landing"
    valid, errors = validate_blueprint_v1(bp)
    assert valid is True
    assert errors == []
