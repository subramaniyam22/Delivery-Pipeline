"""
Unit tests for pipeline state machine: stage order, transitions, get_next_stage, can_transition.
"""
import pytest
from types import SimpleNamespace

from app.pipeline.state_machine import (
    STAGE_ORDER,
    VALID_NEXT,
    can_transition,
    get_next_stage,
    is_autopilot_eligible,
)
from app.models import Stage, ProjectStatus


# --- Pure logic (no DB) ---


def test_stage_order_is_complete():
    assert len(STAGE_ORDER) == 7
    assert STAGE_ORDER[0] == Stage.SALES
    assert STAGE_ORDER[-1] == Stage.COMPLETE
    assert Stage.ONBOARDING in STAGE_ORDER
    assert Stage.BUILD in STAGE_ORDER


def test_get_next_stage_success_path():
    assert get_next_stage(Stage.SALES, success=True, rework=False) == Stage.ONBOARDING
    assert get_next_stage(Stage.ONBOARDING, success=True, rework=False) == Stage.ASSIGNMENT
    assert get_next_stage(Stage.ASSIGNMENT, success=True, rework=False) == Stage.BUILD
    assert get_next_stage(Stage.BUILD, success=True, rework=False) == Stage.TEST
    assert get_next_stage(Stage.TEST, success=True, rework=False) == Stage.DEFECT_VALIDATION
    assert get_next_stage(Stage.DEFECT_VALIDATION, success=True, rework=False) == Stage.COMPLETE
    assert get_next_stage(Stage.COMPLETE, success=True, rework=False) is None


def test_get_next_stage_rework_path():
    assert get_next_stage(Stage.TEST, success=False, rework=True) == Stage.BUILD
    assert get_next_stage(Stage.DEFECT_VALIDATION, success=False, rework=True) == Stage.BUILD


def test_can_transition_valid():
    assert can_transition(Stage.SALES, Stage.ONBOARDING) is True
    assert can_transition(Stage.ONBOARDING, Stage.ASSIGNMENT) is True
    assert can_transition(Stage.BUILD, Stage.TEST) is True
    assert can_transition(Stage.DEFECT_VALIDATION, Stage.COMPLETE) is True
    assert can_transition(Stage.DEFECT_VALIDATION, Stage.BUILD) is True


def test_can_transition_invalid():
    assert can_transition(Stage.SALES, Stage.BUILD) is False
    assert can_transition(Stage.ONBOARDING, Stage.COMPLETE) is False
    assert can_transition(Stage.COMPLETE, Stage.BUILD) is False
    assert can_transition(Stage.BUILD, Stage.ONBOARDING) is False


def test_can_transition_from_none():
    assert can_transition(None, Stage.SALES) is True
    assert can_transition(None, Stage.ONBOARDING) is True


def test_is_autopilot_eligible_active():
    p = SimpleNamespace(status=ProjectStatus.ACTIVE, current_stage=Stage.BUILD)
    assert is_autopilot_eligible(p) is True


def test_is_autopilot_eligible_hold():
    p = SimpleNamespace(status=ProjectStatus.HOLD, current_stage=Stage.ONBOARDING)
    assert is_autopilot_eligible(p) is False


def test_is_autopilot_eligible_needs_review():
    p = SimpleNamespace(status=ProjectStatus.NEEDS_REVIEW, current_stage=Stage.BUILD)
    assert is_autopilot_eligible(p) is False


def test_valid_next_defect_validation_has_two_options():
    assert Stage.COMPLETE in VALID_NEXT[Stage.DEFECT_VALIDATION]
    assert Stage.BUILD in VALID_NEXT[Stage.DEFECT_VALIDATION]
    assert len(VALID_NEXT[Stage.DEFECT_VALIDATION]) == 2
