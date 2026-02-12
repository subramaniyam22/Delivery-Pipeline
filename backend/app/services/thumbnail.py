"""
Thumbnail generation for template previews.
Tier 1: PIL-only (draw hero section as image).
Tier 2: Playwright screenshot when PLAYWRIGHT_ENABLED=true.
"""
from typing import Any, Dict, Optional
import io
import os

from app.config import settings


def _hex_to_rgb(hex_str: str) -> tuple:
    h = (hex_str or "#2563eb").strip().lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    return (37, 99, 235)


def generate_thumbnail_simple(
    blueprint_json: Optional[Dict[str, Any]] = None,
    title: str = "Preview",
    subtitle: str = "",
) -> bytes:
    """
    Generate a thumbnail image using PIL: gradient background + title text.
    No browser dependency.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("PIL/Pillow required for simple thumbnail. Install pillow.")
    width, height = 1200, 800
    tokens = (blueprint_json or {}).get("tokens") or {}
    colors = tokens.get("colors") or {}
    primary = (colors.get("primary") or "#2563eb").strip().lstrip("#")
    try:
        r, g, b = int(primary[0:2], 16), int(primary[2:4], 16), int(primary[4:6], 16)
    except (ValueError, IndexError):
        r, g, b = 37, 99, 235
    img = Image.new("RGB", (width, height), color=(r, g, b))
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except OSError:
        try:
            font_large = ImageFont.truetype("arial.ttf", 48)
            font_small = ImageFont.truetype("arial.ttf", 24)
        except OSError:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
    text_color = (255, 255, 255)
    draw.text((60, height // 2 - 60), (title or "Preview")[: 80], fill=text_color, font=font_large)
    if subtitle:
        draw.text((60, height // 2 + 10), subtitle[: 120], fill=text_color, font=font_small)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_thumbnail_playwright(preview_url: str, viewport_width: int = 1200, viewport_height: int = 800) -> bytes:
    """Capture screenshot of preview_url using headless browser. Requires PLAYWRIGHT_ENABLED=true."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright not installed. Set PREVIEW_THUMBNAIL_MODE=simple or install playwright.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            page.goto(preview_url, wait_until="networkidle", timeout=15000)
            png = page.screenshot(type="png", full_page=False)
            return png
        finally:
            browser.close()


def generate_thumbnail(
    blueprint_json: Optional[Dict[str, Any]] = None,
    preview_url: Optional[str] = None,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
) -> bytes:
    """
    Generate thumbnail bytes. Uses PREVIEW_THUMBNAIL_MODE:
    - simple: PIL hero-style image (no URL needed).
    - playwright: screenshot of preview_url (requires PLAYWRIGHT_ENABLED=true and preview_url).
    """
    mode = (os.getenv("PREVIEW_THUMBNAIL_MODE") or getattr(settings, "PREVIEW_THUMBNAIL_MODE", "simple") or "simple").lower()
    playwright_ok = os.getenv("PLAYWRIGHT_ENABLED", "").lower() == "true" or getattr(settings, "PLAYWRIGHT_ENABLED", False)
    if mode == "playwright" and playwright_ok and preview_url:
        return generate_thumbnail_playwright(preview_url)
    meta = (blueprint_json or {}).get("meta") or {}
    return generate_thumbnail_simple(
        blueprint_json=blueprint_json,
        title=title or meta.get("name") or "Preview",
        subtitle=subtitle or meta.get("category") or "",
    )
