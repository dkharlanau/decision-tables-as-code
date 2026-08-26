from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .io import load_document
from .model import DecisionTable, SUPPORTED_HIT_POLICIES


POLICY_FORMAT_VERSION = 1
_POLICY_FIELDS = {
    "required_rule_fields",
    "allowed_hit_policies",
    "allowed_operators",
    "forbidden_operators",
    "require_input_domains",
    "max_rules",
    "require_complete_effective_window",
}
_PROVENANCE_FIELDS = {"owner", "source", "ticket", "rationale"}
_OPERATOR_NAMES = {
    "eq",
    "ne",
    "in",
    "not_in",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "exists",
    "regex",
    "present",
}
_SEVERITIES = {"error", "warning"}


@dataclass(frozen=True)
class PolicyPack:
    id: str
    version: int
    severity: str
    required_rule_fields: tuple[str, ...] = ()
    allowed_hit_policies: tuple[str, ...] | None = None
    allowed_operators: tuple[str, ...] | None = None
    forbidden_operators: tuple[str, ...] = ()
    require_input_domains: bool = False
    max_rules: int | None = None
    require_complete_effective_window: bool = False
    description: str | None = None


@dataclass(frozen=True)
class PolicyDiagnostic:
    code: str
    severity: str
    policy_id: str
    message: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_policy_pack(path: str | Path) -> PolicyPack:
    return policy_from_mapping(load_document(path))


def policy_from_mapping(raw: Mapping[str, Any]) -> PolicyPack:
    allowed_root = {"version", "id", "description", "severity", "rules"}
    unknown_root = sorted(set(raw) - allowed_root)
    if unknown_root:
        raise ValueError("Unknown policy-pack fields: " + ", ".join(unknown_root))

    version = raw.get("version", 1)
    if version != POLICY_FORMAT_VERSION:
        raise ValueError(f"Unsupported policy-pack version {version!r}; expected {POLICY_FORMAT_VERSION}")

    policy_id = raw.get("id")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ValueError("policy id must be a non-empty string")

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("policy description must be a string")

    severity = raw.get("severity", "error")
    if severity not in _SEVERITIES:
        raise ValueError("policy severity must be 'error' or 'warning'")

    rules = raw.get("rules")
    if not isinstance(rules, Mapping) or not rules:
        raise ValueError("policy rules must be a non-empty object")
    unknown_rules = sorted(set(rules) - _POLICY_FIELDS)
    if unknown_rules:
        raise ValueError("Unknown policy rule fields: " + ", ".join(unknown_rules))

    required_rule_fields = _string_list(rules, "required_rule_fields", default=())
    unknown_provenance = sorted(set(required_rule_fields) - _PROVENANCE_FIELDS)
    if unknown_provenance:
        raise ValueError(
            "required_rule_fields only supports owner, source, ticket, rationale; unknown: "
            + ", ".join(unknown_provenance)
        )

    allowed_hit_policies = _optional_string_list(rules, "allowed_hit_policies")
    if allowed_hit_policies is not None:
        unknown = sorted(set(allowed_hit_policies) - SUPPORTED_HIT_POLICIES)
        if unknown:
            raise ValueError("Unknown allowed hit policies: " + ", ".join(unknown))

    allowed_operators = _optional_string_list(rules, "allowed_operators")
    forbidden_operators = _string_list(rules, "forbidden_operators", default=())
    for field_name, values in (
        ("allowed_operators", allowed_operators or ()),
        ("forbidden_operators", forbidden_operators),
    ):
        unknown = sorted(set(values) - _OPERATOR_NAMES)
        if unknown:
            raise ValueError(f"Unknown {field_name}: " + ", ".join(unknown))
    if allowed_operators is not None:
        overlap = sorted(set(allowed_operators) & set(forbidden_operators))
        if overlap:
            raise ValueError(
                "Operators cannot be both allowed and forbidden: " + ", ".join(overlap)
            )

    require_input_domains = _bool_value(rules, "require_input_domains", False)
    require_complete_effective_window = _bool_value(
        rules, "require_complete_effective_window", False
    )

    max_rules = rules.get("max_rules")
    if max_rules is not None and (not isinstance(max_rules, int) or isinstance(max_rules, bool) or max_rules < 1):
        raise ValueError("max_rules must be a positive integer")

    return PolicyPack(
        id=policy_id,
        version=version,
        severity=severity,
        required_rule_fields=required_rule_fields,
        allowed_hit_policies=allowed_hit_policies,
        allowed_operators=allowed_operators,
        forbidden_operators=forbidden_operators,
        require_input_domains=require_input_domains,
        max_rules=max_rules,
        require_complete_effective_window=require_complete_effective_window,
        description=description,
    )


def check_policy(table: DecisionTable, policy: PolicyPack) -> list[PolicyDiagnostic]:
    diagnostics: list[PolicyDiagnostic] = []

    if policy.allowed_hit_policies is not None and table.hit_policy not in policy.allowed_hit_policies:
        diagnostics.append(_diag(
            policy,
            "POL001",
            f"Hit policy {table.hit_policy!r} is not allowed; allowed: {', '.join(policy.allowed_hit_policies)}",
            "hit_policy",
        ))

    if policy.max_rules is not None and len(table.rules) > policy.max_rules:
        diagnostics.append(_diag(
            policy,
            "POL002",
            f"Table has {len(table.rules)} rules; policy maximum is {policy.max_rules}",
            "rules",
        ))

    if policy.require_input_domains:
        for index, input_definition in enumerate(table.inputs):
            if not input_definition.domain:
                diagnostics.append(_diag(
                    policy,
                    "POL003",
                    f"Input {input_definition.name!r} must declare a finite domain",
                    f"inputs[{index}].domain",
                ))

    for rule_index, rule in enumerate(table.rules):
        for field_name in policy.required_rule_fields:
            value = getattr(rule, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                diagnostics.append(_diag(
                    policy,
                    "POL004",
                    f"Rule {rule.id!r} must define {field_name}",
                    f"rules[{rule_index}].{field_name}",
                ))

        if policy.require_complete_effective_window:
            has_from = rule.effective_from is not None
            has_to = rule.effective_to is not None
            if has_from != has_to:
                missing = "effective_to" if has_from else "effective_from"
                diagnostics.append(_diag(
                    policy,
                    "POL005",
                    f"Rule {rule.id!r} uses an effective-date boundary and must define both effective_from and effective_to",
                    f"rules[{rule_index}].{missing}",
                ))

        for input_name, condition in rule.when.items():
            for operator in _condition_operators(condition):
                condition_path = f"rules[{rule_index}].when.{input_name}"
                if policy.allowed_operators is not None and operator not in policy.allowed_operators:
                    diagnostics.append(_diag(
                        policy,
                        "POL006",
                        f"Operator {operator!r} is not allowed; allowed: {', '.join(policy.allowed_operators)}",
                        condition_path,
                    ))
                if operator in policy.forbidden_operators:
                    diagnostics.append(_diag(
                        policy,
                        "POL007",
                        f"Operator {operator!r} is forbidden by policy",
                        condition_path,
                    ))

    return diagnostics


def check_policies(
    table: DecisionTable, policies: list[PolicyPack] | tuple[PolicyPack, ...]
) -> list[PolicyDiagnostic]:
    diagnostics: list[PolicyDiagnostic] = []
    for policy in policies:
        diagnostics.extend(check_policy(table, policy))
    return diagnostics


def policy_report(
    table: DecisionTable,
    policies: list[PolicyPack] | tuple[PolicyPack, ...],
    base_diagnostics: list[Any] | tuple[Any, ...] = (),
) -> dict[str, Any]:
    policy_diagnostics = check_policies(table, policies)
    base = [item.to_dict() for item in base_diagnostics]
    policy_items = [item.to_dict() for item in policy_diagnostics]
    has_errors = any(item.get("severity") == "error" for item in (*base, *policy_items))
    return {
        "format_version": 1,
        "table_id": table.id,
        "policy_ids": [policy.id for policy in policies],
        "ok": not has_errors,
        "base_validation": base,
        "policy_diagnostics": policy_items,
        "summary": {
            "base_findings": len(base),
            "policy_findings": len(policy_items),
            "errors": sum(1 for item in (*base, *policy_items) if item.get("severity") == "error"),
            "warnings": sum(1 for item in (*base, *policy_items) if item.get("severity") == "warning"),
        },
    }


def _condition_operators(condition: Any) -> tuple[str, ...]:
    if condition == "*":
        return ("present",)
    if isinstance(condition, Mapping):
        return tuple(sorted(str(key) for key in condition))
    if isinstance(condition, (list, tuple)) and not isinstance(condition, (str, bytes, bytearray)):
        return ("in",)
    return ("eq",)


def _diag(policy: PolicyPack, code: str, message: str, path: str) -> PolicyDiagnostic:
    return PolicyDiagnostic(code, policy.severity, policy.id, message, path)


def _string_list(
    mapping: Mapping[str, Any], field_name: str, *, default: tuple[str, ...]
) -> tuple[str, ...]:
    if field_name not in mapping:
        return default
    raw = mapping[field_name]
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) and item for item in raw):
        raise ValueError(f"{field_name} must be a non-empty array of strings")
    if len(set(raw)) != len(raw):
        raise ValueError(f"{field_name} must not contain duplicates")
    return tuple(raw)


def _optional_string_list(mapping: Mapping[str, Any], field_name: str) -> tuple[str, ...] | None:
    if field_name not in mapping:
        return None
    return _string_list(mapping, field_name, default=())


def _bool_value(mapping: Mapping[str, Any], field_name: str, default: bool) -> bool:
    value = mapping.get(field_name, default)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value
