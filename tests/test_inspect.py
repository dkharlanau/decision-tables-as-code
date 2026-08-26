from __future__ import annotations

from decision_tables_as_code.inspect import inspect_table
from decision_tables_as_code.model import table_from_mapping


def test_inspect_exposes_contract_rules_operators_and_diagnostics():
    table = table_from_mapping({
        "version": 1,
        "id": "routing",
        "name": "Routing",
        "hit_policy": "unique",
        "inputs": [
            {"name": "country", "type": "string", "domain": ["DE", "PL"]},
            {"name": "value", "type": "integer"},
        ],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [
            {
                "id": "de-high",
                "owner": "Order Management",
                "effective_from": "2027-01-01",
                "when": {"country": "DE", "value": {"gte": 5000}},
                "then": {"route": "enterprise"},
            },
            {
                "id": "pl-any",
                "when": {"country": ["PL"], "value": "*"},
                "then": {"route": "standard"},
            },
        ],
    })

    result = inspect_table(table)

    assert result["format_version"] == 1
    assert result["table"]["id"] == "routing"
    assert result["contract"]["inputs"][0]["name"] == "country"
    assert result["rules"]["count"] == 2
    assert result["rules"]["with_governance"] == 1
    assert result["rules"]["effective_dated"] == 1
    assert result["rules"]["operators"] == ["eq", "gte", "in", "present"]
    assert result["diagnostics"]["count"] == 0
