from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any, Mapping

from .model import DecisionTable, Rule


@dataclass(frozen=True)
class RuleRelation:
    first_rule_id: str
    second_rule_id: str
    first_index: int
    second_index: int
    dimensions: tuple[str, ...]


@dataclass(frozen=True)
class _Constraint:
    kind: str
    values: tuple[Any, ...] = ()
    lower: Real | None = None
    lower_inclusive: bool = False
    upper: Real | None = None
    upper_inclusive: bool = False


_UNIVERSAL = _Constraint("universal")
_PRESENT_ANY = _Constraint("present_any")
_MISSING_ONLY = _Constraint("missing_only")
_EMPTY = _Constraint("empty")
_UNKNOWN = _Constraint("unknown")


def find_proven_overlaps(table: DecisionTable) -> tuple[RuleRelation, ...]:
    """Return non-identical rule pairs that are provably able to match together.

    Unsupported constructs such as regex and exclusions yield an unknown relation and
    are deliberately not reported as overlaps. False positives are worse than missed
    proofs for a merge-gate validator.
    """
    relations: list[RuleRelation] = []
    for first_index, first in enumerate(table.rules):
        for second_index in range(first_index + 1, len(table.rules)):
            second = table.rules[second_index]
            if first.when == second.when:
                continue
            overlap = rules_overlap(first, second, table.input_names)
            if overlap is True:
                relations.append(RuleRelation(
                    first_rule_id=first.id,
                    second_rule_id=second.id,
                    first_index=first_index,
                    second_index=second_index,
                    dimensions=_relation_dimensions(first.when, second.when, table.input_names),
                ))
    return tuple(relations)


def find_shadowed_rules(table: DecisionTable) -> tuple[RuleRelation, ...]:
    """Return later FIRST-policy rules whose match set is provably contained by an earlier rule."""
    if table.hit_policy != "first":
        return ()

    ordered = sorted(
        enumerate(table.rules),
        key=lambda pair: (pair[1].priority is None, pair[1].priority or 0, pair[0]),
    )
    relations: list[RuleRelation] = []
    for position, (later_index, later) in enumerate(ordered):
        for earlier_index, earlier in ordered[:position]:
            contained = rule_contains(earlier, later, table.input_names)
            if contained is True:
                relations.append(RuleRelation(
                    first_rule_id=earlier.id,
                    second_rule_id=later.id,
                    first_index=earlier_index,
                    second_index=later_index,
                    dimensions=_relation_dimensions(earlier.when, later.when, table.input_names),
                ))
                break
    return tuple(relations)


def rules_overlap(first: Rule, second: Rule, input_names: tuple[str, ...]) -> bool | None:
    unknown = False
    for name in input_names:
        left = _constraint(first.when.get(name, _ABSENT))
        right = _constraint(second.when.get(name, _ABSENT))
        relation = _constraints_overlap(left, right)
        if relation is False:
            return False
        if relation is None:
            unknown = True
    return None if unknown else True


def rule_contains(outer: Rule, inner: Rule, input_names: tuple[str, ...]) -> bool | None:
    unknown = False
    for name in input_names:
        outer_constraint = _constraint(outer.when.get(name, _ABSENT))
        inner_constraint = _constraint(inner.when.get(name, _ABSENT))
        relation = _constraint_contains(outer_constraint, inner_constraint)
        if relation is False:
            return False
        if relation is None:
            unknown = True
    return None if unknown else True


class _Absent:
    pass


_ABSENT = _Absent()


def _constraint(condition: Any) -> _Constraint:
    if isinstance(condition, _Absent):
        return _UNIVERSAL
    if condition == "*":
        return _PRESENT_ANY
    if isinstance(condition, (list, tuple)):
        return _finite(condition)
    if isinstance(condition, Mapping):
        return _mapping_constraint(condition)
    return _finite((condition,))


def _mapping_constraint(condition: Mapping[str, Any]) -> _Constraint:
    keys = set(condition)
    if keys & {"regex", "ne", "not_in"}:
        return _UNKNOWN

    exists = condition.get("exists", _ABSENT)
    other = {key: value for key, value in condition.items() if key != "exists"}
    if not isinstance(exists, _Absent):
        if not isinstance(exists, bool):
            return _UNKNOWN
        if exists is False:
            return _MISSING_ONLY if not other else _EMPTY
        if not other:
            return _PRESENT_ANY

    allowed = {"eq", "in", "gt", "gte", "lt", "lte", "between"}
    if not set(other) <= allowed:
        return _UNKNOWN

    finite_values: tuple[Any, ...] | None = None
    if "eq" in other:
        finite_values = (other["eq"],)
    if "in" in other:
        raw = other["in"]
        if not isinstance(raw, (list, tuple)):
            return _UNKNOWN
        values = tuple(raw)
        finite_values = values if finite_values is None else tuple(
            value for value in finite_values if _contains_equal(values, value)
        )

    interval = _interval_from_operators(other)
    if interval is _UNKNOWN:
        return _UNKNOWN
    if interval is _EMPTY:
        return _EMPTY

    if finite_values is not None:
        if isinstance(interval, _Constraint) and interval.kind == "interval":
            filtered: list[Any] = []
            for value in finite_values:
                membership = _value_in_interval(value, interval)
                if membership is None:
                    return _UNKNOWN
                if membership:
                    filtered.append(value)
            return _finite(filtered)
        return _finite(finite_values)

    if isinstance(interval, _Constraint):
        return interval
    return _PRESENT_ANY


def _interval_from_operators(condition: Mapping[str, Any]) -> _Constraint | object | None:
    has_range = any(key in condition for key in ("gt", "gte", "lt", "lte", "between"))
    if not has_range:
        return None

    lower: Real | None = None
    lower_inclusive = False
    upper: Real | None = None
    upper_inclusive = False

    def set_lower(value: Any, inclusive: bool) -> bool:
        nonlocal lower, lower_inclusive
        if not _is_number(value):
            return False
        if lower is None or value > lower or (value == lower and not inclusive and lower_inclusive):
            lower = value
            lower_inclusive = inclusive
        elif value == lower:
            lower_inclusive = lower_inclusive and inclusive
        return True

    def set_upper(value: Any, inclusive: bool) -> bool:
        nonlocal upper, upper_inclusive
        if not _is_number(value):
            return False
        if upper is None or value < upper or (value == upper and not inclusive and upper_inclusive):
            upper = value
            upper_inclusive = inclusive
        elif value == upper:
            upper_inclusive = upper_inclusive and inclusive
        return True

    if "gt" in condition and not set_lower(condition["gt"], False):
        return _UNKNOWN
    if "gte" in condition and not set_lower(condition["gte"], True):
        return _UNKNOWN
    if "lt" in condition and not set_upper(condition["lt"], False):
        return _UNKNOWN
    if "lte" in condition and not set_upper(condition["lte"], True):
        return _UNKNOWN
    if "between" in condition:
        raw = condition["between"]
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            return _UNKNOWN
        if not set_lower(raw[0], True) or not set_upper(raw[1], True):
            return _UNKNOWN

    if lower is not None and upper is not None:
        if lower > upper:
            return _EMPTY
        if lower == upper and not (lower_inclusive and upper_inclusive):
            return _EMPTY
    return _Constraint("interval", lower=lower, lower_inclusive=lower_inclusive, upper=upper, upper_inclusive=upper_inclusive)


def _finite(values: Any) -> _Constraint:
    unique: list[Any] = []
    for value in values:
        if not _contains_equal(unique, value):
            unique.append(value)
    if not unique:
        return _EMPTY
    return _Constraint("finite", values=tuple(unique))


def _constraints_overlap(left: _Constraint, right: _Constraint) -> bool | None:
    if left.kind == "empty" or right.kind == "empty":
        return False
    if left.kind == "unknown" or right.kind == "unknown":
        return None
    if left.kind == "universal" or right.kind == "universal":
        return True
    if left.kind == "missing_only" or right.kind == "missing_only":
        return left.kind == right.kind
    if left.kind == "present_any" or right.kind == "present_any":
        return True
    if left.kind == "finite" and right.kind == "finite":
        return any(_contains_equal(right.values, value) for value in left.values)
    if left.kind == "finite" and right.kind == "interval":
        return _finite_interval_overlap(left, right)
    if left.kind == "interval" and right.kind == "finite":
        return _finite_interval_overlap(right, left)
    if left.kind == "interval" and right.kind == "interval":
        return _intervals_overlap(left, right)
    return None


def _constraint_contains(outer: _Constraint, inner: _Constraint) -> bool | None:
    if inner.kind == "empty":
        return True
    if outer.kind == "universal":
        return True
    if outer.kind == "empty":
        return False
    if outer.kind == "unknown" or inner.kind == "unknown":
        return None
    if inner.kind == "universal":
        return outer.kind == "universal"
    if outer.kind == "present_any":
        return inner.kind in {"present_any", "finite", "interval"}
    if outer.kind == "missing_only":
        return inner.kind == "missing_only"
    if inner.kind == "missing_only":
        return False
    if outer.kind == "finite" and inner.kind == "finite":
        return all(_contains_equal(outer.values, value) for value in inner.values)
    if outer.kind == "interval" and inner.kind == "finite":
        for value in inner.values:
            membership = _value_in_interval(value, outer)
            if membership is None:
                return None
            if not membership:
                return False
        return True
    if outer.kind == "finite" and inner.kind == "interval":
        point = _interval_single_point(inner)
        return point is not _NO_POINT and _contains_equal(outer.values, point)
    if outer.kind == "interval" and inner.kind == "interval":
        return _interval_contains(outer, inner)
    return False


def _finite_interval_overlap(finite: _Constraint, interval: _Constraint) -> bool | None:
    unknown = False
    for value in finite.values:
        membership = _value_in_interval(value, interval)
        if membership is True:
            return True
        if membership is None:
            unknown = True
    return None if unknown else False


def _value_in_interval(value: Any, interval: _Constraint) -> bool | None:
    if not _is_number(value):
        return None
    if interval.lower is not None:
        if value < interval.lower or (value == interval.lower and not interval.lower_inclusive):
            return False
    if interval.upper is not None:
        if value > interval.upper or (value == interval.upper and not interval.upper_inclusive):
            return False
    return True


def _intervals_overlap(left: _Constraint, right: _Constraint) -> bool:
    if left.upper is not None and right.lower is not None:
        if left.upper < right.lower:
            return False
        if left.upper == right.lower and not (left.upper_inclusive and right.lower_inclusive):
            return False
    if right.upper is not None and left.lower is not None:
        if right.upper < left.lower:
            return False
        if right.upper == left.lower and not (right.upper_inclusive and left.lower_inclusive):
            return False
    return True


def _interval_contains(outer: _Constraint, inner: _Constraint) -> bool:
    if outer.lower is not None:
        if inner.lower is None or inner.lower < outer.lower:
            return False
        if inner.lower == outer.lower and inner.lower_inclusive and not outer.lower_inclusive:
            return False
    if outer.upper is not None:
        if inner.upper is None or inner.upper > outer.upper:
            return False
        if inner.upper == outer.upper and inner.upper_inclusive and not outer.upper_inclusive:
            return False
    return True


class _NoPoint:
    pass


_NO_POINT = _NoPoint()


def _interval_single_point(interval: _Constraint) -> Any:
    if (
        interval.lower is not None
        and interval.upper is not None
        and interval.lower == interval.upper
        and interval.lower_inclusive
        and interval.upper_inclusive
    ):
        return interval.lower
    return _NO_POINT


def _relation_dimensions(first: Mapping[str, Any], second: Mapping[str, Any], input_names: tuple[str, ...]) -> tuple[str, ...]:
    dimensions = [
        name
        for name in input_names
        if first.get(name, _ABSENT) != second.get(name, _ABSENT)
        and (name in first or name in second)
    ]
    return tuple(dimensions)


def _contains_equal(values: Any, target: Any) -> bool:
    return any(value == target for value in values)


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)
