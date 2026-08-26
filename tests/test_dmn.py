from __future__ import annotations

import pytest

from decision_tables_as_code.diff import semantic_diff
from decision_tables_as_code.dmn import DMN_NS, DMNUnsupportedError, dumps_dmn, loads_dmn
from decision_tables_as_code.engine import evaluate
from decision_tables_as_code.model import table_from_mapping


def test_import_unique_table_preserves_rules_conditions_and_domains():
    table = loads_dmn(_unique_dmn())

    assert table.id == "routing"
    assert table.name == "Routing"
    assert table.hit_policy == "unique"
    assert table.inputs[0].name == "country"
    assert table.inputs[0].domain == ("DE", "PL")
    assert table.inputs[1].type == "number"
    assert table.rules[0].id == "de-high"
    assert table.rules[0].when == {"country": "DE", "amount": {"gte": 5000}}
    assert table.rules[1].when == {"country": "DE", "amount": {"gte": 0, "lte": 4999}}
    assert table.rules[2].when == {"country": "PL"}


def test_unique_round_trip_has_no_semantic_diff():
    table = table_from_mapping({
        "version": 1,
        "id": "routing",
        "name": "Routing",
        "description": "Portable routing decision",
        "hit_policy": "unique",
        "inputs": [
            {"name": "country", "type": "string", "domain": ["DE", "PL"]},
            {"name": "amount", "type": "number"},
        ],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [
            {
                "id": "de-high",
                "when": {"country": "DE", "amount": {"gte": 5000}},
                "then": {"route": "enterprise"},
            },
            {
                "id": "de-low",
                "when": {"country": "DE", "amount": {"lt": 5000}},
                "then": {"route": "standard"},
            },
            {
                "id": "pl-all",
                "when": {"country": "PL"},
                "then": {"route": "standard"},
            },
        ],
    })

    restored = loads_dmn(dumps_dmn(table))

    assert semantic_diff(table, restored).changed is False
    assert evaluate(restored, {"country": "DE", "amount": 6000}).outputs == {"route": "enterprise"}
    assert evaluate(restored, {"country": "PL", "amount": 10}).outputs == {"route": "standard"}


def test_first_round_trip_preserves_rule_order_behavior():
    table = table_from_mapping({
        "version": 1,
        "id": "approval",
        "name": "Approval",
        "hit_policy": "first",
        "inputs": [{"name": "amount", "type": "number"}],
        "outputs": [{"name": "strategy", "type": "string"}],
        "rules": [
            {"id": "large", "when": {"amount": {"gte": 10000}}, "then": {"strategy": "L3"}},
            {"id": "medium", "when": {"amount": {"gte": 1000}}, "then": {"strategy": "L2"}},
            {"id": "fallback", "when": {}, "then": {"strategy": "L1"}},
        ],
    })

    restored = loads_dmn(dumps_dmn(table))

    assert semantic_diff(table, restored).changed is False
    assert [rule.id for rule in restored.rules] == ["large", "medium", "fallback"]
    assert evaluate(restored, {"amount": 15000}).outputs == {"strategy": "L3"}
    assert evaluate(restored, {"amount": 5000}).outputs == {"strategy": "L2"}
    assert evaluate(restored, {"amount": 100}).outputs == {"strategy": "L1"}


def test_multiple_decisions_require_explicit_selection():
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{DMN_NS}" id="defs" name="Multiple" namespace="urn:test">
  <decision id="one" name="One">
    <decisionTable id="one-table" hitPolicy="UNIQUE">
      <input id="one-input"><inputExpression id="one-expr" typeRef="string"><text>country</text></inputExpression></input>
      <output id="one-output" name="route" typeRef="string"/>
      <rule id="one-rule"><inputEntry id="one-entry"><text>"DE"</text></inputEntry><outputEntry id="one-result"><text>"A"</text></outputEntry></rule>
    </decisionTable>
  </decision>
  <decision id="two" name="Two">
    <decisionTable id="two-table" hitPolicy="UNIQUE">
      <input id="two-input"><inputExpression id="two-expr" typeRef="string"><text>country</text></inputExpression></input>
      <output id="two-output" name="route" typeRef="string"/>
      <rule id="two-rule"><inputEntry id="two-entry"><text>"PL"</text></inputEntry><outputEntry id="two-result"><text>"B"</text></outputEntry></rule>
    </decisionTable>
  </decision>
</definitions>'''

    with pytest.raises(ValueError, match="exactly one decision-table decision"):
        loads_dmn(xml)

    selected = loads_dmn(xml, decision_id="two")
    assert selected.id == "two"
    assert selected.rules[0].id == "two-rule"


def test_collect_hit_policy_is_rejected_explicitly():
    xml = _unique_dmn().replace('hitPolicy="UNIQUE"', 'hitPolicy="COLLECT"')
    with pytest.raises(DMNUnsupportedError, match="supported subset: UNIQUE, FIRST"):
        loads_dmn(xml)


def test_unsupported_feel_expression_is_rejected():
    xml = _unique_dmn().replace('&gt;= 5000', 'matches("x", "y")', 1)
    with pytest.raises(DMNUnsupportedError, match="Unsupported FEEL literal/expression"):
        loads_dmn(xml)


def test_integer_export_is_rejected_instead_of_silent_number_coercion():
    table = table_from_mapping({
        "version": 1,
        "id": "integer-table",
        "inputs": [{"name": "quantity", "type": "integer"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [{"id": "one", "when": {"quantity": 1}, "then": {"route": "A"}}],
    })

    with pytest.raises(DMNUnsupportedError, match="FEEL has number rather than a distinct integer"):
        dumps_dmn(table)


def test_governance_fields_are_rejected_on_export_instead_of_dropped():
    table = table_from_mapping({
        "version": 1,
        "id": "governed",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [
            {
                "id": "de",
                "owner": "Order Management",
                "effective_from": "2027-01-01",
                "when": {"country": "DE"},
                "then": {"route": "A"},
            }
        ],
    })

    with pytest.raises(DMNUnsupportedError, match="governance/effective-date fields"):
        dumps_dmn(table)


def test_present_wildcard_is_rejected_because_dmn_dash_has_different_null_semantics():
    table = table_from_mapping({
        "version": 1,
        "id": "present-only",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": [{"name": "route", "type": "string"}],
        "rules": [{"id": "present", "when": {"country": "*"}, "then": {"route": "A"}}],
    })

    with pytest.raises(DMNUnsupportedError, match="any present value"):
        dumps_dmn(table)


def _unique_dmn() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{DMN_NS}" id="defs-routing" name="Routing model" namespace="urn:test:routing">
  <decision id="routing" name="Routing">
    <description>Portable routing decision</description>
    <decisionTable id="routing-table" hitPolicy="UNIQUE">
      <input id="input-country" label="Country">
        <inputExpression id="expr-country" typeRef="string"><text>country</text></inputExpression>
        <inputValues id="values-country"><text>"DE", "PL"</text></inputValues>
      </input>
      <input id="input-amount" label="Amount">
        <inputExpression id="expr-amount" typeRef="number"><text>amount</text></inputExpression>
      </input>
      <output id="output-route" name="route" typeRef="string"/>
      <rule id="de-high">
        <inputEntry id="de-high-country"><text>"DE"</text></inputEntry>
        <inputEntry id="de-high-amount"><text>&gt;= 5000</text></inputEntry>
        <outputEntry id="de-high-route"><text>"enterprise"</text></outputEntry>
      </rule>
      <rule id="de-low">
        <inputEntry id="de-low-country"><text>"DE"</text></inputEntry>
        <inputEntry id="de-low-amount"><text>[0..4999]</text></inputEntry>
        <outputEntry id="de-low-route"><text>"standard"</text></outputEntry>
      </rule>
      <rule id="pl-any">
        <inputEntry id="pl-any-country"><text>"PL"</text></inputEntry>
        <inputEntry id="pl-any-amount"><text>-</text></inputEntry>
        <outputEntry id="pl-any-route"><text>"standard"</text></outputEntry>
      </rule>
    </decisionTable>
  </decision>
</definitions>'''
