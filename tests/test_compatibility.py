from __future__ import annotations

from pathlib import Path

from decision_tables_as_code.compatibility import analyze_compatibility
from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping


ROOT = Path(__file__).parents[1]


def test_identical_table_is_proven_equivalent_over_full_domain():
    table = load_table(ROOT / "examples" / "order-routing.yaml")

    report = analyze_compatibility(table, table)

    assert report["provable"] is True
    assert report["equivalent"] is True
    assert report["changed"] is False
    assert report["total_combinations"] == 8
    assert report["evaluated_combinations"] == 8
    assert report["changed_combinations"] == 0
    assert report["witnesses"] == []


def test_existing_example_change_produces_concrete_output_witness():
    before = load_table(ROOT / "examples" / "order-routing.yaml")
    after = load_table(ROOT / "examples" / "order-routing-v2.yaml")

    report = analyze_compatibility(before, after)

    assert report["provable"] is True
    assert report["changed"] is True
    assert report["equivalent"] is False
    assert report["changed_combinations"] == 1
    assert report["category_counts"] == {"outputs_changed": 1}
    witness = report["witnesses"][0]
    assert witness["facts"] == {
        "country": "DE",
        "customer_type": "B2B",
        "order_value": 5000,
    }
    assert witness["before"]["outputs"]["approval"] == "senior"
    assert witness["after"]["outputs"]["approval"] == "director"


def test_union_domain_keeps_values_removed_from_candidate_domain():
    before = _country_table(["DE", "PL"], include_pl=True)
    after = _country_table(["DE"], include_pl=False)

    report = analyze_compatibility(before, after)

    assert report["provable"] is True
    assert report["total_combinations"] == 2
    assert report["input_space"][0]["union_domain"] == ["DE", "PL"]
    assert report["changed_combinations"] == 1
    witness = report["witnesses"][0]
    assert witness["facts"] == {"country": "PL"}
    assert "match_presence_changed" in witness["change_kinds"]
    assert witness["before"]["outputs"] == {"route": "PL"}
    assert witness["after"]["outputs"] is None


def test_rule_id_change_is_behavior_change_even_when_outputs_match():
    before = _single_rule_table("old-id")
    after = _single_rule_table("new-id")

    report = analyze_compatibility(before, after)

    assert report["changed"] is True
    assert report["category_counts"] == {"matched_rules_changed": 1}
    witness = report["witnesses"][0]
    assert witness["before"]["outputs"] == witness["after"]["outputs"] == {"result": "A"}
    assert witness["before"]["matched_rule_ids"] == ["old-id"]
    assert witness["after"]["matched_rule_ids"] == ["new-id"]


def test_effective_dated_table_requires_explicit_as_of_then_proves_equivalent():
    table = load_table(ROOT / "examples" / "effective-routing.yaml")

    blocked = analyze_compatibility(table, table)
    proven = analyze_compatibility(table, table, as_of="2027-01-01")

    assert blocked["provable"] is False
    assert {item["code"] for item in blocked["blocking_reasons"]} == {"as_of_required"}
    assert proven["provable"] is True
    assert proven["equivalent"] is True
    assert proven["as_of"] == "2027-01-01"


def test_missing_domain_returns_unprovable_instead_of_guessing():
    before = table_from_mapping({
        "version": 1,
        "id": "missing-domain",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [{"id": "de", "when": {"country": "DE"}, "then": {"route": "A"}}],
    })
    after = before

    report = analyze_compatibility(before, after)

    assert report["provable"] is False
    assert report["equivalent"] is None
    assert report["evaluated_combinations"] == 0
    assert {item["code"] for item in report["blocking_reasons"]} == {"missing_finite_domain"}


def test_combination_limit_returns_unprovable_with_exact_size():
    table = table_from_mapping({
        "version": 1,
        "id": "large-space",
        "inputs": [
            {"name": "a", "type": "integer", "domain": [1, 2, 3]},
            {"name": "b", "type": "integer", "domain": [1, 2, 3]},
        ],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "all", "when": {}, "then": {"result": "A"}}],
    })

    report = analyze_compatibility(table, table, max_combinations=8)

    assert report["provable"] is False
    assert report["total_combinations"] == 9
    assert report["blocking_reasons"] == [{
        "code": "combination_limit",
        "message": "Compatibility proof would evaluate 9 combinations; limit is 8",
    }]


def test_witness_limit_caps_evidence_without_changing_exact_counts():
    before = table_from_mapping({
        "version": 1,
        "id": "witness-cap",
        "inputs": [{"name": "x", "type": "integer", "domain": [1, 2, 3]}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "all", "when": {}, "then": {"result": "A"}}],
    })
    after = table_from_mapping({
        "version": 1,
        "id": "witness-cap",
        "inputs": [{"name": "x", "type": "integer", "domain": [1, 2, 3]}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "all", "when": {}, "then": {"result": "B"}}],
    })

    report = analyze_compatibility(before, after, max_witnesses=1)

    assert report["changed_combinations"] == 3
    assert report["category_counts"] == {"outputs_changed": 3}
    assert len(report["witnesses"]) == 1
    assert report["witnesses_truncated"] is True


def test_invalid_table_is_not_treated_as_a_behavioral_proof():
    before = table_from_mapping({
        "version": 1,
        "id": "invalid",
        "hit_policy": "unsupported",
        "inputs": [{"name": "x", "type": "integer", "domain": [1]}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "r", "when": {}, "then": {"result": "A"}}],
    })

    report = analyze_compatibility(before, before)

    assert report["provable"] is False
    assert "invalid_before_table" in {item["code"] for item in report["blocking_reasons"]}
    assert "invalid_after_table" in {item["code"] for item in report["blocking_reasons"]}


def _country_table(domain: list[str], *, include_pl: bool):
    rules = [
        {"id": "de", "when": {"country": "DE"}, "then": {"route": "DE"}},
    ]
    if include_pl:
        rules.append({"id": "pl", "when": {"country": "PL"}, "then": {"route": "PL"}})
    return table_from_mapping({
        "version": 1,
        "id": "countries",
        "inputs": [{"name": "country", "type": "string", "domain": domain}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": rules,
    })


def _single_rule_table(rule_id: str):
    return table_from_mapping({
        "version": 1,
        "id": "rule-identity",
        "inputs": [{"name": "x", "type": "integer", "domain": [1]}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": rule_id, "when": {"x": 1}, "then": {"result": "A"}}],
    })
