from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_tables_as_code.cli import main
from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.policy import (
    check_policies,
    check_policy,
    load_policy_pack,
    policy_from_mapping,
    policy_report,
)
from decision_tables_as_code.validate import validate_table


ROOT = Path(__file__).parents[1]
GOVERNED = ROOT / "examples" / "policy" / "governed-routing.yaml"
ENTERPRISE = ROOT / "policies" / "enterprise-governance.yaml"
SAP = ROOT / "policies" / "sap-change-control.yaml"


def test_governed_example_passes_enterprise_and_sap_policies():
    table = load_table(GOVERNED)
    policies = [load_policy_pack(ENTERPRISE), load_policy_pack(SAP)]

    report = policy_report(table, policies, validate_table(table))

    assert report["ok"] is True
    assert report["policy_ids"] == ["enterprise-governance", "sap-change-control"]
    assert report["policy_diagnostics"] == []
    assert report["summary"] == {
        "base_findings": 0,
        "policy_findings": 0,
        "errors": 0,
        "warnings": 0,
    }


def test_enterprise_policy_rejects_missing_rule_provenance_with_exact_paths():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    policy = load_policy_pack(ENTERPRISE)

    diagnostics = check_policy(table, policy)

    missing = [item for item in diagnostics if item.code == "POL004"]
    assert missing
    assert all(item.policy_id == "enterprise-governance" for item in missing)
    assert "rules[0].owner" in {item.path for item in missing}
    assert "rules[0].ticket" in {item.path for item in missing}
    assert "rules[0].rationale" in {item.path for item in missing}


def test_forbidden_operator_and_allowed_operator_checks_are_precise():
    table = table_from_mapping({
        "version": 1,
        "id": "operator-policy",
        "inputs": [{"name": "code", "type": "string", "domain": ["AA-1"]}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "r", "when": {"code": {"regex": "[A-Z]{2}-[0-9]"}}, "then": {"result": "A"}}],
    })
    policy = policy_from_mapping({
        "version": 1,
        "id": "portable-only",
        "rules": {
            "allowed_operators": ["eq", "in", "present"],
            "forbidden_operators": ["regex"],
        },
    })

    diagnostics = check_policy(table, policy)

    assert [(item.code, item.path) for item in diagnostics] == [
        ("POL006", "rules[0].when.code"),
        ("POL007", "rules[0].when.code"),
    ]


def test_policy_checks_domains_rule_count_hit_policy_and_effective_window():
    table = table_from_mapping({
        "version": 1,
        "id": "bounded-policy",
        "hit_policy": "collect",
        "inputs": [{"name": "x", "type": "integer"}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [
            {"id": "one", "effective_from": "2027-01-01", "when": {}, "then": {"result": "A"}},
            {"id": "two", "when": {}, "then": {"result": "B"}},
        ],
    })
    policy = policy_from_mapping({
        "version": 1,
        "id": "bounded",
        "rules": {
            "allowed_hit_policies": ["unique", "first"],
            "require_input_domains": True,
            "max_rules": 1,
            "require_complete_effective_window": True,
        },
    })

    diagnostics = check_policy(table, policy)
    by_code = {item.code: item for item in diagnostics}

    assert by_code["POL001"].path == "hit_policy"
    assert by_code["POL002"].path == "rules"
    assert by_code["POL003"].path == "inputs[0].domain"
    assert by_code["POL005"].path == "rules[0].effective_to"


def test_warning_policy_produces_findings_without_failing_report():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    policy = policy_from_mapping({
        "version": 1,
        "id": "advisory",
        "severity": "warning",
        "rules": {"required_rule_fields": ["owner"]},
    })

    report = policy_report(table, [policy], validate_table(table))

    assert report["policy_diagnostics"]
    assert all(item["severity"] == "warning" for item in report["policy_diagnostics"])
    assert report["ok"] is True
    assert report["summary"]["warnings"] == len(report["policy_diagnostics"])


def test_multiple_packs_compose_in_declared_order():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    first = policy_from_mapping({
        "version": 1,
        "id": "first",
        "rules": {"required_rule_fields": ["owner"]},
    })
    second = policy_from_mapping({
        "version": 1,
        "id": "second",
        "rules": {"required_rule_fields": ["ticket"]},
    })

    diagnostics = check_policies(table, [first, second])

    first_second_boundary = [item.policy_id for item in diagnostics]
    assert first_second_boundary == sorted(first_second_boundary, key=lambda value: 0 if value == "first" else 1)
    assert first_second_boundary[0] == "first"
    assert first_second_boundary[-1] == "second"


def test_invalid_policy_pack_rejects_unknown_fields_and_conflicts():
    with pytest.raises(ValueError, match="Unknown policy rule fields: mystery"):
        policy_from_mapping({
            "version": 1,
            "id": "bad",
            "rules": {"mystery": True},
        })

    with pytest.raises(ValueError, match="both allowed and forbidden: regex"):
        policy_from_mapping({
            "version": 1,
            "id": "conflict",
            "rules": {
                "allowed_operators": ["regex"],
                "forbidden_operators": ["regex"],
            },
        })


def test_policy_check_cli_composes_packs_and_writes_machine_report(tmp_path: Path):
    output = tmp_path / "policy.json"

    exit_code = main([
        "policy-check",
        str(GOVERNED),
        "--policy", str(ENTERPRISE),
        "--policy", str(SAP),
        "--format", "json",
        "--output", str(output),
    ])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["ok"] is True
    assert report["policy_ids"] == ["enterprise-governance", "sap-change-control"]


def test_policy_check_cli_fails_on_governance_error(tmp_path: Path):
    output = tmp_path / "policy.json"

    exit_code = main([
        "policy-check",
        str(ROOT / "examples" / "order-routing.yaml"),
        "--policy", str(ENTERPRISE),
        "--format", "json",
        "--output", str(output),
    ])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["ok"] is False
    assert report["summary"]["errors"] > 0
    assert {item["code"] for item in report["policy_diagnostics"]} == {"POL004"}
