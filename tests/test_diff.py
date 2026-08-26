from pathlib import Path

from decision_tables_as_code.diff import semantic_diff
from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping


ROOT = Path(__file__).parents[1]


def test_semantic_diff_reports_changed_rule_with_versioned_contract():
    result = semantic_diff(
        load_table(ROOT / "examples" / "order-routing.yaml"),
        load_table(ROOT / "examples" / "order-routing-v2.yaml"),
    )
    changed_ids = [item["id"] for item in result.changed_rules]
    payload = result.to_dict()

    assert "de-b2b-high" in changed_ids
    assert payload["format_version"] == 1
    assert payload["changed"] is True
    assert payload["classification"] == "potentially_breaking"
    assert payload["summary"]["potentially_breaking"] >= 1


def test_output_contract_removal_is_breaking():
    before = _table(outputs=[{"name": "route", "type": "string"}])
    after = _table(outputs=[])

    result = semantic_diff(before, after)

    assert result.classification == "breaking"
    assert result.breaking is True
    assert any(
        item["path"] == "outputs.route" and item["classification"] == "breaking"
        for item in result.classifications
    )


def test_governance_only_rule_change_is_not_semantic_break():
    before = _table(owner="Order Management")
    after = _table(owner="Enterprise Architecture")

    result = semantic_diff(before, after)

    assert result.classification == "governance_only"
    assert result.breaking is False


def test_no_changes_classifies_as_none():
    table = _table()
    result = semantic_diff(table, table)
    assert result.to_dict()["classification"] == "none"
    assert result.to_dict()["changed"] is False


def _table(*, outputs=None, owner=None):
    outputs = [{"name": "route", "type": "string"}] if outputs is None else outputs
    then = {item["name"]: "standard" for item in outputs}
    rule = {
        "id": "default",
        "when": {"country": "DE"},
        "then": then,
    }
    if owner is not None:
        rule["owner"] = owner
    return table_from_mapping({
        "version": 1,
        "id": "routing",
        "hit_policy": "unique",
        "inputs": [{"name": "country", "type": "string"}],
        "outputs": outputs,
        "rules": [rule],
    })
