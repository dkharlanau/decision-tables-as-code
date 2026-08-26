from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import DecisionTable, Rule


_CLASSIFICATION_ORDER = {
    "none": 0,
    "governance_only": 1,
    "non_breaking": 2,
    "potentially_breaking": 3,
    "breaking": 4,
}
_RULE_GOVERNANCE_FIELDS = {"description", "owner", "source", "ticket", "rationale", "metadata"}


@dataclass(frozen=True)
class TableDiff:
    added_rules: tuple[str, ...]
    removed_rules: tuple[str, ...]
    changed_rules: tuple[dict[str, Any], ...]
    changed_properties: tuple[dict[str, Any], ...]
    classifications: tuple[dict[str, str], ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.added_rules or self.removed_rules or self.changed_rules or self.changed_properties)

    @property
    def classification(self) -> str:
        if not self.changed:
            return "none"
        if not self.classifications:
            return "potentially_breaking"
        return max(
            (item["classification"] for item in self.classifications),
            key=lambda value: _CLASSIFICATION_ORDER[value],
        )

    @property
    def breaking(self) -> bool:
        return self.classification == "breaking"

    def to_dict(self) -> dict[str, Any]:
        counts = {name: 0 for name in _CLASSIFICATION_ORDER if name != "none"}
        for item in self.classifications:
            counts[item["classification"]] += 1
        return {
            "format_version": 1,
            "changed": self.changed,
            "classification": self.classification,
            "breaking": self.breaking,
            "summary": counts,
            "added_rules": list(self.added_rules),
            "removed_rules": list(self.removed_rules),
            "changed_rules": list(self.changed_rules),
            "changed_properties": list(self.changed_properties),
            "classifications": list(self.classifications),
        }


def semantic_diff(before: DecisionTable, after: DecisionTable) -> TableDiff:
    before_rules = {rule.id: rule for rule in before.rules}
    after_rules = {rule.id: rule for rule in after.rules}

    added = tuple(sorted(after_rules.keys() - before_rules.keys()))
    removed = tuple(sorted(before_rules.keys() - after_rules.keys()))
    changed_rules: list[dict[str, Any]] = []
    classifications: list[dict[str, str]] = []

    for rule_id in added:
        classifications.append(_classification(
            f"rules.{rule_id}",
            "potentially_breaking",
            "A new rule can change which outputs are selected for existing facts.",
        ))
    for rule_id in removed:
        classifications.append(_classification(
            f"rules.{rule_id}",
            "potentially_breaking",
            "Removing a rule can change or remove decisions for facts it previously matched.",
        ))

    for rule_id in sorted(before_rules.keys() & after_rules.keys()):
        changes = _rule_changes(before_rules[rule_id], after_rules[rule_id])
        if changes:
            changed_rules.append({"id": rule_id, "changes": changes})
            classifications.extend(_classify_rule_changes(rule_id, changes))

    changed_properties: list[dict[str, Any]] = []
    for property_name in ("name", "description", "hit_policy", "inputs", "outputs", "metadata"):
        old_value = getattr(before, property_name)
        new_value = getattr(after, property_name)
        if old_value != new_value:
            changed_properties.append({"property": property_name, "before": _plain(old_value), "after": _plain(new_value)})

    classifications.extend(_classify_table_changes(before, after, changed_properties))

    return TableDiff(
        added,
        removed,
        tuple(changed_rules),
        tuple(changed_properties),
        tuple(classifications),
    )


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


def _classify_rule_changes(rule_id: str, changes: dict[str, Any]) -> list[dict[str, str]]:
    fields = set(changes)
    if fields <= _RULE_GOVERNANCE_FIELDS:
        return [_classification(
            f"rules.{rule_id}",
            "governance_only",
            "Only descriptive, ownership, source, ticket, rationale, or metadata fields changed.",
        )]

    items: list[dict[str, str]] = []
    semantic_fields = fields & {"when", "then", "priority", "effective_from", "effective_to"}
    if semantic_fields:
        items.append(_classification(
            f"rules.{rule_id}",
            "potentially_breaking",
            "Rule matching, outputs, ordering, or effective dates changed and may alter decisions.",
        ))
    if fields & _RULE_GOVERNANCE_FIELDS:
        items.append(_classification(
            f"rules.{rule_id}.governance",
            "governance_only",
            "Governance metadata changed alongside semantic rule changes.",
        ))
    return items


def _classify_table_changes(
    before: DecisionTable,
    after: DecisionTable,
    changed_properties: list[dict[str, Any]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    changed_names = {item["property"] for item in changed_properties}

    if "hit_policy" in changed_names:
        items.append(_classification(
            "hit_policy",
            "breaking",
            "Changing hit policy changes selection semantics for the same matching rules.",
        ))

    if changed_names & {"name", "description", "metadata"}:
        items.append(_classification(
            "table.governance",
            "governance_only",
            "Only human-facing table identity or metadata changed for these properties.",
        ))

    if "inputs" in changed_names:
        items.extend(_classify_contract_collection("inputs", before.inputs, after.inputs))
    if "outputs" in changed_names:
        items.extend(_classify_contract_collection("outputs", before.outputs, after.outputs))
    return items


def _classify_contract_collection(name: str, before_items: tuple[Any, ...], after_items: tuple[Any, ...]) -> list[dict[str, str]]:
    before_by_name = {item.name: item for item in before_items}
    after_by_name = {item.name: item for item in after_items}
    items: list[dict[str, str]] = []

    for field_name in sorted(before_by_name.keys() - after_by_name.keys()):
        classification = "breaking" if name == "outputs" else "potentially_breaking"
        items.append(_classification(
            f"{name}.{field_name}",
            classification,
            f"Declared {name[:-1]} {field_name!r} was removed.",
        ))

    for field_name in sorted(after_by_name.keys() - before_by_name.keys()):
        classification = "potentially_breaking" if name == "outputs" else "non_breaking"
        items.append(_classification(
            f"{name}.{field_name}",
            classification,
            f"Declared {name[:-1]} {field_name!r} was added.",
        ))

    for field_name in sorted(before_by_name.keys() & after_by_name.keys()):
        old_item = before_by_name[field_name]
        new_item = after_by_name[field_name]
        if old_item.type != new_item.type:
            items.append(_classification(
                f"{name}.{field_name}.type",
                "breaking",
                f"Declared type changed from {old_item.type!r} to {new_item.type!r}.",
            ))
        if name == "inputs" and getattr(old_item, "domain", ()) != getattr(new_item, "domain", ()):
            items.append(_classification(
                f"inputs.{field_name}.domain",
                "potentially_breaking",
                "The declared finite input domain changed and may alter coverage expectations.",
            ))
        if old_item.description != new_item.description:
            items.append(_classification(
                f"{name}.{field_name}.description",
                "governance_only",
                "Only the field description changed.",
            ))
    return items


def _classification(path: str, classification: str, reason: str) -> dict[str, str]:
    return {"path": path, "classification": classification, "reason": reason}


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value
