from __future__ import annotations

import pytest

from decision_tables_as_code.engine import evaluate
from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.validate import validate_table


def _table(rules):
    return table_from_mapping({
        "version": 1,
        "id": "routing",
        "hit_policy": "unique",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": rules,
    })


def test_rule_provenance_is_preserved():
    table = _table([{
        "id": "de",
        "when": {"country": "DE"},
        "then": {"route": "eu"},
        "owner": "Order Management",
        "source": "pricing-workbook.xlsx",
        "ticket": "CHG-1042",
        "rationale": "Route German orders through the EU flow",
        "metadata": {"control": "SOX-12"},
    }])

    rule = table.rules[0]
    assert rule.owner == "Order Management"
    assert rule.source == "pricing-workbook.xlsx"
    assert rule.ticket == "CHG-1042"
    assert rule.rationale.startswith("Route German")
    assert rule.metadata == {"control": "SOX-12"}


def test_effective_rules_require_explicit_as_of_date():
    table = _table([{
        "id": "de-2027",
        "when": {"country": "DE"},
        "then": {"route": "new"},
        "effective_from": "2027-01-01",
    }])

    with pytest.raises(ValueError, match="explicit as_of"):
        evaluate(table, {"country": "DE"})


def test_evaluation_selects_rule_for_explicit_date():
    table = _table([
        {
            "id": "de-2026",
            "when": {"country": "DE"},
            "then": {"route": "old"},
            "effective_to": "2026-12-31",
        },
        {
            "id": "de-2027",
            "when": {"country": "DE"},
            "then": {"route": "new"},
            "effective_from": "2027-01-01",
        },
    ])

    old = evaluate(table, {"country": "DE"}, as_of="2026-12-31")
    new = evaluate(table, {"country": "DE"}, as_of="2027-01-01")

    assert old.matched_rule_ids == ("de-2026",)
    assert old.outputs == {"route": "old"}
    assert new.matched_rule_ids == ("de-2027",)
    assert new.outputs == {"route": "new"}


def test_non_overlapping_effective_windows_do_not_conflict():
    table = _table([
        {
            "id": "de-2026",
            "when": {"country": "DE"},
            "then": {"route": "old"},
            "effective_to": "2026-12-31",
        },
        {
            "id": "de-2027",
            "when": {"country": "DE"},
            "then": {"route": "new"},
            "effective_from": "2027-01-01",
        },
    ])

    codes = {item.code for item in validate_table(table)}
    assert "DT031" not in codes
    assert "DT032" not in codes


def test_invalid_effective_window_is_reported():
    table = _table([{
        "id": "de",
        "when": {"country": "DE"},
        "then": {"route": "eu"},
        "effective_from": "2027-02-01",
        "effective_to": "2027-01-01",
    }])

    diagnostics = validate_table(table)
    assert any(item.code == "DT025" for item in diagnostics)
