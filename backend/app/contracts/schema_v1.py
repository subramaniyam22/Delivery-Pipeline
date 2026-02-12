"""
Delivery Contract schema v1 — canonical project spec for agents and autopilot.
Strict, versioned shape; no raw DB dumps.
"""
from typing import Any, Dict, List


SCHEMA_VERSION = 1


def empty_contract(project_id: str, last_updated_by: str, updated_at: str) -> Dict[str, Any]:
    """Return minimal v1 contract skeleton."""
    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "last_updated_by": last_updated_by,
            "updated_at": updated_at,
            "audit": [],
        },
        "onboarding": {
            "status": "draft",
            "summary": "",
            "primary_contact": {},
            "brand": {},
            "design_preferences": {},
            "compliance": {},
            "website_fundamentals": {},
        },
        "assignments": {
            "consultant_id": None,
            "builder_id": None,
            "tester_id": None,
        },
        "template": {
            "selected_template_id": None,
            "selected_template_version": None,
            "blueprint_ref": None,
        },
        "artifacts": {
            "uploads": [],
            "build_outputs": {
                "preview_url": None,
                "repo_url": None,
                "bundle_url": None,
            },
        },
        "stages": {},
        "quality": {
            "lighthouse": {"perf": None, "a11y": None, "seo": None, "bp": None},
            "axe": {"critical": None, "serious": None},
        },
        "approvals": [],
        "audit": [],
    }


def stages_skeleton() -> Dict[str, Dict[str, Any]]:
    """Default stages keys with status and outputs."""
    keys = [
        "0_sales", "1_onboarding", "2_assignment", "3_build", "4_test",
        "5_defect_validation", "6_complete",
        "7_reserved", "8_reserved", "9_reserved", "10_reserved", "11_reserved", "12_reserved",
    ]
    return {k: {"status": "not_started", "outputs": {}} for k in keys}
