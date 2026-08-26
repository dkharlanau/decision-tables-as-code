from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_OPERATOR_KEYS = {"eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte", "between", "exists", "regex"}


def condition_matches(condition: Any, value: Any, *, present: bool = True) -> bool:
    """Evaluate one condition against a value.

    Scalars are equality checks. Lists mean membership. A literal "*" matches any
    present value. Mapping conditions compose supported operators with AND logic.
    """
    if condition == "*":
        return present
    if isinstance(condition, Mapping):
        unknown = set(condition) - _OPERATOR_KEYS
        if unknown:
            raise ValueError(f"Unsupported condition operators: {', '.join(sorted(unknown))}")
        return all(_operator_matches(op, expected, value, present) for op, expected in condition.items())
    if isinstance(condition, Sequence) and not isinstance(condition, (str, bytes, bytearray)):
        return value in condition
    return value == condition


def _operator_matches(operator: str, expected: Any, value: Any, present: bool) -> bool:
    if operator == "exists":
        return present is bool(expected)
    if not present:
        return False
    if operator == "eq":
        return value == expected
    if operator == "ne":
        return value != expected
    if operator == "in":
        return value in expected
    if operator == "not_in":
        return value not in expected
    if operator == "gt":
        return value > expected
    if operator == "gte":
        return value >= expected
    if operator == "lt":
        return value < expected
    if operator == "lte":
        return value <= expected
    if operator == "between":
        if not isinstance(expected, Sequence) or isinstance(expected, (str, bytes)) or len(expected) != 2:
            raise ValueError("between requires [minimum, maximum]")
        return expected[0] <= value <= expected[1]
    if operator == "regex":
        return re.fullmatch(str(expected), str(value)) is not None
    raise ValueError(f"Unsupported condition operator: {operator}")


def rule_matches(conditions: Mapping[str, Any], facts: Mapping[str, Any]) -> bool:
    for name, condition in conditions.items():
        present = name in facts
        value = facts.get(name)
        if not condition_matches(condition, value, present=present):
            return False
    return True
