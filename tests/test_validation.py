from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.validate import validate_table


def _codes(table):
    return {item.code for item in validate_table(table)}


def test_conflicting_exact_rules_are_errors():
    table = table_from_mapping({
        "version": 1,
        "id": "conflict",
        "inputs": [{"name": "country"}],
        "outputs": [{"name": "result"}],
        "rules": [
            {"id": "a", "when": {"country": "DE"}, "then": {"result": "A"}},
            {"id": "b", "when": {"country": "DE"}, "then": {"result": "B"}},
        ],
    })
    assert "DT031" in _codes(table)


def test_unknown_columns_are_reported():
    table = table_from_mapping({
        "version": 1,
        "id": "unknown",
        "inputs": [{"name": "country"}],
        "outputs": [{"name": "result"}],
        "rules": [{"id": "a", "when": {"market": "DE"}, "then": {"route": "A"}}],
    })
    assert {"DT021", "DT022"}.issubset(_codes(table))
