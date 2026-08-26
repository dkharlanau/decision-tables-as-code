from pathlib import Path

from decision_tables_as_code.io import load_table
from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.scenarios import load_scenarios, run_scenarios


ROOT = Path(__file__).parents[1]


def test_example_scenario_pack_passes():
    report = run_scenarios(
        load_table(ROOT / "examples" / "order-routing.yaml"),
        load_scenarios(ROOT / "examples" / "order-routing.scenarios.yaml"),
    )
    assert report.ok
    assert report.total == 5
    assert report.passed == 5


def test_effective_dated_scenario_pack_passes_with_explicit_dates():
    report = run_scenarios(
        load_table(ROOT / "examples" / "effective-routing.yaml"),
        load_scenarios(ROOT / "examples" / "effective-routing.scenarios.yaml"),
    )
    assert report.ok
    assert report.total == 4
    assert report.results[0].actual["as_of"] == "2026-12-31"
    assert report.results[1].actual["as_of"] == "2027-01-01"


def test_scenario_reports_output_mismatch():
    table = table_from_mapping({
        "version": 1,
        "id": "simple",
        "inputs": [{"name": "country"}],
        "outputs": [{"name": "result"}],
        "rules": [{"id": "de", "when": {"country": "DE"}, "then": {"result": "A"}}],
    })
    report = run_scenarios(table, {
        "version": 1,
        "scenarios": [{
            "id": "wrong",
            "facts": {"country": "DE"},
            "expect": {"outputs": {"result": "B"}},
        }],
    })
    assert not report.ok
    assert "outputs expected" in report.results[0].message


def test_scenario_can_expect_engine_error():
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
    report = run_scenarios(table, {
        "version": 1,
        "scenarios": [{
            "id": "ambiguity",
            "facts": {"country": "DE"},
            "expect": {"error": "UNIQUE hit policy violated"},
        }],
    })
    assert report.ok
