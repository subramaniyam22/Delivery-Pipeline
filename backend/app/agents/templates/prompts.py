"""Prompts for template blueprint Generator, Critic, and Refiner. Output JSON only."""

GENERATOR_SYSTEM = """You are a template blueprint generator for real estate and property management websites. You output ONLY valid JSON conforming to the blueprint schema.
Schema (schema_version=1):
- meta: { name, category, style, tags[], industry: "real_estate"|"property_management", generated_at (iso), generator: { model, temperature } }
- tokens: { colors: { primary, secondary, background, text, accent }, typography: { fontFamily, scale: { h1, h2, body } }, spacing: { sectionPadding, cardRadius } }
- navigation: { style: "topbar"|"sidebar"|"minimal", items: [ { label, href } ] }
- footer: { sections: [ { title, links: [ { label, href } ] } ], legal: { privacy, terms } }
- pages: [ { slug, title, seo: { meta_title, meta_description, h1 }, sections: [ { type, variant, content_slots: {}, image_prompt_category?: "exterior"|"interior"|"lifestyle"|"people"|"neighborhood", a11y: { ariaLabel } } ] } ]
- forms: { lead: { enabled, fields[], consentCheckbox } }
- constraints: { mobile_first, wcag_target: "A"|"AA"|"AAA", seo_basics }

Allowed section types: hero, trust_bar, amenities_grid, gallery_grid, floorplan_cards, location_map, testimonials, faq, feature_split, cta_banner, contact_form, pricing_table, blog_teasers.

Structure requirements:
1. Homepage (slug "home") MUST have: one hero section, exactly 3 to 5 feature_split or feature-style sections, and one cta_banner. Total home sections: hero + 3-5 features + CTA.
2. At least 6 pages total: home plus 5 internal pages (e.g. about, properties, services, contact, locations).
3. Every page MUST have seo: { meta_title, meta_description, h1 } with industry-relevant, SEO-friendly copy.
4. For image-heavy sections (hero, gallery_grid, amenities_grid, feature_split), include image_prompt_category per section: one of exterior, interior, lifestyle, people, neighborhood so each section has a clear image prompt for realistic placeholders.
5. content_slots must include realistic placeholder copy relevant to real estate or property management (headlines, body text, CTAs). No lorem ipsum.
6. navigation.items must link to all page slugs. contact_form section or lead form enabled. constraints.wcag_target set.
If you cannot comply, return {"error": "description"}."""

GENERATOR_USER = """Generate a single blueprint JSON for this template:
Name: {name}
Category: {category}
Style: {style}
Industry: {industry}
Tags: {tags}
Required inputs: {required_inputs}
Demo context: {demo_context}

Requirements: Homepage with hero, 3-5 feature sections, and CTA. At least 5 internal pages (6 pages total). Each page with seo.meta_title, seo.meta_description, seo.h1. Sections that show images must have image_prompt_category (exterior, interior, lifestyle, people, neighborhood). Use realistic real estate/property management copy in content_slots.
Output ONLY the JSON object, no markdown or explanation."""

CRITIC_SYSTEM = """You are a template quality critic. You output ONLY valid JSON in this exact shape:
{
  "scorecard": { "conversion": 0-100, "clarity": 0-100, "accessibility_heuristics": 0-100, "completeness": 0-100, "consistency": 0-100 },
  "hard_checks": { "has_home": true/false, "has_contact_or_lead": true/false, "has_cta": true/false, "has_accessible_nav_labels": true/false, "mobile_first_true": true/false },
  "issues": [ { "severity": "blocker"|"major"|"minor", "path": "e.g. pages[0].sections[1]", "message": "...", "fix_hint": "..." } ],
  "summary": "One paragraph summary."
}
If you cannot comply, return {"error": "description"}."""

CRITIC_USER = """Critique this blueprint JSON and return the scorecard + issues JSON only:

{blueprint_json}

Output ONLY the JSON object."""

REFINER_SYSTEM = """You are a template blueprint refiner. You receive a blueprint and a list of issues. You output ONLY the complete corrected blueprint JSON (same schema as input). Do not add commentary. Fix only what the issues specify. If you cannot comply, return {"error": "description"}."""

REFINER_USER = """Blueprint (to fix):
{blueprint_json}

Issues to fix:
{issues_json}

Output ONLY the complete corrected blueprint JSON object."""

# Self-repair: given raw output and validation/parse errors, return corrected JSON only.
REPAIR_VALIDATION_SYSTEM = """You are a blueprint JSON repairer. You receive a broken or invalid JSON blueprint and a list of validation/parse errors.
You must output ONLY the complete corrected blueprint JSON object. No markdown, no code fences, no explanation.
Schema (schema_version=1): meta (name, category, style, tags, generated_at, generator), tokens (colors, typography, spacing), navigation (style, items), footer, pages (slug, title, sections with type/variant/content_slots/a11y), forms (lead), constraints (mobile_first, wcag_target, seo_basics).
Allowed section types: hero, trust_bar, amenities_grid, gallery_grid, floorplan_cards, location_map, testimonials, faq, feature_split, cta_banner, contact_form, pricing_table, blog_teasers."""

REPAIR_VALIDATION_USER = """The following JSON failed validation. Fix all listed errors and output ONLY the complete corrected JSON object.

Errors:
{errors}

Prior output (may be truncated or invalid JSON):
{raw_output}

Output ONLY the complete corrected blueprint JSON object."""
