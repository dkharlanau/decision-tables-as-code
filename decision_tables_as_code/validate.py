from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from .matcher import condition_matches
from .model import DecisionTable, SUPPORTED_HIT_POLICIES, SUPPORTED_TYPES
from .overlap import find_proven_overlaps, find_shadowed_rules


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def validate_table(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if table.version != 1:
        diagnostics.append(Diagnostic("DT001", "error", f"Unsupported format version {table.version}", "version"))
    if table.hit_policy not in SUPPORTED_HIT_POLICIES:
        diagnostics.append(Diagnostic("DT002", "error", f"Unsupported hit policy {table.hit_policy!r}", "hit_policy"))
    if not table.inputs:
        diagnostics.append(Diagnostic("DT003", "error", "At least one input is required", "inputs"))
    if not table.outputs:
        diagnostics.append(Diagnostic("DT004", "error", "At least one output is required", "outputs"))
    if not table.rules:
        diagnostics.append(Diagnostic("DT005", "warning", "Decision table has no rules", "rules"))

    diagnostics.extend(_duplicate_name_diagnostics(table))
    diagnostics.extend(_type_diagnostics(table))
    diagnostics.extend(_rule_diagnostics(table))
    diagnostics.extend(_duplicate_and_conflict_diagnostics(table))
    diagnostics.extend(_condition_shape_diagnostics(table))
    diagnostics.extend(_relationship_diagnostics(table))
    return diagnostics


def has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(item.severity == "error" for item in diagnostics)


def _duplicate_name_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for kind, values in (("input", table.input_names), ("output", table.output_names)):
        seen: set[str] = set()
        for index, value in enumerate(values):
            if value in seen:
                diagnostics.append(Diagnostic("DT010", "error", f"Duplicate {kind} name {value!r}", f"{kind}s[{index}].name"))
            seen.add(value)
    return diagnostics


def _type_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for collection, items in (("inputs", table.inputs), ("outputs", table.outputs)):
        for index, item in enumerate(items):
            if item.type not in SUPPORTED_TYPES:
                diagnostics.append(Diagnostic("DT011", "error", f"Unsupported type {item.type!r}", f"{collection}[{index}].type"))
    return diagnostics


def _rule_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    input_names = set(table.input_names)
    output_names = set(table.output_names)
    seen_ids: set[str] = set()

    for index, rule in enumerate(table.rules):
        path = f"rules[{index}]"
        if rule.id in seen_ids:
            diagnostics.append(Diagnostic("DT020", "error", f"Duplicate rule id {rule.id!r}", f"{path}.id"))
        seen_ids.add(rule.id)

        unknown_inputs = sorted(set(rule.when) - input_names)
        for name in unknown_inputs:
            diagnostics.append(Diagnostic("DT021", "error", f"Rule references unknown input {name!r}", f"{path}.when.{name}"))

        unknown_outputs = sorted(set(rule.then) - output_names)
        for name in unknown_outputs:
            diagnostics.append(Diagnostic("DT022", "error", f"Rule writes unknown output {name!r}", f"{path}.then.{name}"))

        missing_outputs = sorted(output_names - set(rule.then))
        for name in missing_outputs:
            diagnostics.append(Diagnostic("DT023", "warning", f"Rule does not set output {name!r}", f"{path}.then"))

        diagnostics.extend(_effective_date_diagnostics(rule, path))
    return diagnostics


def _effective_date_diagnostics(rule: Any, path: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    parsed: dict[str, date] = {}
    for field_name in ("effective_from", "effective_to"):
        value = getattr(rule, field_name)
        if value is None:
            continue
        try:
            parsed[field_name] = date.fromisoformat(value)
        except ValueError:
            diagnostics.append(Diagnostic(
                "DT024",
                "error",
                f"{field_name} must be an ISO date in YYYY-MM-DD format",
                f"{path}.{field_name}",
            ))
    if parsed.get("effective_from") and parsed.get("effective_to"):
        if parsed["effective_from"] > parsed["effective_to"]:
            diagnostics.append(Diagnostic(
                "DT025",
                "error",
                "effective_from must be on or before effective_to",
                path,
            ))
    return diagnostics


def _duplicate_and_conflict_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    by_condition: dict[str, tuple[int, Any]] = {}
    for index, rule in enumerate(table.rules):
        condition_key = _canonical(rule.when)
        output_key = _canonical(rule.then)
        if condition_key in by_condition:
            other_index, other_output = by_condition[condition_key]
            other_rule = table.rules[other_index]
            if other_output == output_key:
                severity = "error" if table.hit_policy == "unique" else "warning"
                suffix = "; duplicate matches violate UNIQUE hit policy" if table.hit_policy == "unique" else ""
                diagnostics.append(Diagnostic(
                    "DT030",
                    severity,
                    f"Rule {rule.id!r} duplicates conditions and outputs of {other_rule.id!r}{suffix}",
                    f"rules[{index}]",
                ))
            else:
                diagnostics.append(Diagnostic(
                    "DT031",
                    "error",
                    f"Rule {rule.id!r} conflicts with {other_rule.id!r}: same conditions, different outputs",
                    f"rules[{index}]",
                ))
        else:
            by_condition[condition_key] = (index, output_key)
    return diagnostics


def _condition_shape_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for rule_index, rule in enumerate(table.rules):
        for name, condition in rule.when.items():
            try:
                if isinstance(condition, dict):
                    if "between" in condition:
                        between = condition["between"]
                        if not isinstance(between, list) or len(between) != 2:
                            raise ValueError("between requires a two-item list")
                    condition_matches(condition, None, present=False)
            except (TypeError, ValueError) as exc:
                diagnostics.append(Diagnostic(
                    "DT040",
                    "error",
                    str(exc),
                    f"rules[{rule_index}].when.{name}",
                ))
    return diagnostics


def _relationship_diagnostics(table: DecisionTable) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if table.hit_policy == "unique":
        for relation in find_proven_overlaps(table):
            dimensions = ", ".join(relation.dimensions) or "declared inputs"
            diagnostics.append(Diagnostic(
                "DT032",
                "error",
                f"Rules {relation.first_rule_id!r} and {relation.second_rule_id!r} can both match; proven overlap on {dimensions}",
                f"rules[{relation.second_index}]",
            ))
    if table.hit_policy == "first":
        for relation in find_shadowed_rules(table):
            diagnostics.append(Diagnostic(
                "DT033",
                "warning",
                f"Rule {relation.second_rule_id!r} is fully shadowed by earlier rule {relation.first_rule_id!r}",
                f"rules[{relation.second_index}]",
            ))
    return diagnostics


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
