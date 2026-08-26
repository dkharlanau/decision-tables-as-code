from __future__ import annotations

from decision_tables_as_code.explain import explain_table
from decision_tables_as_code.model import table_from_mapping


def test_explain_identifies_failed_conditions_and_selected_rule():
    table = table_from_mapping({
        "version": 1,
        "id": "routing",
        "hit_policy": "first",
        "inputs": [
            {"name": "country", "type": "string"},
            {"name": "value", "type": "integer"},
        ],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [
            {
                "id": "de-high",
                "priority": 10,
                "when": {"country": "DE", "value": {"gte": 5000}},
                "then": {"route": "enterprise"},
            },
            {
                "id": "de-default",
                "priority": 20,
                "when": {"country": "DE"},
                "then": {"route": "standard"},
            },
        ],
    })

    result = explain_table(table, {"country": "DE", "value": 1000})

    assert result["format_version"] == 1
    assert result["result"]["matched_rule_ids"] == ("de-default",)
    assert result["rules"][0]["matched"] is False
    assert result["rules"][0]["conditions"][1]["input"] == "value"
    assert result["rules"][0]["conditions"][1]["matched"] is False
    assert result["rules"][1]["matched"] is True
    assert result["rules"][1]["selected"] is True


def test_explain_marks_effective_dated_rule_inactive():
    table = table_from_mapping({
        "version": 1,
        "id": "routing",
        "hit_policy": "unique",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [{
            "id": "future",
            "effective_from": "2027-01-01",
            "when": {"country": "DE"},
            "then": {"route": "new"},
        }],
    })

    result = explain_table(table, {"country": "DE"}, as_of="2026-12-31")

    assert result["rules"][0]["effective"] is False
    assert result["rules"][0]["conditions_matched"] is True
    assert result["rules"][0]["matched"] is False
    assert result["result"]["matched_rule_ids"] == ()
