"""
Auto-fix actions for validation failures (e.g. axe color-contrast).
Used by template validation pipeline to apply WCAG-AA safe tokens and re-run.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List

# WCAG 2 AA safe palette: dark text on white, dark primary/accent so white text passes.
WCAG_AA_SAFE_COLORS = {
    "primary": "#1e3a5f",
    "secondary": "#1e40af",
    "background": "#ffffff",
    "text": "#1a1a2e",
    "accent": "#2563eb",
}


def get_fix_actions(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    From validation summary (with axe, failed_reasons, etc.), return list of
    fix actions: [{ "type": "color_contrast", "applicable": bool }, ...].
    """
    actions: List[Dict[str, Any]] = []
    axe = summary.get("axe") or {}
    violations = axe.get("violations") or []
    violation_ids = [v.get("id") for v in violations if v.get("id")]
    failed_reasons = summary.get("failed_reasons") or []

    # color-contrast: applicable when axe reports it and we failed on serious/critical.
    has_serious_or_critical = (
        axe.get("serious", 0) > 0 or axe.get("critical", 0) > 0
    )
    has_color_contrast = "color-contrast" in violation_ids
    color_contrast_applicable = has_color_contrast and (
        has_serious_or_critical
        or any("Axe serious" in r or "Axe critical" in r for r in failed_reasons)
    )
    actions.append({"type": "color_contrast", "applicable": color_contrast_applicable})

    return actions


def apply_color_contrast_fix(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a new blueprint with tokens.colors merged to WCAG-AA safe values.
    Does not mutate the input.
    """
    out = copy.deepcopy(blueprint)
    tokens = out.get("tokens")
    if not isinstance(tokens, dict):
        out["tokens"] = {"colors": dict(WCAG_AA_SAFE_COLORS)}
        return out
    colors = tokens.get("colors") or {}
    if not isinstance(colors, dict):
        colors = {}
    merged = {**colors, **WCAG_AA_SAFE_COLORS}
    out["tokens"] = {**tokens, "colors": merged}
    return out
