"""
Minimal tests for HITL gates: condition evaluator and gate resolution.
Scenario A/B/C/D are documented in prompt; these tests cover resolution and condition logic.
"""
import pytest

from app.services.conditions import (
    get_value_by_path,
    evaluate_condition,
    evaluate_conditions_json,
)
from app.services.hitl_service import (
    resolve_gate_for_stage,
    should_require_approval,
)


class TestConditions:
    def test_get_value_by_path(self):
        obj = {"a": {"b": {"c": 1}}}
        assert get_value_by_path(obj, "a.b.c") == 1
        assert get_value_by_path(obj, "a.b.x") is None
        assert get_value_by_path(obj, "a.b") == {"c": 1}

    def test_evaluate_condition_exists(self):
        ctx = {"stage_outputs": {"build": {"preview_url": "https://x.com"}}}
        assert evaluate_condition({"path": "stage_outputs.build.preview_url", "op": "exists"}, ctx) is True
        assert evaluate_condition({"path": "stage_outputs.build.missing", "op": "exists"}, ctx) is False

    def test_evaluate_condition_gte(self):
        ctx = {"quality": {"lighthouse": {"accessibility": 95}}}
        assert evaluate_condition(
            {"path": "quality.lighthouse.accessibility", "op": ">=", "value": 90},
            ctx,
        ) is True
        assert evaluate_condition(
            {"path": "quality.lighthouse.accessibility", "op": ">=", "value": 100},
            ctx,
        ) is False

    def test_evaluate_conditions_json_all(self):
        ctx = {"project": {"consultant_user_id": "u1"}}
        conditions = {"all": [{"path": "project.consultant_user_id", "op": "exists"}]}
        passed, reasons = evaluate_conditions_json(conditions, ctx)
        assert passed is True
        assert reasons == []

    def test_evaluate_conditions_json_fail(self):
        ctx = {"project": {"consultant_user_id": None}}
        conditions = {"all": [{"path": "project.consultant_user_id", "op": "exists"}]}
        passed, reasons = evaluate_conditions_json(conditions, ctx)
        assert passed is False
        assert len(reasons) >= 1


class TestHitlResolution:
    def test_resolve_gate_project_override_wins(self):
        global_rules = [{"stage_key": "2_assignment", "mode": "always", "approver_roles": ["admin"]}]
        project_rules = [{"stage_key": "2_assignment", "mode": "never"}]
        gate = resolve_gate_for_stage("2_assignment", global_rules, project_rules)
        assert gate["mode"] == "never"

    def test_resolve_gate_global_used(self):
        global_rules = [{"stage_key": "2_assignment", "mode": "always", "approver_roles": ["manager"]}]
        gate = resolve_gate_for_stage("2_assignment", global_rules, [])
        assert gate["mode"] == "always"

    def test_resolve_gate_implicit_never(self):
        gate = resolve_gate_for_stage("3_build", [], [])
        assert gate["mode"] == "never"

    def test_should_require_approval_never(self):
        required, _ = should_require_approval({"mode": "never"}, {})
        assert required is False

    def test_should_require_approval_always(self):
        required, reasons = should_require_approval({"mode": "always"}, {})
        assert required is True
        assert "Approval required by policy" in reasons[0]

    def test_should_require_approval_conditional_pass(self):
        ctx = {"project": {"consultant_user_id": "u1"}}
        rule = {"mode": "conditional", "conditions_json": {"all": [{"path": "project.consultant_user_id", "op": "exists"}]}}
        required, _ = should_require_approval(rule, ctx)
        assert required is False

    def test_should_require_approval_conditional_fail(self):
        ctx = {"project": {"consultant_user_id": None}}
        rule = {"mode": "conditional", "conditions_json": {"all": [{"path": "project.consultant_user_id", "op": "exists"}]}}
        required, reasons = should_require_approval(rule, ctx)
        assert required is True
        assert any("Gate conditions failed" in r for r in reasons)

    def test_full_autopilot_conditional_ignored(self):
        rule = {"mode": "conditional", "conditions_json": {"all": [{"path": "x", "op": "exists"}]}}
        required, _ = should_require_approval(rule, {}, autopilot_mode="full")
        assert required is False

    def test_full_autopilot_always_respected(self):
        required, _ = should_require_approval({"mode": "always"}, {}, autopilot_mode="full")
        assert required is True
