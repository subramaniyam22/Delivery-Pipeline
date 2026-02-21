"""
Unit tests for Decision Policies → BUILD/QA thresholds merge.
Uses only app.services.threshold_merge (no DB, no agents) so tests run without
pydantic/langsmith or SQLite UUID issues.
"""
import pytest

from app.services.threshold_merge import merge_decision_policies_into_thresholds


def test_merge_empty_dp_leaves_thresholds_unchanged():
    base = {"build_pass_score": 90}
    out = merge_decision_policies_into_thresholds(base, {})
    assert out == {"build_pass_score": 90}


def test_merge_lighthouse_floor_normalizes_percent():
    base = {}
    dp = {
        "lighthouse_floor": {
            "performance": 80,
            "accessibility": 90,
            "best_practices": 85,
            "seo": 70,
        }
    }
    out = merge_decision_policies_into_thresholds(base, dp)
    assert out["lighthouse_min"]["performance"] == 0.8
    assert out["lighthouse_min"]["accessibility"] == 0.9
    assert out["lighthouse_min"]["best_practices"] == 0.85
    assert out["lighthouse_min"]["seo"] == 0.7


def test_merge_lighthouse_floor_already_0_1_unchanged():
    base = {}
    dp = {"lighthouse_floor": {"performance": 0.75}}
    out = merge_decision_policies_into_thresholds(base, dp)
    assert out["lighthouse_min"]["performance"] == 0.75


def test_merge_axe_block_severities_and_callout_max():
    base = {}
    dp = {
        "axe_block_severities": ["critical", "serious"],
        "axe_callout_max": 5,
    }
    out = merge_decision_policies_into_thresholds(base, dp)
    assert out["axe_block_severities"] == ["critical", "serious"]
    assert out["axe"]["moderate_max"] == 5


def test_merge_axe_callout_max_none_not_set():
    base = {}
    dp = {"axe_block_severities": ["critical"]}
    out = merge_decision_policies_into_thresholds(base, dp)
    assert "axe" not in out or "moderate_max" not in out.get("axe", {})


def test_merge_pass_threshold_and_qa_pass_rate():
    base = {}
    dp = {"pass_threshold_overall": 95}
    out = merge_decision_policies_into_thresholds(base, dp)
    assert out["build_pass_score"] == 95
    assert out["qa_pass_score"] == 95
    base2 = {}
    dp2 = {"qa_pass_rate_min": 98}
    out2 = merge_decision_policies_into_thresholds(base2, dp2)
    assert out2["qa_pass_score"] == 98


def test_merge_does_not_mutate_input():
    base = {"build_pass_score": 90}
    dp = {"lighthouse_floor": {"performance": 80}}
    out = merge_decision_policies_into_thresholds(base, dp)
    assert base == {"build_pass_score": 90}
    assert out["build_pass_score"] == 90
    assert out["lighthouse_min"]["performance"] == 0.8
