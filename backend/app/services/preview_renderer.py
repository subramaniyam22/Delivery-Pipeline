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

# Section type -> (html snippet template, optional variant handling)
SECTION_SNIPPETS = {
    "hero": """
<section class="section-hero" {{ aria_attr }} style="{% if hero_image_url %}background: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url('{{ hero_image_url }}') center/cover;{% else %}background: {{ primary }};{% endif %} color: {{ text_light }}; padding: {{ section_padding }}px 24px; min-height: 280px; display: flex; align-items: center;">
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
      {% for img in gallery_images %}<img src="{{ img }}" alt="Gallery" style="width: 100%; height: 200px; object-fit: cover; border-radius: {{ card_radius }}px;" loading="lazy" />{% endfor %}
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
    <div style="height: 200px; background: #e2e8f0; border-radius: {{ card_radius }}px; display: flex; align-items: center; justify-content: center; color: #64748b;">Map placeholder</div>
  </div>
</section>""",
    "testimonials": """
<section class="section-testimonials" {{ aria_attr }} style="padding: {{ section_padding }}px 24px; background: {{ background }};">
  <div class="container" style="max-width: 900px; margin: 0 auto;">
    <h2 style="font-family: {{ font_family }}; font-size: {{ h2_size }}px; margin: 0 0 20px;">What residents say</h2>
    <div style="display: grid; gap: 16px;">
      {% for t in testimonials_list %}<blockquote style="margin: 0; padding: 16px; border-left: 4px solid {{ primary }}; background: white; border-radius: {{ card_radius }}px;">{{ t.quote }} — <cite>{{ t.name }}</cite></blockquote>{% endfor %}
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
    <a href="{{ cta_link }}" style="display: inline-block; padding: 12px 24px; background: white; color: {{ button_text_on_white }}; border-radius: {{ card_radius }}px; text-decoration: none;">{{ cta_button }}</a>
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


def _get_tokens(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    tokens = (blueprint.get("tokens") or {}) if isinstance(blueprint, dict) else {}
    colors = tokens.get("colors") or {}
    typography = tokens.get("typography") or {}
    scale = typography.get("scale") or {}
    spacing = tokens.get("spacing") or {}
    primary = colors.get("primary") or "#2563eb"
    accent = colors.get("accent") or "#3b82f6"
    return {
        "primary": primary,
        "secondary": (colors.get("secondary") or "#1e40af"),
        "background": (colors.get("background") or "#ffffff"),
        "text": (colors.get("text") or "#0f172a"),
        "accent": accent,
        "text_light": _contrast_text_on(primary),
        "text_on_primary": _contrast_text_on(primary),
        "text_on_accent": _contrast_text_on(accent),
        "button_text_on_white": _contrast_button_on_white(primary),
        "font_family": (typography.get("fontFamily") or "Inter, sans-serif"),
        "h1_size": scale.get("h1") or 32,
        "h2_size": scale.get("h2") or 24,
        "body_size": scale.get("body") or 16,
        "section_padding": spacing.get("sectionPadding") or 48,
        "card_radius": spacing.get("cardRadius") or 12,
    }


def _get_template_images_by_category(template_images: Optional[Dict[str, List[str]]], category: Optional[str]) -> List[str]:
    """Return list of URLs for a given category (exterior, interior, etc.) from template uploads."""
    if not template_images or not category:
        return []
    urls = template_images.get(category) or template_images.get(category.lower())
    return list(urls) if isinstance(urls, list) else [urls] if urls else []


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
        hero_imgs = _get_template_images_by_category(template_images, image_prompt_category or "exterior")
        out["hero_image_url"] = hero_imgs[0] if hero_imgs else None
    elif section_type == "trust_bar":
        out["trust_items"] = slots.get("items") or demo.get("amenities") or ["Trusted", "Secure", "Fast"]
    elif section_type == "amenities_grid":
        out["amenities_title"] = slots.get("title") or "Amenities"
        out["amenities_list"] = slots.get("items") or demo.get("amenities") or ["Pool", "Fitness", "Parking"]
    elif section_type == "gallery_grid":
        out["gallery_title"] = slots.get("title") or "Gallery"
        gallery_from_template = _get_template_images_by_category(template_images, image_prompt_category or "exterior")
        out["gallery_images"] = slots.get("images") or gallery_from_template or demo.get("gallery_images") or ["https://placehold.co/800x500?text=Image"]
    elif section_type == "floorplan_cards":
        out["floorplans_title"] = slots.get("title") or "Floor plans"
        out["floor_plans"] = slots.get("plans") or demo.get("floor_plans") or [{"name": "2B/2B", "beds": 2, "baths": 2, "rent_from": 1850, "image_url": "https://placehold.co/400x300?text=2B2B"}]
    elif section_type == "location_map":
        out["address"] = slots.get("address") or (demo.get("property") or {}).get("address") or "123 Main St"
    elif section_type == "testimonials":
        out["testimonials_list"] = slots.get("items") or demo.get("testimonials") or [{"name": "Jane D.", "quote": "Great experience."}]
    elif section_type == "faq":
        out["faqs_list"] = slots.get("items") or demo.get("faqs") or [{"q": "Question?", "a": "Answer."}]
    elif section_type == "feature_split":
        out["feature_heading"] = slots.get("heading") or "Feature"
        out["feature_body"] = slots.get("body") or "Description."
        split_imgs = _get_template_images_by_category(template_images, image_prompt_category or "interior")
        out["feature_image_url"] = split_imgs[0] if split_imgs else None
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
    aria_attr = f'aria-label="{html_module.escape(aria_label)}"' if aria_label else ""
    slots = _get_demo_slots(stype, content_slots, demo, template_images, image_prompt_category)
    ctx = {**tokens, **slots, "aria_attr": aria_attr}
    if stype in SECTION_SNIPPETS:
        try:
            tpl = env.from_string(SECTION_SNIPPETS[stype])
            return tpl.render(**ctx)
        except Exception:
            pass
    return f'<section class="section-unknown" style="padding: 24px; background: #f1f5f9; border-radius: 8px;"><p style="margin: 0;">Section: {html_module.escape(stype)} (placeholder)</p></section>'


def _nav_html(blueprint: Dict[str, Any], tokens: Dict[str, Any]) -> str:
    """Build nav with relative hrefs (index.html, slug.html) so preview works from S3 subpath."""
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
    return f'<nav style="background: {primary}; padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;" aria-label="Main navigation"><a href="index.html" style="color: {text_on_primary}; text-decoration: none; font-weight: 600;">{html_module.escape((blueprint.get("meta") or {}).get("name") or "Home")}</a>{links}</nav>'


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
            f'<a href="{html_module.escape((l.get("href") or "#"))}" style="color: {text}; font-size: {body_size}px;">{html_module.escape(l.get("label") or "")}</a>'
            for l in links if isinstance(l, dict)
        )
        parts.append(f"<div><strong>{html_module.escape(title)}</strong> {link_str}</div>")
    return f'<footer style="padding: 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; margin-top: 48px;"><div style="max-width: 900px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 24px;">{"".join(parts)}</div></footer>'


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
    nav = _nav_html(blueprint_json, tokens)
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
    body {{ margin: 0; font-family: {font_family}; font-size: {body_size}px; color: {tokens.get("text", "#0f172a")}; background: {tokens.get("background", "#fff")}; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    a {{ color: {tokens.get("primary", "#2563eb")}; }}
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


def render_preview_assets(
    blueprint_json: Dict[str, Any],
    demo_dataset: Dict[str, Any],
    template_images: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Return dict of path -> content (str or bytes).
    index.html (first page), one {slug}.html per other page (so nav links work from S3 subpath),
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
    pages = blueprint_json.get("pages") or []
    if not pages or not isinstance(pages[0], dict):
        pages = [{"slug": "home", "title": "Home", "sections": []}]
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
        f'<a href="#section-{page_section_starts[i]}" style="color: {text_on_primary}; text-decoration: none; padding: 8px 16px;">{html_module.escape((items[i].get("label") or (pages[i].get("title") if i < len(pages) and isinstance(pages[i], dict) else f"Page {i + 1}")) if i < len(items) and isinstance(items[i], dict) else (pages[i].get("title") if i < len(pages) and isinstance(pages[i], dict) else f"Page {i + 1}")}</a>'
        for i in range(len(page_section_starts))
    )
    nav_html = f'<nav style="background: {primary}; padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;" aria-label="Main navigation"><a href="#" style="color: {text_on_primary}; text-decoration: none; font-weight: 600;">{html_module.escape(meta_name)}</a>{nav_links}</nav>'
    footer = _footer_html(blueprint_json, tokens)
    css = f"""
:root {{ --color-primary: {primary}; --font-body: {font_family}; }}
body {{ margin: 0; box-sizing: border-box; }}
* {{ box-sizing: border-box; }}
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
