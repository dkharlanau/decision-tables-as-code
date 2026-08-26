from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


SUPPORTED_HIT_POLICIES = {"unique", "first", "collect"}
SUPPORTED_TYPES = {"string", "integer", "number", "boolean", "date", "any"}


@dataclass(frozen=True)
class InputDefinition:
    name: str
    type: str = "any"
    description: str | None = None
    domain: tuple[Any, ...] = ()


@dataclass(frozen=True)
class OutputDefinition:
    name: str
    type: str = "any"
    description: str | None = None


@dataclass(frozen=True)
class Rule:
    id: str
    when: Mapping[str, Any]
    then: Mapping[str, Any]
    description: str | None = None
    priority: int | None = None
    owner: str | None = None
    source: str | None = None
    ticket: str | None = None
    rationale: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionTable:
    id: str
    name: str
    version: int
    hit_policy: str
    inputs: tuple[InputDefinition, ...]
    outputs: tuple[OutputDefinition, ...]
    rules: tuple[Rule, ...]
    description: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def input_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.inputs)

    @property
    def output_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.outputs)


def table_from_mapping(raw: Mapping[str, Any]) -> DecisionTable:
    if not isinstance(raw, Mapping):
        raise ValueError("Decision table document must be a mapping/object")

    version = raw.get("version", 1)
    if not isinstance(version, int):
        raise ValueError("version must be an integer")

    table_id = raw.get("id")
    if not isinstance(table_id, str) or not table_id.strip():
        raise ValueError("id must be a non-empty string")

    name = raw.get("name", table_id)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    hit_policy = str(raw.get("hit_policy", "unique")).lower()

    inputs_raw = raw.get("inputs", [])
    outputs_raw = raw.get("outputs", [])
    rules_raw = raw.get("rules", [])
    if not isinstance(inputs_raw, list) or not isinstance(outputs_raw, list) or not isinstance(rules_raw, list):
        raise ValueError("inputs, outputs and rules must be arrays")

    inputs = tuple(_input_from_mapping(item) for item in inputs_raw)
    outputs = tuple(_output_from_mapping(item) for item in outputs_raw)
    rules = tuple(_rule_from_mapping(item, index) for index, item in enumerate(rules_raw, start=1))

    metadata = raw.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be an object")

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("description must be a string")

    return DecisionTable(
        id=table_id,
        name=name,
        version=version,
        hit_policy=hit_policy,
        inputs=inputs,
        outputs=outputs,
        rules=rules,
        description=description,
        metadata=dict(metadata),
    )


def _input_from_mapping(raw: Mapping[str, Any]) -> InputDefinition:
    if not isinstance(raw, Mapping):
        raise ValueError("each input must be an object")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("input.name must be a non-empty string")
    data_type = str(raw.get("type", "any")).lower()
    domain_raw = raw.get("domain", [])
    if domain_raw is None:
        domain_raw = []
    if not isinstance(domain_raw, list):
        raise ValueError(f"input {name!r}: domain must be an array")
    return InputDefinition(
        name=name,
        type=data_type,
        description=raw.get("description"),
        domain=tuple(domain_raw),
    )


def _output_from_mapping(raw: Mapping[str, Any]) -> OutputDefinition:
    if not isinstance(raw, Mapping):
        raise ValueError("each output must be an object")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("output.name must be a non-empty string")
    return OutputDefinition(
        name=name,
        type=str(raw.get("type", "any")).lower(),
        description=raw.get("description"),
    )


def _rule_from_mapping(raw: Mapping[str, Any], index: int) -> Rule:
    if not isinstance(raw, Mapping):
        raise ValueError("each rule must be an object")
    rule_id = raw.get("id", f"rule-{index}")
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError("rule.id must be a non-empty string")
    when = raw.get("when", {})
    then = raw.get("then", {})
    if not isinstance(when, Mapping) or not isinstance(then, Mapping):
        raise ValueError(f"rule {rule_id!r}: when and then must be objects")
    priority = raw.get("priority")
    if priority is not None and not isinstance(priority, int):
        raise ValueError(f"rule {rule_id!r}: priority must be an integer")

    metadata = raw.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise ValueError(f"rule {rule_id!r}: metadata must be an object")

    return Rule(
        id=rule_id,
        when=dict(when),
        then=dict(then),
        description=_optional_string(raw, "description", rule_id),
        priority=priority,
        owner=_optional_string(raw, "owner", rule_id),
        source=_optional_string(raw, "source", rule_id),
        ticket=_optional_string(raw, "ticket", rule_id),
        rationale=_optional_string(raw, "rationale", rule_id),
        effective_from=_optional_string(raw, "effective_from", rule_id),
        effective_to=_optional_string(raw, "effective_to", rule_id),
        metadata=dict(metadata),
    )


def _optional_string(raw: Mapping[str, Any], field_name: str, rule_id: str) -> str | None:
    value = raw.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"rule {rule_id!r}: {field_name} must be a string")
    return value
