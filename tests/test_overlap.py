from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.overlap import find_proven_overlaps, find_shadowed_rules
from decision_tables_as_code.validate import validate_table


def _table(hit_policy, rules, input_type="string"):
    return table_from_mapping({
        "version": 1,
        "id": "relations",
        "hit_policy": hit_policy,
        "inputs": [{"name": "value", "type": input_type}],
        "outputs": [{"name": "result"}],
        "rules": rules,
    })


def _codes(table):
    return [item.code for item in validate_table(table)]


def test_unique_detects_scalar_list_overlap():
    table = _table("unique", [
        {"id": "de", "when": {"value": "DE"}, "then": {"result": "A"}},
        {"id": "dach", "when": {"value": ["DE", "AT"]}, "then": {"result": "B"}},
    ])
    relations = find_proven_overlaps(table)
    assert [(item.first_rule_id, item.second_rule_id) for item in relations] == [("de", "dach")]
    assert "DT032" in _codes(table)


def test_unique_detects_overlapping_numeric_ranges():
    table = _table("unique", [
        {"id": "low", "when": {"value": {"gte": 100, "lt": 200}}, "then": {"result": "A"}},
        {"id": "high", "when": {"value": {"between": [150, 300]}}, "then": {"result": "B"}},
    ], input_type="integer")
    assert "DT032" in _codes(table)


def test_disjoint_numeric_ranges_do_not_report_overlap():
    table = _table("unique", [
        {"id": "low", "when": {"value": {"lt": 100}}, "then": {"result": "A"}},
        {"id": "high", "when": {"value": {"gte": 100}}, "then": {"result": "B"}},
    ], input_type="integer")
    assert "DT032" not in _codes(table)


def test_regex_overlap_is_not_guessed():
    table = _table("unique", [
        {"id": "regex", "when": {"value": {"regex": "D.*"}}, "then": {"result": "A"}},
        {"id": "de", "when": {"value": "DE"}, "then": {"result": "B"}},
    ])
    assert find_proven_overlaps(table) == ()
    assert "DT032" not in _codes(table)


def test_first_policy_detects_specific_rule_shadowed_by_earlier_wildcard():
    table = _table("first", [
        {"id": "fallback", "priority": 10, "when": {"value": "*"}, "then": {"result": "fallback"}},
        {"id": "specific", "priority": 20, "when": {"value": "DE"}, "then": {"result": "specific"}},
    ])
    relations = find_shadowed_rules(table)
    assert [(item.first_rule_id, item.second_rule_id) for item in relations] == [("fallback", "specific")]
    assert "DT033" in _codes(table)


def test_first_policy_specific_before_fallback_is_not_full_shadow():
    table = _table("first", [
        {"id": "specific", "priority": 10, "when": {"value": "DE"}, "then": {"result": "specific"}},
        {"id": "fallback", "priority": 20, "when": {"value": "*"}, "then": {"result": "fallback"}},
    ])
    assert find_shadowed_rules(table) == ()
    assert "DT033" not in _codes(table)


def test_unique_exact_duplicate_is_an_error_even_with_same_output():
    table = _table("unique", [
        {"id": "a", "when": {"value": "DE"}, "then": {"result": "A"}},
        {"id": "b", "when": {"value": "DE"}, "then": {"result": "A"}},
    ])
    diagnostics = validate_table(table)
    duplicate = next(item for item in diagnostics if item.code == "DT030")
    assert duplicate.severity == "error"
    assert "UNIQUE" in duplicate.message
