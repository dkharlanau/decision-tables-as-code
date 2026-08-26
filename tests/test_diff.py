from pathlib import Path

from decision_tables_as_code.diff import semantic_diff
from decision_tables_as_code.io import load_table


ROOT = Path(__file__).parents[1]


def test_semantic_diff_reports_changed_rule():
    result = semantic_diff(
        load_table(ROOT / "examples" / "order-routing.yaml"),
        load_table(ROOT / "examples" / "order-routing-v2.yaml"),
    )
    changed_ids = [item["id"] for item in result.changed_rules]
    assert "de-b2b-high" in changed_ids
