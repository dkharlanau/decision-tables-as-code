from __future__ import annotations

from datetime import date, datetime
from itertools import product
from math import prod
from typing import Any, Mapping

from .engine import evaluate
from .model import DecisionTable
from .validate import validate_table


REPORT_FORMAT_VERSION = 1


def analyze_compatibility(
    before: DecisionTable,
    after: DecisionTable,
    *,
    as_of: str | date | datetime | None = None,
    max_combinations: int = 10_000,
    max_witnesses: int = 100,
) -> dict[str, Any]:
    """Exhaustively compare two tables over the union of their declared finite domains.

    The function returns `provable: false` rather than guessing when the input
    contracts/domains do not define a finite common fact space or the requested
    proof would exceed the safety limit.
    """
    if max_combinations < 1:
        raise ValueError("max_combinations must be at least 1")
    if max_witnesses < 0:
        raise ValueError("max_witnesses must be zero or greater")

    blockers = _proof_blockers(before, after, as_of=as_of)
    if blockers:
        return _unprovable_report(before, after, blockers, as_of=as_of)

    before_inputs = {item.name: item for item in before.inputs}
    after_inputs = {item.name: item for item in after.inputs}
    input_order = [item.name for item in before.inputs]
    spaces: list[dict[str, Any]] = []
    union_domains: list[tuple[Any, ...]] = []

    for name in input_order:
        before_domain = before_inputs[name].domain
        after_domain = after_inputs[name].domain
        union_domain = _ordered_union(before_domain, after_domain)
        union_domains.append(union_domain)
        spaces.append({
            "name": name,
            "type": before_inputs[name].type,
            "before_domain": list(before_domain),
            "after_domain": list(after_domain),
            "union_domain": list(union_domain),
        })

    total = prod(len(domain) for domain in union_domains)
    if total > max_combinations:
        return _unprovable_report(
            before,
            after,
            [{
                "code": "combination_limit",
                "message": f"Compatibility proof would evaluate {total} combinations; limit is {max_combinations}",
            }],
            as_of=as_of,
            input_space=spaces,
            total_combinations=total,
        )

    category_counts: dict[str, int] = {}
    changed_combinations = 0
    witnesses: list[dict[str, Any]] = []

    for values in product(*union_domains):
        facts = dict(zip(input_order, values))
        before_behavior = _behavior(before, facts, as_of=as_of)
        after_behavior = _behavior(after, facts, as_of=as_of)
        change_kinds = _change_kinds(before_behavior, after_behavior)
        if not change_kinds:
            continue

        changed_combinations += 1
        for kind in change_kinds:
            category_counts[kind] = category_counts.get(kind, 0) + 1
        if len(witnesses) < max_witnesses:
            witnesses.append({
                "facts": facts,
                "change_kinds": change_kinds,
                "before": before_behavior,
                "after": after_behavior,
            })

    changed = changed_combinations > 0
    return {
        "format_version": REPORT_FORMAT_VERSION,
        "before_table": before.id,
        "after_table": after.id,
        "provable": True,
        "equivalent": not changed,
        "changed": changed,
        "as_of": _date_text(as_of),
        "input_space": spaces,
        "total_combinations": total,
        "evaluated_combinations": total,
        "changed_combinations": changed_combinations,
        "category_counts": dict(sorted(category_counts.items())),
        "witnesses_truncated": changed_combinations > len(witnesses),
        "witness_limit": max_witnesses,
        "witnesses": witnesses,
        "blocking_reasons": [],
    }


def _proof_blockers(
    before: DecisionTable,
    after: DecisionTable,
    *,
    as_of: str | date | datetime | None,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []

    for side, table in (("before", before), ("after", after)):
        errors = [item for item in validate_table(table) if item.severity == "error"]
        if errors:
            rendered = "; ".join(f"{item.code} {item.path}: {item.message}" for item in errors)
            blockers.append({
                "code": f"invalid_{side}_table",
                "message": f"{side.capitalize()} table has validation errors: {rendered}",
            })

    before_by_name = {item.name: item for item in before.inputs}
    after_by_name = {item.name: item for item in after.inputs}
    before_names = set(before_by_name)
    after_names = set(after_by_name)

    if before_names != after_names:
        missing_after = sorted(before_names - after_names)
        added_after = sorted(after_names - before_names)
        details: list[str] = []
        if missing_after:
            details.append("removed inputs: " + ", ".join(missing_after))
        if added_after:
            details.append("added inputs: " + ", ".join(added_after))
        blockers.append({
            "code": "input_contract_mismatch",
            "message": "Input names differ between versions (" + "; ".join(details) + ")",
        })
        return blockers

    type_mismatches = [
        name
        for name in sorted(before_names)
        if before_by_name[name].type != after_by_name[name].type
    ]
    if type_mismatches:
        rendered = ", ".join(
            f"{name}: {before_by_name[name].type} -> {after_by_name[name].type}"
            for name in type_mismatches
        )
        blockers.append({
            "code": "input_type_mismatch",
            "message": "Input types differ between versions: " + rendered,
        })

    missing_domains: list[str] = []
    for name in sorted(before_names):
        if not before_by_name[name].domain:
            missing_domains.append(f"before.{name}")
        if not after_by_name[name].domain:
            missing_domains.append(f"after.{name}")
    if missing_domains:
        blockers.append({
            "code": "missing_finite_domain",
            "message": "Compatibility proof requires non-empty domain values for every input in both versions; missing: " + ", ".join(missing_domains),
        })

    if as_of is None and (_has_effective_dates(before) or _has_effective_dates(after)):
        blockers.append({
            "code": "as_of_required",
            "message": "At least one table has effective-dated rules; pass an explicit as_of date for deterministic comparison",
        })

    return blockers


def _behavior(
    table: DecisionTable,
    facts: Mapping[str, Any],
    *,
    as_of: str | date | datetime | None,
) -> dict[str, Any]:
    try:
        result = evaluate(table, facts, as_of=as_of)
    except Exception as exc:  # deterministic runtime behavior is part of compatibility
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "status": "ok",
        "matched_rule_ids": list(result.matched_rule_ids),
        "outputs": result.outputs,
    }


def _change_kinds(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    if before == after:
        return []
    if before.get("status") != after.get("status"):
        return ["error_vs_result"]
    if before.get("status") == "error":
        return ["error_changed"]

    kinds: list[str] = []
    before_rules = before.get("matched_rule_ids", [])
    after_rules = after.get("matched_rule_ids", [])
    if bool(before_rules) != bool(after_rules):
        kinds.append("match_presence_changed")
    if before_rules != after_rules:
        kinds.append("matched_rules_changed")
    if before.get("outputs") != after.get("outputs"):
        kinds.append("outputs_changed")
    return kinds or ["result_changed"]


def _ordered_union(before: tuple[Any, ...], after: tuple[Any, ...]) -> tuple[Any, ...]:
    result: list[Any] = []
    for value in (*before, *after):
        if not any(_same_domain_value(value, existing) for existing in result):
            result.append(value)
    return tuple(result)


def _same_domain_value(left: Any, right: Any) -> bool:
    # bool is a subclass of int in Python; domains should not collapse true and 1.
    if type(left) is not type(right):
        return False
    return left == right


def _has_effective_dates(table: DecisionTable) -> bool:
    return any(rule.effective_from is not None or rule.effective_to is not None for rule in table.rules)


def _date_text(value: str | date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _unprovable_report(
    before: DecisionTable,
    after: DecisionTable,
    blockers: list[dict[str, str]],
    *,
    as_of: str | date | datetime | None,
    input_space: list[dict[str, Any]] | None = None,
    total_combinations: int | None = None,
) -> dict[str, Any]:
    return {
        "format_version": REPORT_FORMAT_VERSION,
        "before_table": before.id,
        "after_table": after.id,
        "provable": False,
        "equivalent": None,
        "changed": None,
        "as_of": _date_text(as_of),
        "input_space": input_space or [],
        "total_combinations": total_combinations,
        "evaluated_combinations": 0,
        "changed_combinations": None,
        "category_counts": {},
        "witnesses_truncated": False,
        "witness_limit": None,
        "witnesses": [],
        "blocking_reasons": blockers,
    }
