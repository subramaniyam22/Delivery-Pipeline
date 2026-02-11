"""
Demo preview dataset generator for template previews.
Full dataset is keyed by demo_dataset_key (e.g. pmc_default_v1); templates store only the key.
"""
from typing import Any, Dict, Optional

DEMO_DATASET_KEY = "pmc_default_v1"


def generate_demo_preview_dataset() -> Dict[str, Any]:
    """Return a single JSON-serializable object for preview renderer."""
    return {
        "brand": {
            "name": "PMC Properties",
            "logo_url": "https://placehold.co/200x80/2563eb/white?text=PMC",
            "colors": {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#3b82f6"},
            "fonts": {"heading": "Inter", "body": "Inter"},
        },
        "company": {
            "description": "Professional property management and leasing.",
            "phone": "+1 (555) 123-4567",
            "email": "contact@pmcproperties.example.com",
        },
        "property": {
            "name": "Sunset Gardens",
            "address": "123 Main St, Anytown, ST 12345",
            "geo": {"lat": 40.7128, "lng": -74.0060},
            "highlights": ["Pool", "Fitness Center", "Pet Friendly"],
        },
        "amenities": ["Pool", "Fitness Center", "Pet Friendly", "Parking", "Laundry"],
        "gallery_images": [
            "https://placehold.co/800x500/2563eb/white?text=Hero",
            "https://placehold.co/800x500/1e40af/white?text=Gallery+1",
            "https://placehold.co/800x500/3b82f6/white?text=Gallery+2",
        ],
        "floor_plans": [
            {"name": "2B/2B", "beds": 2, "baths": 2, "sqft": 1100, "rent_from": 1850, "image_url": "https://placehold.co/400x300?text=2B2B"},
            {"name": "3B/2B", "beds": 3, "baths": 2, "sqft": 1400, "rent_from": 2200, "image_url": "https://placehold.co/400x300?text=3B2B"},
        ],
        "testimonials": [
            {"name": "Jane D.", "quote": "Great management and responsive team."},
            {"name": "John S.", "quote": "Love the amenities and location."},
        ],
        "faqs": [
            {"q": "What is the lease term?", "a": "Standard 12-month lease."},
            {"q": "Are pets allowed?", "a": "Yes, with deposit and monthly fee."},
        ],
        "policies": {
            "privacy_url": "https://example.com/privacy",
            "terms_url": "https://example.com/terms",
        },
        "social_links": {
            "facebook": "https://facebook.com/example",
            "instagram": "https://instagram.com/example",
            "linkedin": "https://linkedin.com/company/example",
        },
        "locations": [
            {"name": "Sunset Gardens", "address": "123 Main St", "geo": {"lat": 40.7128, "lng": -74.0060}},
        ],
    }


def get_demo_dataset_for_template(slug: str) -> Dict[str, Any]:
    """Merge default dataset with template-specific overrides."""
    base = generate_demo_preview_dataset()
    slug_lower = (slug or "").lower()
    if "student-housing" in slug_lower:
        base.setdefault("roommate_info", {"available": True, "notes": "Roommate matching available."})
    if "luxury" in slug_lower:
        base.setdefault("hero_video_url", "https://placehold.co/1920x1080?text=Hero+Video")
    if "multi-location" in slug_lower:
        base["locations"] = [
            {"name": "Location A", "address": "100 First St", "geo": {"lat": 40.71, "lng": -74.00}},
            {"name": "Location B", "address": "200 Second St", "geo": {"lat": 40.72, "lng": -74.01}},
        ]
    return base


def get_demo_dataset_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Return full demo dataset for a given key (for API)."""
    if key == DEMO_DATASET_KEY or key == "pmc_default_v1":
        return generate_demo_preview_dataset()
    return None
