from pathlib import Path

import pytest

from decision_tables_as_code.engine import evaluate
from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping


EXAMPLE = Path(__file__).parents[1] / "examples" / "order-routing.yaml"


def test_unique_evaluation_selects_expected_rule():
    table = load_table(EXAMPLE)
    result = evaluate(table, {"country": "DE", "customer_type": "B2B", "order_value": 6000})
    assert result.matched_rule_ids == ("de-b2b-high",)
    assert result.outputs == {"route": "enterprise-desk", "approval": "senior"}


def test_first_hit_policy_respects_priority():
    table = table_from_mapping({
        "version": 1,
        "id": "priority",
        "hit_policy": "first",
        "inputs": [{"name": "country"}],
        "outputs": [{"name": "result"}],
        "rules": [
            {"id": "fallback", "priority": 100, "when": {"country": "*"}, "then": {"result": "fallback"}},
            {"id": "specific", "priority": 10, "when": {"country": "DE"}, "then": {"result": "specific"}},
        ],
    })
    result = evaluate(table, {"country": "DE"})
    assert result.matched_rule_ids == ("specific",)


def test_unique_policy_raises_when_multiple_rules_match():
    table = table_from_mapping({
        "version": 1,
        "id": "ambiguous",
        "hit_policy": "unique",
        "inputs": [{"name": "country"}],
        "outputs": [{"name": "result"}],
        "rules": [
            {"id": "a", "when": {"country": "DE"}, "then": {"result": "A"}},
            {"id": "b", "when": {"country": ["DE", "AT"]}, "then": {"result": "B"}},
        ],
    })
    with pytest.raises(ValueError, match="UNIQUE hit policy violated"):
        evaluate(table, {"country": "DE"})
