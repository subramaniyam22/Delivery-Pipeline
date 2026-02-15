"""
Render client preview assets from template blueprint + delivery contract.
Uses real client onboarding data (brand, content) with graceful fallbacks.
"""
from __future__ import annotations

import copy
from typing import Any, Dict

from app.services.preview_renderer import render_preview_assets_single_page
from app.services.demo_preview_data import _default_dataset


def _contract_to_client_dataset(contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a dataset dict matching the demo_dataset shape from contract onboarding.
    Uses client-provided project_summary, project_notes, pages, and primary contact so
    the template preview shows real client information. Missing fields get placeholders.
    """
    if not contract or not isinstance(contract, dict):
        return _default_dataset()
    ob = contract.get("onboarding") or {}
    req = ob.get("requirements") or {}
    brand = ob.get("brand") or {}
    design = ob.get("design_preferences") or {}
    fundamentals = ob.get("website_fundamentals") or {}
    theme_colors = design.get("theme_colors") or {}
    if isinstance(theme_colors, dict):
        primary = theme_colors.get("primary") or "#2563eb"
        secondary = theme_colors.get("secondary") or "#1e40af"
        accent = theme_colors.get("accent") or "#3b82f6"
    else:
        primary, secondary, accent = "#2563eb", "#1e40af", "#3b82f6"
    logo_url = brand.get("logo_url") or "https://placehold.co/200x80/2563eb/white?text=Logo"
    images_json = brand.get("images") or []
    if isinstance(images_json, list) and images_json:
        gallery_images = [
            (img.get("url") or img) if isinstance(img, dict) else str(img)
            for img in images_json[:6]
        ]
    else:
        gallery_images = ["https://placehold.co/800x500?text=Client+content+pending"]
    copy_text = fundamentals.get("copy_text") or req.get("copy_scope_notes") or "Client content pending."
    privacy_url = fundamentals.get("privacy_policy_url") or ""
    primary_contact = ob.get("primary_contact") or {}
    brand_name = primary_contact.get("company_name") or primary_contact.get("name") or "Client"
    project_summary = (req.get("project_summary") or ob.get("summary") or "").strip()
    project_notes = (req.get("project_notes") or "").strip()
    description = project_summary or project_notes or copy_text[:200] if copy_text else "Professional services."
    return {
        "brand": {
            "name": brand_name,
            "logo_url": logo_url,
            "colors": {"primary": primary, "secondary": secondary, "accent": accent},
            "fonts": {"heading": "Inter", "body": "Inter"},
        },
        "company": {
            "description": description,
            "phone": primary_contact.get("phone") or "",
            "email": primary_contact.get("email") or "",
        },
        "property": {
            "name": brand_name,
            "address": primary_contact.get("address") or "Address pending",
            "geo": {"lat": 40.7128, "lng": -74.0060},
            "highlights": [project_summary[:80]] if project_summary else ["Client content pending"],
        },
        "amenities": [project_notes[:80]] if project_notes else (["Client content pending"] if not copy_text else [copy_text[:50]]),
        "gallery_images": gallery_images,
        "floor_plans": [
            {"name": "2B/2B", "beds": 2, "baths": 2, "sqft": 1100, "rent_from": 0, "image_url": gallery_images[0] if gallery_images else "https://placehold.co/400x300?text=Floor+plan"},
        ],
        "testimonials": [{"name": brand_name, "quote": (project_summary or copy_text)[:100] if (project_summary or copy_text) else "Client content pending."}],
        "faqs": [{"q": "Privacy", "a": f"Privacy policy: {privacy_url}" if privacy_url else "Client content pending."}],
        "policies": {"privacy_url": privacy_url, "terms_url": ""},
        "social_links": {},
        "locations": [{"name": brand_name, "address": "Address pending", "geo": {"lat": 40.7128, "lng": -74.0060}}],
    }


def _blueprint_with_client_tokens(blueprint: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of blueprint with tokens overridden from contract theme_colors when present."""
    out = copy.deepcopy(blueprint)
    ob = (contract or {}).get("onboarding") or {}
    design = ob.get("design_preferences") or {}
    theme_colors = design.get("theme_colors") or {}
    if not isinstance(theme_colors, dict):
        pass
    else:
        tokens = out.get("tokens") or {}
        colors = dict(tokens.get("colors") or {})
        if theme_colors.get("primary"):
            colors["primary"] = theme_colors["primary"]
        if theme_colors.get("secondary"):
            colors["secondary"] = theme_colors["secondary"]
        if theme_colors.get("accent"):
            colors["accent"] = theme_colors["accent"]
        if theme_colors.get("background"):
            colors["background"] = theme_colors["background"]
        if theme_colors.get("text"):
            colors["text"] = theme_colors["text"]
        out["tokens"] = {**(tokens or {}), "colors": colors}
    req = ob.get("requirements") or {}
    pages_str = (req.get("pages") or "").strip()
    if pages_str:
        nav_items = []
        for i, part in enumerate([p.strip() for p in pages_str.replace(",", "\n").split("\n") if p.strip()]):
            nav_items.append({"label": part, "href": part.lower().replace(" ", "-") if i > 0 else "home"})
        if nav_items:
            out["navigation"] = {"items": nav_items}
    return out


def render_client_preview_assets(
    blueprint_json: Dict[str, Any],
    contract_json: Dict[str, Any],
) -> Dict[str, str]:
    """
    Render preview assets using blueprint structure and client data from contract.
    Returns dict of path -> content (str). Never raises; missing data uses placeholders.
    """
    try:
        if not blueprint_json or not isinstance(blueprint_json, dict):
            return {"index.html": "<!DOCTYPE html><html><body><p>No blueprint</p></body></html>"}
        client_dataset = _contract_to_client_dataset(contract_json)
        blueprint_with_tokens = _blueprint_with_client_tokens(blueprint_json, contract_json or {})
        # Single-page preview so one S3 signed URL works; in-page links avoid AccessDenied on other .html keys
        assets = render_preview_assets_single_page(blueprint_with_tokens, client_dataset)
        return assets
    except Exception:
        return {"index.html": "<!DOCTYPE html><html><body><p>Preview generation failed. Please try again.</p></body></html>"}
