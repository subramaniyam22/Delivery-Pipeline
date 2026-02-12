"""
Condition evaluator for HITL gates and other rule-based checks.
Supports path-based value lookup and ops: exists, ==, !=, >=, <=, >, <, contains, in.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_value_by_path(obj: Any, path: str) -> Any:
    """Safe navigation: get value at path like 'a.b.c'. Returns None if any segment missing."""
    if not path or obj is None:
        return None
    parts = path.strip().split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        part = part.strip()
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            try:
                idx = int(part)
                current = current[idx] if 0 <= idx < len(current) else None
            except ValueError:
                return None
        else:
            current = getattr(current, part, None)
    return current


def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition against context.
    condition: { "path": "stage_outputs.build.preview_url", "op": "exists" }
               { "path": "quality.lighthouse.accessibility", "op": ">=", "value": 90 }
    """
    if not condition or not isinstance(condition, dict):
        return True
    path = condition.get("path")
    op = (condition.get("op") or "exists").strip().lower()
    value = condition.get("value")
    actual = get_value_by_path(context, path) if path else None

    if op == "exists":
        return actual is not None and actual != ""
    if op == "!=":
        return actual != value
    if op == "==":
        return actual == value
    if op in (">=", "<=", ">", "<"):
        try:
            a, b = float(actual) if actual is not None else None, float(value) if value is not None else None
            if a is None or b is None:
                return False
            if op == ">=":
                return a >= b
            if op == "<=":
                return a <= b
            if op == ">":
                return a > b
            if op == "<":
                return a < b
        except (TypeError, ValueError):
            return False
    if op == "contains":
        if value is None:
            return False
        if isinstance(actual, (list, tuple)):
            return value in actual
        if isinstance(actual, str):
            return str(value) in actual
        return False
    if op == "in":
        if actual is None:
            return False
        if isinstance(value, (list, tuple)):
            return actual in value
        return False
    return True


def _condition_failure_summary(condition: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Human-readable summary of why a condition failed."""
    path = condition.get("path", "")
    op = (condition.get("op") or "exists").strip().lower()
    value = condition.get("value")
    actual = get_value_by_path(context, path) if path else None
    path_display = path or "?"
    if op == "exists":
        return f"{path_display} missing"
    if op in (">=", "<=", ">", "<"):
        return f"{path_display} ({actual}) {op} {value} failed"
    if op == "==":
        return f"{path_display} != {value}"
    if op == "!=":
        return f"{path_display} == {value}"
    return f"Condition on {path_display} failed"


def evaluate_conditions_json(
    conditions_json: Optional[Dict[str, Any]],
    context: Dict[str, Any],
) -> tuple[bool, List[str]]:
    """
    Evaluate conditions_json with "all" and "any" nesting.
    Returns (passed: bool, failure_reasons: list). If conditions_json missing -> (True, []).
    """
    if not conditions_json:
        return True, []

    reasons: List[str] = []

    def _eval(node: Any) -> bool:
        if node is None:
            return True
        if isinstance(node, dict):
            if "all" in node:
                children = node["all"]
                if not isinstance(children, list):
                    return True
                for c in children:
                    if not _eval(c):
                        if isinstance(c, dict) and "path" in c:
                            reasons.append(_condition_failure_summary(c, context))
                        return False
                return True
            if "any" in node:
                children = node["any"]
                if not isinstance(children, list):
                    return True
                for c in children:
                    if _eval(c):
                        return True
                if children and isinstance(children[0], dict) and "path" in children[0]:
                    reasons.append(_condition_failure_summary(children[0], context))
                return False
            # single condition
            passed = evaluate_condition(node, context)
            if not passed:
                reasons.append(_condition_failure_summary(node, context))
            return passed
        return True

    passed = _eval(conditions_json)
    return passed, reasons
