from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any, Mapping

from .engine import evaluate
from .matcher import condition_matches
from .model import DecisionTable, Rule


EXPLAIN_FORMAT_VERSION = 1


def explain_table(
    table: DecisionTable,
    facts: Mapping[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    evaluation_date = _parse_date(as_of) if as_of is not None else None
    traces: list[dict[str, Any]] = []

    for rule in _ordered_rules(table):
        effective = _effective(rule, evaluation_date)
        conditions: list[dict[str, Any]] = []
        for name, condition in rule.when.items():
            present = name in facts
            value = facts.get(name)
            matched = condition_matches(condition, value, present=present)
            conditions.append({
                "input": name,
                "condition": condition,
                "present": present,
                "value": value,
                "matched": matched,
            })

        condition_match = all(item["matched"] for item in conditions)
        traces.append({
            "id": rule.id,
            "priority": rule.priority,
            "effective": effective,
            "conditions_matched": condition_match,
            "matched": effective and condition_match,
            "conditions": conditions,
        })

    evaluation_error: str | None = None
    result: dict[str, Any] | None = None
    try:
        decision = evaluate(table, facts, as_of=as_of)
        result = asdict(decision)
        selected = set(decision.matched_rule_ids)
    except ValueError as exc:
        evaluation_error = str(exc)
        selected = set()

    for trace in traces:
        trace["selected"] = trace["id"] in selected

    return {
        "format_version": EXPLAIN_FORMAT_VERSION,
        "table_id": table.id,
        "facts": dict(facts),
        "as_of": as_of,
        "rules": traces,
        "result": result,
        "evaluation_error": evaluation_error,
    }


def _ordered_rules(table: DecisionTable) -> tuple[Rule, ...]:
    ordered = sorted(
        enumerate(table.rules),
        key=lambda pair: (pair[1].priority is None, pair[1].priority or 0, pair[0]),
    )
    return tuple(rule for _, rule in ordered)


def _effective(rule: Rule, evaluation_date: date | None) -> bool:
    if rule.effective_from is None and rule.effective_to is None:
        return True
    if evaluation_date is None:
        raise ValueError(
            f"Rule {rule.id!r} has effective dates; pass an explicit as_of date for deterministic explanation"
        )
    if rule.effective_from is not None and evaluation_date < _parse_date(rule.effective_from):
        return False
    if rule.effective_to is not None and evaluation_date > _parse_date(rule.effective_to):
        return False
    return True


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date {value!r}; expected YYYY-MM-DD") from exc
