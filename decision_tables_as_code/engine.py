from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from .matcher import rule_matches
from .model import DecisionTable, Rule


@dataclass(frozen=True)
class DecisionResult:
    table_id: str
    matched_rule_ids: tuple[str, ...]
    outputs: Any


def matching_rules(
    table: DecisionTable,
    facts: Mapping[str, Any],
    *,
    as_of: str | date | datetime | None = None,
) -> tuple[Rule, ...]:
    evaluation_date = _coerce_date(as_of) if as_of is not None else None
    ordered = sorted(
        enumerate(table.rules),
        key=lambda pair: (pair[1].priority is None, pair[1].priority or 0, pair[0]),
    )
    return tuple(
        rule
        for _, rule in ordered
        if _rule_is_effective(rule, evaluation_date) and rule_matches(rule.when, facts)
    )


def evaluate(
    table: DecisionTable,
    facts: Mapping[str, Any],
    *,
    as_of: str | date | datetime | None = None,
) -> DecisionResult:
    matches = matching_rules(table, facts, as_of=as_of)

    if table.hit_policy == "first":
        selected = matches[:1]
        outputs: Any = dict(selected[0].then) if selected else None
    elif table.hit_policy == "unique":
        if len(matches) > 1:
            ids = ", ".join(rule.id for rule in matches)
            raise ValueError(f"UNIQUE hit policy violated; matched rules: {ids}")
        selected = matches
        outputs = dict(selected[0].then) if selected else None
    elif table.hit_policy == "collect":
        selected = matches
        outputs = [dict(rule.then) for rule in selected]
    else:
        raise ValueError(f"Unsupported hit policy: {table.hit_policy}")

    return DecisionResult(
        table_id=table.id,
        matched_rule_ids=tuple(rule.id for rule in selected),
        outputs=outputs,
    )


def _rule_is_effective(rule: Rule, evaluation_date: date | None) -> bool:
    if rule.effective_from is None and rule.effective_to is None:
        return True
    if evaluation_date is None:
        raise ValueError(
            f"Rule {rule.id!r} has effective dates; pass an explicit as_of date for deterministic evaluation"
        )
    if rule.effective_from is not None and evaluation_date < _coerce_date(rule.effective_from):
        return False
    if rule.effective_to is not None and evaluation_date > _coerce_date(rule.effective_to):
        return False
    return True


def _coerce_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO date {value!r}; expected YYYY-MM-DD") from exc
    raise TypeError("as_of must be an ISO date string, date, or datetime")
