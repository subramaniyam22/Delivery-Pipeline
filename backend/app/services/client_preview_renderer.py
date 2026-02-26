"""
Render client preview assets from template blueprint + delivery contract.
Uses real client onboarding data (brand, content) with graceful fallbacks.
Multi-page output: index.html plus one {slug}.html per page so users can navigate to all pages.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List

from app.services.preview_renderer import render_preview_assets
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
    logo_url = (brand.get("logo_url") or "").strip() or "https://placehold.co/200x80/2563eb/white?text=Logo"
    images_json = brand.get("images") or []
    if isinstance(images_json, list) and images_json:
        gallery_images = []
        for img in images_json[:12]:
            u = None
            if isinstance(img, dict):
                u = (img.get("url") or img.get("path") or img.get("file_path") or (img.get("storage_key") if isinstance(img.get("storage_key"), str) and img.get("storage_key", "").startswith("http") else None))
                if u:
                    u = str(u).strip()
            elif isinstance(img, str):
                u = img.strip() if img else None
            if u and u.startswith(("http://", "https://", "data:")):
                gallery_images.append(u)
        if not gallery_images:
            gallery_images = ["https://placehold.co/800x500?text=Client+content+pending"]
    else:
        gallery_images = ["https://placehold.co/800x500?text=Client+content+pending"]
    copy_text = (fundamentals.get("copy_text") or req.get("copy_scope_notes") or "").strip()
    privacy_url = fundamentals.get("privacy_policy_url") or ""
    privacy_text = (fundamentals.get("privacy_policy_text") or "").strip()
    primary_contact = ob.get("primary_contact") or {}
    brand_name = primary_contact.get("company_name") or primary_contact.get("name") or "Client"
    project_summary = (req.get("project_summary") or ob.get("summary") or "").strip()
    project_notes = (req.get("project_notes") or "").strip()
    # Use full client content across the site: hero, company, property, amenities, testimonials, faqs
    description = project_summary or project_notes or (copy_text[:300] if copy_text else "Professional services.")
    # Highlights and amenities from summary/notes/copy so internal pages have real content
    highlights = []
    if project_summary:
        highlights.append(project_summary[:120])
    if project_notes:
        highlights.append(project_notes[:120])
    if copy_text and len(highlights) < 3:
        highlights.append(copy_text[:120])
    if not highlights:
        highlights = ["Client content pending"]
    amenities_list = [s.strip() for s in (project_notes or copy_text or "").replace("\n", ",").split(",") if s.strip()][:10]
    if not amenities_list:
        amenities_list = highlights[:5] if len(highlights) > 1 else ["Client content pending"]
    testimonials = []
    if project_summary:
        testimonials.append({"name": brand_name, "quote": project_summary[:200]})
    if project_notes:
        testimonials.append({"name": "Team", "quote": project_notes[:200]})
    if copy_text:
        testimonials.append({"name": brand_name, "quote": copy_text[:200]})
    if not testimonials:
        testimonials = [{"name": brand_name, "quote": "Client content pending."}]
    faqs = []
    if privacy_url or privacy_text:
        faqs.append({"q": "Privacy policy", "a": privacy_text[:300] if privacy_text else f"See {privacy_url}"})
    nav_notes = (req.get("navigation_notes") or "").strip()
    if nav_notes:
        faqs.append({"q": "Navigation & structure", "a": nav_notes[:200]})
    if not faqs:
        faqs = [{"q": "Contact", "a": primary_contact.get("email") or primary_contact.get("phone") or "See contact details."}]
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
            "highlights": highlights,
        },
        "amenities": amenities_list,
        "gallery_images": gallery_images,
        "floor_plans": [
            {"name": "2B/2B", "beds": 2, "baths": 2, "sqft": 1100, "rent_from": 0, "image_url": gallery_images[0] if gallery_images else "https://placehold.co/400x300?text=Floor+plan"},
        ],
        "testimonials": testimonials,
        "faqs": faqs,
        "policies": {"privacy_url": privacy_url, "terms_url": ""},
        "social_links": {},
        "locations": [{"name": brand_name, "address": primary_contact.get("address") or "Address pending", "geo": {"lat": 40.7128, "lng": -74.0060}}],
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


def _client_images_as_template_images(contract: Dict[str, Any]) -> Dict[str, List[str]]:
    """Build category -> [urls] from contract onboarding brand.images and logo so hero/gallery/feature_split use client uploads."""
    ob = (contract or {}).get("onboarding") or {}
    brand = ob.get("brand") or {}
    images_json = brand.get("images") or []
    logo_url = (brand.get("logo_url") or "").strip()
    urls: List[str] = []
    if logo_url and logo_url.startswith(("http://", "https://", "data:")):
        urls.append(logo_url)
    for img in (images_json if isinstance(images_json, list) else [])[:12]:
        if isinstance(img, dict):
            u = img.get("url") or img.get("path") or img.get("file_path")
            if u:
                u = str(u).strip()
                if u.startswith(("http://", "https://", "data:")):
                    urls.append(u)
        elif isinstance(img, str) and img.strip().startswith(("http://", "https://", "data:")):
            urls.append(img.strip())
    if not urls:
        return {}
    # Spread to all section categories so hero, gallery, feature_split get client images (no relative 404s)
    return {cat: urls for cat in ("exterior", "interior", "lifestyle", "people", "neighborhood")}


def render_client_preview_assets(
    blueprint_json: Dict[str, Any],
    contract_json: Dict[str, Any],
) -> Dict[str, str]:
    """
    Render preview assets using blueprint structure and client data from contract.
    Multi-page: index.html plus one {slug}.html per page so users can navigate to all pages.
    Passes client-uploaded images as template_images so hero/gallery/feature sections show them.
    Returns dict of path -> content (str). Never raises; missing data uses placeholders.
    """
    try:
        if not blueprint_json or not isinstance(blueprint_json, dict):
            return {"index.html": "<!DOCTYPE html><html><body><p>No blueprint</p></body></html>"}
        client_dataset = _contract_to_client_dataset(contract_json)
        blueprint_with_tokens = _blueprint_with_client_tokens(blueprint_json, contract_json or {})
        client_template_images = _client_images_as_template_images(contract_json or {})
        assets = render_preview_assets(
            blueprint_with_tokens, client_dataset, template_images=client_template_images
        )
        return assets
    except Exception:
        return {"index.html": "<!DOCTYPE html><html><body><p>Preview generation failed. Please try again.</p></body></html>"}
