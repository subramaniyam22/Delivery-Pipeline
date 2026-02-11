"""
Demo preview dataset for template previews (API).
Uses scripts.seed.demo_data when available so there is a single source of truth.
"""
from typing import Any, Dict, Optional

try:
    from scripts.seed.demo_data import get_demo_dataset_by_key as _get_demo_dataset_by_key
except ImportError:
    _get_demo_dataset_by_key = None

DEMO_DATASET_KEY = "pmc_default_v1"


def generate_demo_preview_dataset() -> Dict[str, Any]:
    """Return the default demo dataset. Delegates to scripts when available."""
    try:
        from scripts.seed.demo_data import generate_demo_preview_dataset as _gen
        return _gen()
    except ImportError:
        return _default_dataset()


def get_demo_dataset_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Return full demo dataset for a given key (for API)."""
    if _get_demo_dataset_by_key is not None:
        return _get_demo_dataset_by_key(key)
    if key == DEMO_DATASET_KEY or key == "pmc_default_v1":
        return _default_dataset()
    return None


def _default_dataset() -> Dict[str, Any]:
    """Inline fallback when scripts.seed is not importable."""
    return {
        "brand": {"name": "PMC Properties", "logo_url": "https://placehold.co/200x80/2563eb/white?text=PMC", "colors": {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#3b82f6"}, "fonts": {"heading": "Inter", "body": "Inter"}},
        "company": {"description": "Professional property management and leasing.", "phone": "+1 (555) 123-4567", "email": "contact@pmcproperties.example.com"},
        "property": {"name": "Sunset Gardens", "address": "123 Main St, Anytown, ST 12345", "geo": {"lat": 40.7128, "lng": -74.0060}, "highlights": ["Pool", "Fitness Center", "Pet Friendly"]},
        "amenities": ["Pool", "Fitness Center", "Pet Friendly", "Parking", "Laundry"],
        "gallery_images": ["https://placehold.co/800x500/2563eb/white?text=Hero", "https://placehold.co/800x500/1e40af/white?text=Gallery+1", "https://placehold.co/800x500/3b82f6/white?text=Gallery+2"],
        "floor_plans": [{"name": "2B/2B", "beds": 2, "baths": 2, "sqft": 1100, "rent_from": 1850, "image_url": "https://placehold.co/400x300?text=2B2B"}, {"name": "3B/2B", "beds": 3, "baths": 2, "sqft": 1400, "rent_from": 2200, "image_url": "https://placehold.co/400x300?text=3B2B"}],
        "testimonials": [{"name": "Jane D.", "quote": "Great management and responsive team."}, {"name": "John S.", "quote": "Love the amenities and location."}],
        "faqs": [{"q": "What is the lease term?", "a": "Standard 12-month lease."}, {"q": "Are pets allowed?", "a": "Yes, with deposit and monthly fee."}],
        "policies": {"privacy_url": "https://example.com/privacy", "terms_url": "https://example.com/terms"},
        "social_links": {"facebook": "https://facebook.com/example", "instagram": "https://instagram.com/example", "linkedin": "https://linkedin.com/company/example"},
        "locations": [{"name": "Sunset Gardens", "address": "123 Main St", "geo": {"lat": 40.7128, "lng": -74.0060}}],
    }
