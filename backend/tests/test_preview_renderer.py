"""Minimal regression tests for preview_renderer: import and render_preview_assets_single_page.

Prevents SyntaxError regressions (e.g. f-string closing brace mismatch) that break worker import.
"""
import pytest

from app.services.preview_renderer import render_preview_assets_single_page


def test_preview_renderer_imports():
    """Import must succeed so worker can load template_preview pipeline."""
    from app.services import preview_renderer  # noqa: F401
    assert hasattr(preview_renderer, "render_preview_assets_single_page")


def test_render_preview_assets_single_page_minimal_blueprint():
    """Call render_preview_assets_single_page with minimal blueprint; no SyntaxError."""
    blueprint = {
        "meta": {"name": "Test"},
        "pages": [
            {"slug": "home", "title": "Home", "sections": []},
        ],
        "navigation": {"items": []},
    }
    demo = {}
    out = render_preview_assets_single_page(blueprint, demo)
    assert "index.html" in out
    assert isinstance(out["index.html"], str)
    assert "Preview" in out["index.html"] or "Test" in out["index.html"]
    assert "section-0" in out["index.html"] or "main" in out["index.html"]
