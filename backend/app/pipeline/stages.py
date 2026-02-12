"""
Pipeline stage definitions. Stage keys align with Stage enum (0..6) plus placeholders 7..12.
Minimal readiness rules for Prompt 1: only 0_onboarding and 1_assignment; rest blocked.
"""
from typing import Any, Dict, List

from app.models import Stage

# Order matches Stage enum: SALES=0, ONBOARDING=1, ASSIGNMENT=2, BUILD=3, TEST=4, DEFECT_VALIDATION=5, COMPLETE=6
_STAGE_ORDER = [
    Stage.SALES,
    Stage.ONBOARDING,
    Stage.ASSIGNMENT,
    Stage.BUILD,
    Stage.TEST,
    Stage.DEFECT_VALIDATION,
    Stage.COMPLETE,
]

STAGES: List[Dict[str, Any]] = [
    {"key": "0_sales", "order": 0, "label": "Sales", "stage": Stage.SALES},
    {"key": "1_onboarding", "order": 1, "label": "Onboarding", "stage": Stage.ONBOARDING},
    {"key": "2_assignment", "order": 2, "label": "Assignment", "stage": Stage.ASSIGNMENT},
    {"key": "3_build", "order": 3, "label": "Build", "stage": Stage.BUILD},
    {"key": "4_test", "order": 4, "label": "Test", "stage": Stage.TEST},
    {"key": "5_defect_validation", "order": 5, "label": "Defect Validation", "stage": Stage.DEFECT_VALIDATION},
    {"key": "6_complete", "order": 6, "label": "Complete", "stage": Stage.COMPLETE},
    {"key": "7_reserved", "order": 7, "label": "Reserved", "stage": None},
    {"key": "8_reserved", "order": 8, "label": "Reserved", "stage": None},
    {"key": "9_reserved", "order": 9, "label": "Reserved", "stage": None},
    {"key": "10_reserved", "order": 10, "label": "Reserved", "stage": None},
    {"key": "11_reserved", "order": 11, "label": "Reserved", "stage": None},
    {"key": "12_reserved", "order": 12, "label": "Reserved", "stage": None},
]

STAGE_KEY_TO_ORDER = {s["key"]: s["order"] for s in STAGES}
STAGE_KEY_TO_STAGE = {s["key"]: s["stage"] for s in STAGES if s.get("stage") is not None}
# Map Stage enum to stage_key for worker/orchestrator
STAGE_TO_KEY = {s["stage"]: s["key"] for s in STAGES if s.get("stage") is not None}

# Stages that have minimal gates implemented (onboarding, assignment, build with template validation)
GATES_IMPLEMENTED_KEYS = {"1_onboarding", "2_assignment", "3_build"}
BLOCKED_REASON_NOT_IMPLEMENTED = "Stage gates not enabled yet (Prompt 7 will implement full 0–12 readiness rules)."
