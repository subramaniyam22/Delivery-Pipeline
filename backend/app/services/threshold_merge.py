"""
Pure merge of Decision Policies and PolicyConfig into global_thresholds for BUILD/QA gating.
No DB or heavy dependencies so it can be unit-tested without app/agent imports.
"""
from typing import Any, Dict


def merge_policy_config_into_thresholds(
    global_thresholds: Dict[str, Any], policy: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge PolicyConfig.value_json (Admin Policies UI) into thresholds.
    Keys: pass_threshold_percent, lighthouse_thresholds_json, axe_policy_json.
    """
    out = dict(global_thresholds)
    if policy.get("pass_threshold_percent") is not None:
        out["build_pass_score"] = int(policy["pass_threshold_percent"])
        out.setdefault("qa_pass_score", int(policy["pass_threshold_percent"]))
    lh = policy.get("lighthouse_thresholds_json")
    if isinstance(lh, dict):
        out.setdefault("lighthouse_min", {})
        for k in ("performance", "accessibility", "best_practices", "seo"):
            if k in lh and lh[k] is not None:
                v = lh[k]
                out["lighthouse_min"][k] = (
                    (v / 100.0) if (isinstance(v, (int, float)) and v > 1) else v
                )
    axe = policy.get("axe_policy_json")
    if isinstance(axe, dict):
        if "block" in axe:
            out["axe_block_severities"] = axe["block"]
        if axe.get("allow_medium_minor_if_total_under") is not None:
            out.setdefault("axe", {})["moderate_max"] = int(axe["allow_medium_minor_if_total_under"])
    return out


def merge_decision_policies_into_thresholds(
    global_thresholds: Dict[str, Any], dp: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge decision_policies_json (dp) into a copy of global_thresholds.
    Used by BUILD/QA to apply lighthouse_floor, lighthouse_target, axe_block_severities, axe_callout_max.
    """
    out = dict(global_thresholds)
    if "pass_threshold_overall" in dp:
        out.setdefault("build_pass_score", int(dp["pass_threshold_overall"]))
        out.setdefault("qa_pass_score", int(dp["pass_threshold_overall"]))
    if "qa_pass_rate_min" in dp:
        out.setdefault("qa_pass_score", int(dp["qa_pass_rate_min"]))
    if "lighthouse_floor" in dp and isinstance(dp["lighthouse_floor"], dict):
        floor = dp["lighthouse_floor"]
        out.setdefault("lighthouse_min", {})
        for k in ("performance", "accessibility", "best_practices", "seo"):
            if k in floor and floor[k] is not None:
                v = floor[k]
                out["lighthouse_min"][k] = (
                    (v / 100.0) if (isinstance(v, (int, float)) and v > 1) else v
                )
    if "lighthouse_target" in dp and isinstance(dp["lighthouse_target"], dict):
        target = dp["lighthouse_target"]
        out.setdefault("lighthouse_target", {})
        for k in ("performance", "accessibility", "best_practices", "seo"):
            if k in target and target[k] is not None:
                v = target[k]
                out["lighthouse_target"][k] = (
                    (v / 100.0) if (isinstance(v, (int, float)) and v > 1) else v
                )
    if "axe_block_severities" in dp:
        out["axe_block_severities"] = dp["axe_block_severities"]
    if dp.get("axe_callout_max") is not None:
        out.setdefault("axe", {})["moderate_max"] = int(dp["axe_callout_max"])
    return out
