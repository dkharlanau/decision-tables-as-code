from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .model import DecisionTable
from .validate import validate_table


INSPECT_FORMAT_VERSION = 1


def inspect_table(table: DecisionTable) -> dict[str, Any]:
    diagnostics = validate_table(table)
    operators = sorted({
        operator
        for rule in table.rules
        for condition in rule.when.values()
        for operator in _condition_operators(condition)
    })

    governed_rules = sum(
        1
        for rule in table.rules
        if any((rule.owner, rule.source, rule.ticket, rule.rationale, rule.metadata))
    )
    effective_dated_rules = sum(
        1 for rule in table.rules if rule.effective_from is not None or rule.effective_to is not None
    )

    severity_counts: dict[str, int] = {}
    for item in diagnostics:
        severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1

    return {
        "format_version": INSPECT_FORMAT_VERSION,
        "table": {
            "id": table.id,
            "name": table.name,
            "version": table.version,
            "hit_policy": table.hit_policy,
            "description": table.description,
            "metadata": dict(table.metadata),
        },
        "contract": {
            "inputs": [asdict(item) for item in table.inputs],
            "outputs": [asdict(item) for item in table.outputs],
        },
        "rules": {
            "count": len(table.rules),
            "ids": [rule.id for rule in table.rules],
            "with_priority": sum(1 for rule in table.rules if rule.priority is not None),
            "with_governance": governed_rules,
            "effective_dated": effective_dated_rules,
            "operators": operators,
        },
        "diagnostics": {
            "count": len(diagnostics),
            "by_severity": severity_counts,
            "findings": [item.to_dict() for item in diagnostics],
        },
    }


def _condition_operators(condition: Any) -> tuple[str, ...]:
    if condition == "*":
        return ("present",)
    if isinstance(condition, (list, tuple)):
        return ("in",)
    if isinstance(condition, Mapping):
        return tuple(sorted(str(key) for key in condition))
    return ("eq",)
