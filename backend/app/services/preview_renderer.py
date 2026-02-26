"""
Render static HTML preview from blueprint_json + demo_dataset.
Uses Jinja2 snippets per section type; tokens for colors/typography; demo data in content_slots.
WCAG 2 AA: contrast and landmarks (one main, unique section labels) applied in tokens and structure.
"""
from typing import Any, Dict, List, Optional

import html as html_module
from jinja2 import Environment, BaseLoader


def _hex_to_rgb(hex_color: str) -> tuple:
    """Parse #rrggbb to (r,g,b) 0-255."""
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if len(h) == 3:
        return int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16)
    return 0, 0, 0


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Relative luminance 0-1 (WCAG)."""
    def f(x: int) -> float:
        x = x / 255.0
        return (x / 12.92) if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast_text_on(hex_bg: str) -> str:
    """Return a foreground hex that meets WCAG AA contrast on hex_bg (e.g. #ffffff or #1a1a2e)."""
    r, g, b = _hex_to_rgb(hex_bg)
    lum = _relative_luminance(r, g, b)
    return "#ffffff" if lum < 0.4 else "#1a1a2e"


def _contrast_button_on_white(hex_primary: str) -> str:
    """Return a button text color on white background that meets WCAG AA (use primary if dark enough, else dark blue)."""
    r, g, b = _hex_to_rgb(hex_primary)
    lum = _relative_luminance(r, g, b)
    return hex_primary if lum < 0.4 else "#1e3a5f"


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio between two relative luminances (0-1)."""
    lo, hi = min(lum1, lum2), max(lum1, lum2)
    return (hi + 0.05) / (lo + 0.05) if lo >= 0 else 21.0


def _link_color_for_background(link_hex: str, bg_hex: str) -> str:
    """Return a link color that meets WCAG AA (4.5:1) on bg. Avoids color-contrast Axe failures."""
    link_rgb = _hex_to_rgb(link_hex)
    bg_rgb = _hex_to_rgb(bg_hex)
    link_lum = _relative_luminance(*link_rgb)
    bg_lum = _relative_luminance(*bg_rgb)
    if _contrast_ratio(link_lum, bg_lum) >= 4.5:
        return link_hex
    if bg_lum > 0.5:
        return "#1e3a5f"  # dark blue on light background
    return "#93c5fd"  # light blue on dark background

# Section type -> (html snippet template, optional variant handling)
SECTION_SNIPPETS = {
    "hero": """
<section class="section-hero" {{ aria_attr }} style="{% if hero_image_url %}background: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url('{{ hero_image_url }}') center/cover; color: #ffffff;{% else %}background: {{ primary }}; color: {{ text_light }};{% endif %} padding: {{ section_padding }}px 24px; min-height: 280px; display: flex; align-items: center;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h1 style="font-family: {{ font_family }}; font-size: {{ h1_size }}px; margin: 0 0 12px;">{{ hero_title }}</h1>
    <p style="font-size: {{ body_size }}px; opacity: 0.95; margin: 0;">{{ hero_subtitle }}</p>
    {% if cta_text %}<a href="{{ cta_href }}" class="cta" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: {{ accent }}; color: {{ text_on_accent }}; border-radius: {{ card_radius }}px; text-decoration: none;">{{ cta_text }}</a>{% endif %}
  </div>
</section>""",
    "trust_bar": """
<section class="section-trust" {{ aria_attr }} style="padding: 24px; background: {{ background }}; border-bottom: 1px solid #e2e8f0;">
  <div class="container" style="max-width: 900px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;">
    {% for item in trust_items %}<span style="font-size: {{ body_size }}px; color: {{ text }};">{{ item }}</span>{% if not loop.last %} · {% endif %}{% endfor %}
  </div>
</section>""",
    "amenities_grid": """
<section class="section-amenities" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">{{ amenities_title }}</h2>
    <ul style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; list-style: none; padding: 0; margin: 0;">
      {% for a in amenities_list %}<li style="padding: 12px; background: {{ background }}; border-radius: {{ card_radius }}px; border: 1px solid #e2e8f0;">{{ a }}</li>{% endfor %}
    </ul>
  </div>
</section>""",
    "gallery_grid": """
<section class="section-gallery" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">{{ gallery_title }}</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px;">
      {% for img in gallery_images %}<img src="{{ img }}" alt="{{ gallery_title }} image {{ loop.index }}" style="width: 100%; height: 200px; object-fit: cover; border-radius: {{ card_radius }}px;" loading="lazy" />{% endfor %}
    </div>
  </div>
</section>""",
    "floorplan_cards": """
<section class="section-floorplans" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">{{ floorplans_title }}</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px;">
      {% for fp in floor_plans %}<div style="border: 1px solid #e2e8f0; border-radius: {{ card_radius }}px; overflow: hidden;"><img src="{{ fp.image_url }}" alt="{{ fp.name }}" style="width: 100%; height: 160px; object-fit: cover;" /><div style="padding: 12px;"><strong>{{ fp.name }}</strong> · {{ fp.beds }} bed, {{ fp.baths }} bath · from ${{ fp.rent_from }}</div></div>{% endfor %}
    </div>
  </div>
</section>""",
    "location_map": """
<section class="section-map" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 12px;">Location</h2>
    <p style="font-size: {{ body_size }}px; color: {{ text }};">{{ address }}</p>
    <div style="height: 200px; border-radius: {{ card_radius }}px; overflow: hidden;">
      <iframe title="Map showing location" src="{{ map_embed_url }}" style="width: 100%; height: 100%; border: 0;" loading="lazy"></iframe>
    </div>
  </div>
</section>""",
    "testimonials": """
<section class="section-testimonials" {{ aria_attr }} style="padding: {{ section_padding }}px 24px; background: {{ background }};">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">What residents say</h2>
    <div style="display: grid; gap: 16px;">
      {% for t in testimonials_list %}<blockquote style="margin: 0; padding: 16px; border-left: 4px solid {{ primary }}; background: #ffffff; color: {{ text }}; border-radius: {{ card_radius }}px;">{{ t.quote }} — <cite>{{ t.name }}</cite></blockquote>{% endfor %}
    </div>
  </div>
</section>""",
    "faq": """
<section class="section-faq" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">FAQ</h2>
    <dl style="margin: 0;">
      {% for faq in faqs_list %}<div style="margin-bottom: 16px;"><dt style="font-weight: 600; margin-bottom: 4px;">{{ faq.q }}</dt><dd style="margin: 0; color: {{ text }};">{{ faq.a }}</dd></div>{% endfor %}
    </dl>
  </div>
</section>""",
    "feature_split": """
<section class="section-feature-split" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 32px; align-items: center;">
    <div><h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 12px;">{{ feature_heading }}</h2><p style="font-size: {{ body_size }}px; color: {{ text }};">{{ feature_body }}</p></div>
    <div style="height: 200px; border-radius: {{ card_radius }}px; overflow: hidden;">{% if feature_image_url %}<img src="{{ feature_image_url }}" alt="" style="width: 100%; height: 100%; object-fit: cover;" />{% else %}<div style="height: 100%; background: {{ primary }}; opacity: 0.2;"></div>{% endif %}</div>
  </div>
</section>""",
    "cta_banner": """
<section class="section-cta" {{ aria_attr }} style="padding: {{ section_padding }}px 24px; background: {{ primary }}; color: {{ text_on_primary }}; text-align: center;">
  <div class="container" style="max-width: 700px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 12px;">{{ cta_heading }}</h2>
    <p style="margin: 0 0 20px;">{{ cta_subtext }}</p>
    <a href="{{ cta_link }}" style="display: inline-block; padding: 12px 24px; background: #ffffff; color: {{ button_text_on_white }}; border-radius: {{ card_radius }}px; text-decoration: none;">{{ cta_button }}</a>
  </div>
</section>""",
    "contact_form": """
<section class="section-contact" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 500px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">Contact us</h2>
    <form action="#" method="get" style="display: flex; flex-direction: column; gap: 12px;" aria-label="Contact form (preview only)">
      <input type="text" placeholder="Name" disabled style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px;" />
      <input type="email" placeholder="Email" disabled style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px;" />
      <textarea placeholder="Message" rows="4" disabled style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px;"></textarea>
      <button type="button" disabled style="padding: 12px; background: {{ primary }}; color: {{ text_on_primary }}; border: none; border-radius: 8px;">Send (preview)</button>
    </form>
  </div>
</section>""",
    "pricing_table": """
<section class="section-pricing" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;"><h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px;">Pricing</h2><p style="color: {{ text }};">Preview placeholder</p></div>
</section>""",
    "blog_teasers": """
<section class="section-blog" {{ aria_attr }} style="padding: {{ section_padding }}px 24px;">
  <div class="container" style="max-width: 900px; margin: 0 auto;"><h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px;">Blog</h2><p style="color: {{ text }};">Preview placeholder</p></div>
</section>""",
}


def _text_accessible_on_background(text_hex: str, bg_hex: str) -> str:
    """Return a foreground color that meets WCAG AA (4.5:1) on bg. Used for body/section text to fix color-contrast."""
    t_rgb = _hex_to_rgb(text_hex)
    b_rgb = _hex_to_rgb(bg_hex)
    t_lum = _relative_luminance(*t_rgb)
    b_lum = _relative_luminance(*b_rgb)
    if _contrast_ratio(t_lum, b_lum) >= 4.5:
        return text_hex
    return "#ffffff" if b_lum < 0.4 else "#1a1a2e"


def _get_tokens(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    tokens = (blueprint.get("tokens") or {}) if isinstance(blueprint, dict) else {}
    colors = tokens.get("colors") or {}
    typography = tokens.get("typography") or {}
    scale = typography.get("scale") or {}
    spacing = tokens.get("spacing") or {}
    primary = colors.get("primary") or "#2563eb"
    accent = colors.get("accent") or "#3b82f6"
    background = colors.get("background") or "#ffffff"
    text_raw = colors.get("text") or "#0f172a"
    text_accessible = _text_accessible_on_background(text_raw, background)
    return {
        "primary": primary,
        "secondary": (colors.get("secondary") or "#1e40af"),
        "background": background,
        "text": text_accessible,
        "text_raw": text_raw,
        "accent": accent,
        "text_light": _contrast_text_on(primary),
        "text_on_primary": _contrast_text_on(primary),
        "text_on_accent": _contrast_text_on(accent),
        "button_text_on_white": _contrast_button_on_white(primary),
        "link_color": _link_color_for_background(primary, background),
        "font_family": (typography.get("fontFamily") or "Inter, sans-serif"),
        "h1_size": scale.get("h1") or 32,
        "h2_size": scale.get("h2") or 24,
        "body_size": scale.get("body") or 16,
        "section_padding": spacing.get("sectionPadding") or 48,
        "card_radius": spacing.get("cardRadius") or 12,
    }


def _is_relative_image_path(url: Any) -> bool:
    """True if url looks like a relative path (e.g. assets/img/hero.jpg), not an absolute URL. Preview bundle does not serve image files; use template-uploaded URLs instead."""
    if not url or not isinstance(url, str):
        return False
    s = url.strip()
    if not s:
        return False
    if s.startswith("http://") or s.startswith("https://") or s.startswith("//"):
        return False
    return True


def _normalize_category_key(category: Optional[str]) -> str:
    """Normalize section image_prompt_category for lookup (exterior, interior, etc.)."""
    if not category or not isinstance(category, str):
        return ""
    return category.strip().lower().replace(" ", "_") or ""


def _get_template_images_by_category(template_images: Optional[Dict[str, List[str]]], category: Optional[str]) -> List[str]:
    """Return list of URLs for a given category (exterior, interior, etc.) from template uploads. Falls back to 'general' then first non-empty category."""
    if not template_images:
        return []
    norm = _normalize_category_key(category)
    for key in (category, norm, "general"):
        if not key:
            continue
        urls = template_images.get(key)
        result = list(urls) if isinstance(urls, list) else [urls] if urls else []
        if result:
            return result
    # Use first non-empty category so any uploaded images appear in preview
    for urls in template_images.values():
        result = list(urls) if isinstance(urls, list) else [urls] if urls else []
        if result:
            return result
    return []


def _get_demo_slots(
    section_type: str,
    content_slots: Dict[str, Any],
    demo: Dict[str, Any],
    template_images: Optional[Dict[str, List[str]]] = None,
    image_prompt_category: Optional[str] = None,
) -> Dict[str, Any]:
    demo = demo or {}
    slots = content_slots or {}
    template_images = template_images or {}
    out = {}
    if section_type == "hero":
        brand = demo.get("brand") or {}
        out["hero_title"] = slots.get("title") or brand.get("name") or "Welcome"
        out["hero_subtitle"] = slots.get("subtitle") or (demo.get("company") or {}).get("description") or "Your tagline here"
        out["cta_text"] = slots.get("cta_text") or "Get started"
        out["cta_href"] = slots.get("cta_href") or "#"
        # Prefer uploaded template images when available so blueprint uploads are always used in preview
        hero_from_slot = slots.get("hero_image_url") or slots.get("image")
        hero_imgs = _get_template_images_by_category(template_images, image_prompt_category or "exterior")
        if hero_imgs:
            out["hero_image_url"] = hero_imgs[0]
        else:
            out["hero_image_url"] = hero_from_slot
    elif section_type == "trust_bar":
        out["trust_items"] = slots.get("items") or demo.get("amenities") or ["Trusted", "Secure", "Fast"]
    elif section_type == "amenities_grid":
        out["amenities_title"] = slots.get("title") or "Amenities"
        out["amenities_list"] = slots.get("items") or demo.get("amenities") or ["Pool", "Fitness", "Parking"]
    elif section_type == "gallery_grid":
        out["gallery_title"] = slots.get("title") or "Gallery"
        gallery_from_template = _get_template_images_by_category(template_images, image_prompt_category or "exterior")
        # Prefer uploaded template images when available so blueprint uploads are always used in preview
        if gallery_from_template:
            out["gallery_images"] = gallery_from_template
        else:
            slot_images = slots.get("images")
            if slot_images is not None and isinstance(slot_images, list) and len(slot_images) > 0:
                out["gallery_images"] = slot_images
            else:
                out["gallery_images"] = demo.get("gallery_images") or ["https://placehold.co/800x500?text=Image"]
    elif section_type == "floorplan_cards":
        out["floorplans_title"] = slots.get("title") or "Floor plans"
        out["floor_plans"] = slots.get("plans") or demo.get("floor_plans") or [{"name": "2B/2B", "beds": 2, "baths": 2, "rent_from": 1850, "image_url": "https://placehold.co/400x300?text=2B2B"}]
    elif section_type == "location_map":
        out["address"] = slots.get("address") or (demo.get("property") or {}).get("address") or "123 Main St"
        # Sample map embed URL (OpenStreetMap) for context; no API key. Use property geo or default NYC.
        geo = (demo.get("property") or {}).get("geo") or {}
        lat = float(geo.get("lat", 40.7128))
        lng = float(geo.get("lng", -74.0060))
        delta = 0.01
        bbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"
        out["map_embed_url"] = (
            f"https://www.openstreetmap.org/export/embed.html?"
            f"bbox={bbox}&layer=mapnik&marker={lat},{lng}"
        )
    elif section_type == "testimonials":
        out["testimonials_list"] = slots.get("items") or demo.get("testimonials") or [{"name": "Jane D.", "quote": "Great experience."}]
    elif section_type == "faq":
        out["faqs_list"] = slots.get("items") or demo.get("faqs") or [{"q": "Question?", "a": "Answer."}]
    elif section_type == "feature_split":
        out["feature_heading"] = slots.get("heading") or "Feature"
        out["feature_body"] = slots.get("body") or "Description."
        # Prefer uploaded template images when available so blueprint uploads are always used in preview
        feature_from_slot = slots.get("feature_image_url") or slots.get("image")
        split_imgs = _get_template_images_by_category(template_images, image_prompt_category or "interior")
        if split_imgs:
            out["feature_image_url"] = split_imgs[0]
        else:
            out["feature_image_url"] = feature_from_slot
    elif section_type == "cta_banner":
        out["cta_heading"] = slots.get("heading") or "Get in touch"
        out["cta_subtext"] = slots.get("subtext") or "We'd love to hear from you."
        out["cta_button"] = slots.get("button") or "Contact us"
        out["cta_link"] = slots.get("link") or "#contact"
    else:
        out.update(slots)
    return out


_SECTION_TYPE_LABELS: Dict[str, str] = {
    "hero": "Hero",
    "trust_bar": "Trust bar",
    "amenities_grid": "Amenities",
    "gallery_grid": "Gallery",
    "floorplan_cards": "Floor plans",
    "location_map": "Location",
    "testimonials": "Testimonials",
    "faq": "FAQ",
    "feature_split": "Feature",
    "cta_banner": "Call to action",
    "contact_form": "Contact",
}


def _render_section(
    sec: Dict[str, Any],
    tokens: Dict[str, Any],
    demo: Dict[str, Any],
    env: Environment,
    template_images: Optional[Dict[str, List[str]]] = None,
    section_index: int = 0,
) -> str:
    stype = (sec.get("type") or "hero").strip()
    content_slots = sec.get("content_slots") or {}
    image_prompt_category = (sec.get("image_prompt_category") or "").strip() or None
    a11y = sec.get("a11y") or {}
    aria_label = a11y.get("ariaLabel") if isinstance(a11y, dict) else None
    if not aria_label:
        type_label = _SECTION_TYPE_LABELS.get(stype) or stype.replace("_", " ").title()
        aria_label = f"{type_label} {section_index + 1}"
    # Use only aria-label on <section> (implicit role="region") to satisfy aria-roles and landmark-unique
    safe_label = html_module.escape(str(aria_label).strip() or "Content region")
    aria_attr = f'aria-label="{safe_label}"'
    slots = _get_demo_slots(stype, content_slots, demo, template_images, image_prompt_category)
    ctx = {**tokens, **slots, "aria_attr": aria_attr}
    if stype in SECTION_SNIPPETS:
        try:
            tpl = env.from_string(SECTION_SNIPPETS[stype])
            return tpl.render(**ctx)
        except Exception:
            pass
    return f'<section class="section-unknown" style="padding: 24px; background: #f1f5f9; border-radius: 8px;"><p style="margin: 0;">Section: {html_module.escape(stype)} (placeholder)</p></section>'


def _nav_html(blueprint: Dict[str, Any], tokens: Dict[str, Any], logo_url: Optional[str] = None) -> str:
    """Build nav with relative hrefs (index.html, slug.html) so preview works from S3 subpath. Optional logo_url shows client logo."""
    nav = blueprint.get("navigation") or {}
    items = nav.get("items") or []
    primary = tokens.get("primary", "#2563eb")
    text_on_primary = tokens.get("text_on_primary", "#ffffff")
    font_family = tokens.get("font_family", "Inter, sans-serif")

    def _href_for_slug(slug: str) -> str:
        s = (slug or "").strip().lstrip("/")
        if not s or s == "home":
            return "index.html"
        return f"{s}.html"

    links = "".join(
        f'<a href="{_href_for_slug(item.get("href") or "")}" style="color: {text_on_primary}; text-decoration: none; padding: 8px 16px;">{html_module.escape(item.get("label") or "")}</a>'
        for item in items if isinstance(item, dict)
    )
    logo_part = ""
    if logo_url and logo_url.startswith(("http://", "https://", "data:")):
        logo_part = f'<img src="{html_module.escape(logo_url)}" alt="Logo" style="height: 36px; max-width: 140px; object-fit: contain; margin-right: 12px; vertical-align: middle;" />'
    return f'<nav style="background: {primary}; padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;" aria-label="Main navigation">{logo_part}<a href="index.html" style="color: {text_on_primary}; text-decoration: none; font-weight: 600;">{html_module.escape((blueprint.get("meta") or {}).get("name") or "Home")}</a>{links}</nav>'


def _footer_href(href: str) -> str:
    """Normalize footer link to relative .html so preview works when served from /api/templates/{id}/preview/ (avoids 404 on /about, /careers)."""
    if not href or href == "#":
        return "#"
    s = (href or "").strip().lstrip("/")
    if not s:
        return "index.html"
    if s.startswith("http://") or s.startswith("https://") or s.startswith("mailto:"):
        return href
    return f"{s}.html" if not s.endswith(".html") else s


def _collect_linked_slugs(blueprint: Dict[str, Any]) -> List[str]:
    """Collect all nav and footer link slugs so we can generate a page for each (no 404s)."""
    slugs: List[str] = []
    nav = blueprint.get("navigation") or {}
    for item in nav.get("items") or []:
        if not isinstance(item, dict):
            continue
        href = (item.get("href") or "").strip().lstrip("/")
        if href and href != "home" and not href.startswith("http") and not href.startswith("#"):
            base = href.replace(".html", "")
            if base and base not in slugs:
                slugs.append(base)
    footer = blueprint.get("footer") or {}
    for sec in footer.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        for link in sec.get("links") or []:
            if not isinstance(link, dict):
                continue
            href = (link.get("href") or "").strip().lstrip("/")
            if href and href != "#" and not href.startswith("http") and not href.startswith("mailto:"):
                base = href.replace(".html", "")
                if base and base not in slugs:
                    slugs.append(base)
    return slugs


def _footer_html(blueprint: Dict[str, Any], tokens: Dict[str, Any]) -> str:
    footer = blueprint.get("footer") or {}
    sections = footer.get("sections") or []
    text = tokens.get("text", "#64748b")
    body_size = tokens.get("body_size", 16)
    parts = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = sec.get("title") or ""
        links = sec.get("links") or []
        link_str = " ".join(
            f'<a href="{html_module.escape(_footer_href(l.get("href") or ""))}" style="color: {text}; font-size: {body_size}px;">{html_module.escape(l.get("label") or "")}</a>'
            for l in links if isinstance(l, dict)
        )
        parts.append(f"<div><strong>{html_module.escape(title)}</strong> {link_str}</div>")
    return f'<footer role="contentinfo" aria-label="Site footer" style="padding: 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; margin-top: 48px;"><div style="max-width: 900px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 24px;">{"".join(parts)}</div></footer>'


def _render_one_page_html(
    blueprint_json: Dict[str, Any],
    demo_dataset: Dict[str, Any],
    page: Dict[str, Any],
    template_images: Optional[Dict[str, List[str]]] = None,
) -> str:
    """Render full HTML for one page (nav + sections + footer). Used for index and slug.html."""
    if not blueprint_json or not isinstance(blueprint_json, dict):
        return "<!DOCTYPE html><html><body><p>No blueprint</p></body></html>"
    tokens = _get_tokens(blueprint_json)
    env = Environment(loader=BaseLoader(), autoescape=True)
    template_images = template_images or {}
    sections_html = []
    for i, sec in enumerate(page.get("sections") or []):
        if isinstance(sec, dict):
            sections_html.append(_render_section(sec, tokens, demo_dataset, env, template_images, section_index=i))
    logo_url = (demo_dataset.get("brand") or {}).get("logo_url") if demo_dataset else None
    nav = _nav_html(blueprint_json, tokens, logo_url=logo_url)
    footer = _footer_html(blueprint_json, tokens)
    meta_name = (blueprint_json.get("meta") or {}).get("name") or "Preview"
    title = page.get("title") or "Home"
    font_family = tokens.get("font_family", "Inter, sans-serif")
    body_size = tokens.get("body_size", 16)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_module.escape(title)} - {html_module.escape(meta_name)}</title>
  <style>
    body {{ margin: 0; font-family: {font_family}; font-size: {body_size}px; color: {tokens.get("text", "#0f172a")}; background: {tokens.get("background", "#ffffff")}; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    a {{ color: {tokens.get("link_color", "#1e3a5f")}; }}
  </style>
</head>
<body>
{nav}
<main id="main-content" role="main" aria-label="Main content">
{"".join(sections_html)}
</main>
{footer}
</body>
</html>"""


def render_preview_html(blueprint_json: Dict[str, Any], demo_dataset: Dict[str, Any]) -> str:
    """Produce a single HTML string for the first page (home). Kept for backward compatibility."""
    pages = (blueprint_json or {}).get("pages") or []
    first_page = pages[0] if pages and isinstance(pages[0], dict) else {"slug": "home", "title": "Home", "sections": []}
    return _render_one_page_html(blueprint_json, demo_dataset, first_page)


def _slug_to_title_from_blueprint(blueprint: Dict[str, Any]) -> Dict[str, str]:
    """Build slug -> page title from nav and footer so placeholder pages have sensible titles."""
    m: Dict[str, str] = {}
    for item in (blueprint.get("navigation") or {}).get("items") or []:
        if isinstance(item, dict):
            href = (item.get("href") or "").strip().lstrip("/").replace(".html", "")
            if href and href != "home":
                m[href] = (item.get("label") or href.replace("-", " ").title()).strip() or href
    for sec in (blueprint.get("footer") or {}).get("sections") or []:
        if isinstance(sec, dict):
            for link in sec.get("links") or []:
                if isinstance(link, dict):
                    href = (link.get("href") or "").strip().lstrip("/").replace(".html", "")
                    if href and href != "#":
                        if href not in m:
                            m[href] = (link.get("label") or href.replace("-", " ").title()).strip() or href
    return m


def _default_sections_for_placeholder_page(page_title: str) -> List[Dict[str, Any]]:
    """
    Return a full set of sections for an internal/placeholder page so it shows real content
    and images from the demo dataset (company description, gallery, testimonials, FAQ, etc.)
    instead of only a trust bar. Each section is filled by _get_demo_slots from demo_dataset.
    Uses multiple image_prompt_category values so template_images (e.g. client uploads) are
    used across hero, feature, and gallery sections.
    """
    return [
        {"type": "trust_bar", "content_slots": {}},
        {"type": "hero", "content_slots": {"title": page_title}, "image_prompt_category": "exterior"},
        {"type": "feature_split", "content_slots": {}, "image_prompt_category": "interior"},
        {"type": "gallery_grid", "content_slots": {}, "image_prompt_category": "lifestyle"},
        {"type": "amenities_grid", "content_slots": {}},
        {"type": "floorplan_cards", "content_slots": {}},
        {"type": "testimonials", "content_slots": {}},
        {"type": "faq", "content_slots": {}},
        {"type": "location_map", "content_slots": {}},
        {"type": "contact_form", "content_slots": {}},
        {"type": "cta_banner", "content_slots": {}},
    ]


def render_preview_assets(
    blueprint_json: Dict[str, Any],
    demo_dataset: Dict[str, Any],
    template_images: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Return dict of path -> content (str or bytes).
    index.html (first page), one {slug}.html per other page (so nav/footer links never 404).
    Ensures every linked slug from nav and footer has a generated page (placeholder if not in blueprint).
    assets/style.css, assets/app.js.
    template_images: optional dict category -> list of image URLs (from Template Registry uploads) used for hero, gallery, feature_split by image_prompt_category.
    """
    if not blueprint_json or not isinstance(blueprint_json, dict):
        return {"index.html": "<!DOCTYPE html><html><body><p>No blueprint</p></body></html>"}
    tokens = _get_tokens(blueprint_json)
    primary = tokens.get("primary", "#2563eb")
    font_family = tokens.get("font_family", "Inter, sans-serif")
    template_images = template_images or {}
    css = f"""
:root {{
  --color-primary: {primary};
  --font-body: {font_family};
}}
body {{ margin: 0; box-sizing: border-box; }}
* {{ box-sizing: border-box; }}
"""
    js = "// Preview static bundle - no runtime required."
    pages = list(blueprint_json.get("pages") or [])
    if not pages or not isinstance(pages[0], dict):
        pages = [{"slug": "home", "title": "Home", "sections": []}]
    existing_slugs = {(p.get("slug") or "").strip().lstrip("/").replace(".html", "") or "home": p for p in pages if isinstance(p, dict)}
    linked_slugs = _collect_linked_slugs(blueprint_json)
    slug_to_title = _slug_to_title_from_blueprint(blueprint_json)
    for slug in linked_slugs:
        if not slug or slug == "home":
            continue
        if slug not in existing_slugs:
            title = slug_to_title.get(slug) or slug.replace("-", " ").title()
            pages.append({
                "slug": slug,
                "title": title,
                "sections": _default_sections_for_placeholder_page(title),
            })
            existing_slugs[slug] = pages[-1]
    out = {
        "index.html": _render_one_page_html(blueprint_json, demo_dataset, pages[0], template_images),
        "assets/style.css": css.strip(),
        "assets/app.js": js,
    }
    for i in range(1, len(pages)):
        page = pages[i]
        if not isinstance(page, dict):
            continue
        slug = (page.get("slug") or "").strip().lstrip("/") or f"page{i}"
        out[f"{slug}.html"] = _render_one_page_html(blueprint_json, demo_dataset, page, template_images)
    return out


def _nav_label(i: int, pages: List[Any], items: List[Any]) -> str:
    """Return a plain string label for the nav link at index i (no nested f-strings)."""
    if i < len(items) and isinstance(items[i], dict):
        label = items[i].get("label")
        if label:
            return str(label)
    if i < len(pages) and isinstance(pages[i], dict):
        title = pages[i].get("title")
        if title:
            return str(title)
    return "Page " + str(i + 1)


def render_preview_assets_single_page(
    blueprint_json: Dict[str, Any],
    demo_dataset: Dict[str, Any],
    template_images: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Return a single index.html containing all pages' content with in-page anchors (#section-0, #section-1, ...).
    Use this for client preview so one S3 signed URL works and navigation does not trigger AccessDenied.
    """
    if not blueprint_json or not isinstance(blueprint_json, dict):
        return {"index.html": "<!DOCTYPE html><html><body><p>No blueprint</p></body></html>"}
    tokens = _get_tokens(blueprint_json)
    primary = tokens.get("primary", "#2563eb")
    font_family = tokens.get("font_family", "Inter, sans-serif")
    template_images = template_images or {}
    env = Environment(loader=BaseLoader(), autoescape=True)
    pages = blueprint_json.get("pages") or []
    if not pages or not isinstance(pages[0], dict):
        pages = [{"slug": "home", "title": "Home", "sections": []}]
    nav = blueprint_json.get("navigation") or {}
    items = nav.get("items") or []
    meta_name = (blueprint_json.get("meta") or {}).get("name") or "Preview"
    text_on_primary = tokens.get("text_on_primary", "#ffffff")
    section_index = 0
    page_section_starts = []
    sections_html = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_section_starts.append(section_index)
        for sec in page.get("sections") or []:
            if isinstance(sec, dict):
                html = _render_section(
                    sec, tokens, demo_dataset, env, template_images, section_index=section_index
                )
                sections_html.append(
                    f'<div id="section-{section_index}" class="page-section" role="region" aria-label="{html_module.escape((page.get("title") or "Section") + " " + str(section_index + 1))}">'
                    + html
                    + "</div>"
                )
                section_index += 1
    nav_links = "".join(
        f'<a href="#section-{page_section_starts[i]}" style="color: {text_on_primary}; text-decoration: none; padding: 8px 16px;">{html_module.escape(_nav_label(i, pages, items))}</a>'
        for i in range(len(page_section_starts))
    )
    nav_html = f'<nav style="background: {primary}; padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;" aria-label="Main navigation"><a href="#" style="color: {text_on_primary}; text-decoration: none; font-weight: 600;">{html_module.escape(meta_name)}</a>{nav_links}</nav>'
    footer = _footer_html(blueprint_json, tokens)
    body_text = tokens.get("text", "#1a1a2e")
    body_bg = tokens.get("background", "#ffffff")
    link_color = tokens.get("link_color", "#1e3a5f")
    css = f"""
:root {{ --color-primary: {primary}; --font-body: {font_family}; }}
body {{ margin: 0; box-sizing: border-box; color: {body_text}; background: {body_bg}; }}
* {{ box-sizing: border-box; }}
a {{ color: {link_color}; }}
"""
    js = "// Preview static bundle - no runtime required."
    body_size = tokens.get("body_size", 16)
    single_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_module.escape(meta_name)} - Preview</title>
  <style>{css}</style>
</head>
<body>
{nav_html}
<main id="main-content" role="main" aria-label="Main content">
{"".join(sections_html)}
</main>
{footer}
</body>
</html>"""
    return {
        "index.html": single_html,
        "assets/style.css": css.strip(),
        "assets/app.js": js,
    }
