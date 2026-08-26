from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .coverage import analyze_coverage
from .diff import semantic_diff
from .engine import evaluate
from .importer import dump_yaml, import_spreadsheet, load_import_config
from .io import load_table
from .model import table_from_mapping
from .render import render_html, render_markdown
from .reporting import diagnostics_to_github_annotations, sarif_json
from .scenarios import load_scenarios, run_scenarios
from .validate import has_errors, validate_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dtac", description="Decision Tables as Code CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="Validate a decision table")
    validate_parser.add_argument("table")
    validate_parser.add_argument("--format", choices=("text", "json", "sarif", "github"), default="text", dest="output_format")
    validate_parser.add_argument("--output", help="Write validation output to a file instead of stdout")
    validate_parser.add_argument("--json", action="store_true", dest="legacy_json", help=argparse.SUPPRESS)

    eval_parser = sub.add_parser("eval", help="Evaluate facts against a decision table")
    eval_parser.add_argument("table")
    eval_parser.add_argument("--facts", required=True, help="JSON object or @path/to/facts.json")
    eval_parser.add_argument("--as-of", help="Explicit YYYY-MM-DD date used for effective-dated rules")

    diff_parser = sub.add_parser("diff", help="Create a semantic diff between two tables")
    diff_parser.add_argument("before")
    diff_parser.add_argument("after")

    coverage_parser = sub.add_parser("coverage", help="Evaluate finite input domains for gaps and ambiguity")
    coverage_parser.add_argument("table")
    coverage_parser.add_argument("--max-combinations", type=int, default=10_000)

    import_parser = sub.add_parser("import", help="Import a CSV/XLSX decision table using an explicit mapping config")
    import_parser.add_argument("source")
    import_parser.add_argument("--config", required=True)
    import_parser.add_argument("--output")

    test_parser = sub.add_parser("test", help="Run executable decision scenarios")
    test_parser.add_argument("table")
    test_parser.add_argument("scenarios")
    test_parser.add_argument("--json", action="store_true", dest="json_output")

    render_parser = sub.add_parser("render", help="Render a business-review report")
    render_parser.add_argument("table")
    render_parser.add_argument("--format", choices=("markdown", "html"), default="markdown")
    render_parser.add_argument("--output")
    render_parser.add_argument("--coverage", action="store_true")
    render_parser.add_argument("--against", help="Previous table version for semantic change highlighting")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.table, args.output_format, args.output, args.legacy_json)
        if args.command == "eval":
            return _eval(args.table, args.facts, args.as_of)
        if args.command == "diff":
            return _diff(args.before, args.after)
        if args.command == "coverage":
            return _coverage(args.table, args.max_combinations)
        if args.command == "import":
            return _import(args.source, args.config, args.output)
        if args.command == "test":
            return _test(args.table, args.scenarios, args.json_output)
        if args.command == "render":
            return _render(args.table, args.format, args.output, args.coverage, args.against)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _validate(path: str, output_format: str, output_path: str | None, legacy_json: bool = False) -> int:
    if legacy_json:
        if output_format != "text":
            raise ValueError("Use either --json or --format, not both")
        output_format = "json"

    table = load_table(path)
    diagnostics = validate_table(table)

    if output_format == "json":
        rendered = json.dumps([item.to_dict() for item in diagnostics], indent=2) + "\n"
    elif output_format == "sarif":
        rendered = sarif_json(diagnostics, path)
    elif output_format == "github":
        rendered = diagnostics_to_github_annotations(diagnostics, path)
    elif not diagnostics:
        rendered = f"OK {table.id}: no validation findings\n"
    else:
        rendered = "".join(
            f"{item.severity.upper():7} {item.code} {item.path}: {item.message}\n"
            for item in diagnostics
        )

    if output_path:
        Path(output_path).write_text(rendered, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(rendered, end="")
    return 1 if has_errors(diagnostics) else 0


def _eval(path: str, raw_facts: str, as_of: str | None = None) -> int:
    table = load_table(path)
    facts = _read_json_arg(raw_facts)
    if not isinstance(facts, dict):
        raise ValueError("--facts must resolve to a JSON object")
    result = evaluate(table, facts, as_of=as_of)
    print(json.dumps(asdict(result), indent=2, default=str))
    return 0


def _diff(before_path: str, after_path: str) -> int:
    result = semantic_diff(load_table(before_path), load_table(after_path))
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 1 if result.changed else 0


def _coverage(path: str, max_combinations: int) -> int:
    result = analyze_coverage(load_table(path), max_combinations=max_combinations)
    payload = {
        "evaluated_combinations": result.evaluated_combinations,
        "covered_combinations": result.covered_combinations,
        "coverage_percent": result.coverage_percent,
        "uncovered": result.uncovered,
        "ambiguous": result.ambiguous,
    }
    print(json.dumps(payload, indent=2, default=str))
    return 1 if result.uncovered or result.ambiguous else 0


def _import(source: str, config_path: str, output_path: str | None) -> int:
    document = import_spreadsheet(source, load_import_config(config_path))
    table = table_from_mapping(document)
    diagnostics = validate_table(table)
    if has_errors(diagnostics):
        for item in diagnostics:
            print(f"{item.severity.upper():7} {item.code} {item.path}: {item.message}", file=sys.stderr)
        return 1
    rendered = dump_yaml(document)
    if output_path:
        Path(output_path).write_text(rendered, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(rendered, end="")
    return 0


def _test(table_path: str, scenario_path: str, json_output: bool) -> int:
    report = run_scenarios(load_table(table_path), load_scenarios(scenario_path))
    if json_output:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        for result in report.results:
            marker = "PASS" if result.passed else "FAIL"
            print(f"{marker:4} {result.id}: {result.message}")
        print(f"{report.passed}/{report.total} scenarios passed")
    return 0 if report.ok else 1


def _render(table_path: str, output_format: str, output_path: str | None, include_coverage: bool, against_path: str | None) -> int:
    table = load_table(table_path)
    diagnostics = validate_table(table)
    coverage = analyze_coverage(table) if include_coverage else None
    diff = semantic_diff(load_table(against_path), table) if against_path else None
    if output_format == "html":
        rendered = render_html(table, diagnostics, coverage=coverage, diff=diff)
    else:
        rendered = render_markdown(table, diagnostics, coverage=coverage, diff=diff)
    if output_path:
        Path(output_path).write_text(rendered, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(rendered, end="")
    return 0


def _read_json_arg(value: str):
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


if __name__ == "__main__":
    raise SystemExit(main())
