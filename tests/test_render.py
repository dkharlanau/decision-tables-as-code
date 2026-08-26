from pathlib import Path

from decision_tables_as_code.coverage import analyze_coverage
from decision_tables_as_code.diff import semantic_diff
from decision_tables_as_code.io import load_table
from decision_tables_as_code.render import render_html, render_markdown, rule_anchor, table_fingerprint
from decision_tables_as_code.validate import validate_table


ROOT = Path(__file__).parents[1]


def test_markdown_report_contains_matrix_diagnostics_and_stable_anchor():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    report = render_markdown(table, validate_table(table), coverage=analyze_coverage(table))
    assert "## Rule matrix" in report
    assert "Coverage: `100.0%`" in report
    assert rule_anchor("de-b2b-high") in report
    assert table_fingerprint(table) in report


def test_html_report_is_standalone_and_navigable():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    report = render_html(table, validate_table(table), coverage=analyze_coverage(table))
    assert report.startswith("<!doctype html>")
    assert "<style>" in report
    assert 'class="table-wrap"' in report
    assert f'id="{rule_anchor("pl-all")}"' in report


def test_diff_report_marks_changed_rule_and_removed_summary():
    before = load_table(ROOT / "examples" / "order-routing.yaml")
    after = load_table(ROOT / "examples" / "order-routing-v2.yaml")
    diff = semantic_diff(before, after)
    report = render_markdown(after, validate_table(after), diff=diff)
    assert "Changed rules: `1`" in report
    assert "de-b2b-high" in report
    assert "changed" in report


def test_semantic_fingerprint_is_deterministic():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    assert table_fingerprint(table) == table_fingerprint(table)
    assert len(table_fingerprint(table)) == 64
