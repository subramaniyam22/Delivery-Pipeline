"""
Tests for blueprint run worker: redaction, parse/validation error codes, status response shape.
"""
import pytest
from app.utils.redact import redact_secrets
from app.templates.blueprint_schema_v1 import validate_blueprint_v1


def test_redact_secrets_sk():
    out = redact_secrets("prefix sk-proj-abc123def456ghi789 suffix")
    assert "sk-" in out
    assert "abc123def456ghi789" not in out
    assert "***REDACTED***" in out


def test_redact_secrets_api_key():
    out = redact_secrets('api_key="sk-12345678901234567890123456789012"')
    assert "***REDACTED***" in out
    assert "12345678901234567890123456789012" not in out


def test_redact_secrets_none():
    assert redact_secrets(None) == ""


def test_validation_error_stores_details():
    """Invalid blueprint fails with VALIDATION_ERROR and produces error list for details."""
    invalid = {"schema_version": 2, "meta": {}}
    valid, errors = validate_blueprint_v1(invalid)
    assert valid is False
    assert len(errors) >= 1
    assert any("schema_version" in e for e in errors)


def test_parse_error_invalid_json():
    """Non-JSON would yield PARSE_ERROR in worker; here we only test validator input."""
    valid, errors = validate_blueprint_v1({"schema_version": 1})  # missing required keys
    assert valid is False
    assert any("meta" in e or "tokens" in e for e in errors)


def _valid_blueprint_minimal():
    return {
        "schema_version": 1,
        "meta": {"name": "T", "category": "residential", "style": "modern", "tags": [], "generated_at": "2025-01-01T00:00:00Z", "generator": {"model": "gpt-4o", "temperature": 0.2}},
        "tokens": {"colors": {"primary": "#2563eb", "secondary": "#1e40af", "background": "#fff", "text": "#0f172a", "accent": "#22d3ee"}, "typography": {"fontFamily": "Inter", "scale": {"h1": 32, "h2": 24, "body": 16}}, "spacing": {"sectionPadding": 48, "cardRadius": 12}},
        "navigation": {"style": "topbar", "items": [{"label": "Home", "href": "home"}, {"label": "Contact", "href": "contact"}]},
        "footer": {"sections": [{"title": "Links", "links": [{"label": "Home", "href": "home"}]}], "legal": {"privacy": True, "terms": True}},
        "pages": [
            {"slug": "home", "title": "Home", "sections": [{"type": "hero", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "Hero"}}, {"type": "cta_banner", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "CTA"}}]},
            {"slug": "contact", "title": "Contact", "sections": [{"type": "contact_form", "variant": "default", "content_slots": {}, "a11y": {"ariaLabel": "Contact form"}}]},
        ],
        "forms": {"lead": {"enabled": False, "fields": [], "consentCheckbox": False}},
        "constraints": {"mobile_first": True, "wcag_target": "AA", "seo_basics": True},
    }


def test_valid_blueprint_passes():
    bp = _valid_blueprint_minimal()
    valid, errors = validate_blueprint_v1(bp)
    assert valid is True
    assert errors == []
