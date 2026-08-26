from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import DecisionTable, Rule


@dataclass(frozen=True)
class TableDiff:
    added_rules: tuple[str, ...]
    removed_rules: tuple[str, ...]
    changed_rules: tuple[dict[str, Any], ...]
    changed_properties: tuple[dict[str, Any], ...]

    @property
    def changed(self) -> bool:
        return bool(self.added_rules or self.removed_rules or self.changed_rules or self.changed_properties)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def semantic_diff(before: DecisionTable, after: DecisionTable) -> TableDiff:
    before_rules = {rule.id: rule for rule in before.rules}
    after_rules = {rule.id: rule for rule in after.rules}

    added = tuple(sorted(after_rules.keys() - before_rules.keys()))
    removed = tuple(sorted(before_rules.keys() - after_rules.keys()))
    changed_rules: list[dict[str, Any]] = []

    for rule_id in sorted(before_rules.keys() & after_rules.keys()):
        changes = _rule_changes(before_rules[rule_id], after_rules[rule_id])
        if changes:
            changed_rules.append({"id": rule_id, "changes": changes})

    changed_properties: list[dict[str, Any]] = []
    for property_name in ("name", "description", "hit_policy", "inputs", "outputs", "metadata"):
        old_value = getattr(before, property_name)
        new_value = getattr(after, property_name)
        if old_value != new_value:
            changed_properties.append({"property": property_name, "before": _plain(old_value), "after": _plain(new_value)})

    return TableDiff(added, removed, tuple(changed_rules), tuple(changed_properties))


def _rule_changes(before: Rule, after: Rule) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for field_name in (
        "when",
        "then",
        "description",
        "priority",
        "owner",
        "source",
        "ticket",
        "rationale",
        "effective_from",
        "effective_to",
        "metadata",
    ):
        old_value = getattr(before, field_name)
        new_value = getattr(after, field_name)
        if old_value != new_value:
            changes[field_name] = {"before": _plain(old_value), "after": _plain(new_value)}
    return changes


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value
