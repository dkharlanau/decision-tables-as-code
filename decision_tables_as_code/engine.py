from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .matcher import rule_matches
from .model import DecisionTable, Rule


@dataclass(frozen=True)
class DecisionResult:
    table_id: str
    matched_rule_ids: tuple[str, ...]
    outputs: Any


def matching_rules(table: DecisionTable, facts: Mapping[str, Any]) -> tuple[Rule, ...]:
    ordered = sorted(
        enumerate(table.rules),
        key=lambda pair: (pair[1].priority is None, pair[1].priority or 0, pair[0]),
    )
    return tuple(rule for _, rule in ordered if rule_matches(rule.when, facts))


def evaluate(table: DecisionTable, facts: Mapping[str, Any]) -> DecisionResult:
    matches = matching_rules(table, facts)

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
