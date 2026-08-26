from pathlib import Path

from decision_tables_as_code.coverage import analyze_coverage
from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping


EXAMPLE = Path(__file__).parents[1] / "examples" / "order-routing.yaml"


def test_example_has_complete_finite_domain_coverage():
    report = analyze_coverage(load_table(EXAMPLE))
    assert report.evaluated_combinations == 8
    assert report.coverage_percent == 100.0
    assert report.uncovered == ()
    assert report.ambiguous == ()


def test_coverage_reports_gap():
    table = table_from_mapping({
        "version": 1,
        "id": "gap",
        "inputs": [{"name": "country", "domain": ["DE", "PL"]}],
        "outputs": [{"name": "result"}],
        "rules": [{"id": "de", "when": {"country": "DE"}, "then": {"result": "A"}}],
    })
    report = analyze_coverage(table)
    assert report.coverage_percent == 50.0
    assert report.uncovered == ({"country": "PL"},)
