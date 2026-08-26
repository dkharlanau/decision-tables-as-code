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
from .validate import has_errors, validate_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dtac", description="Decision Tables as Code CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="Validate a decision table")
    validate_parser.add_argument("table")
    validate_parser.add_argument("--json", action="store_true", dest="json_output")

    eval_parser = sub.add_parser("eval", help="Evaluate facts against a decision table")
    eval_parser.add_argument("table")
    eval_parser.add_argument("--facts", required=True, help="JSON object or @path/to/facts.json")

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.table, args.json_output)
        if args.command == "eval":
            return _eval(args.table, args.facts)
        if args.command == "diff":
            return _diff(args.before, args.after)
        if args.command == "coverage":
            return _coverage(args.table, args.max_combinations)
        if args.command == "import":
            return _import(args.source, args.config, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _validate(path: str, json_output: bool) -> int:
    table = load_table(path)
    diagnostics = validate_table(table)
    if json_output:
        print(json.dumps([item.to_dict() for item in diagnostics], indent=2))
    elif not diagnostics:
        print(f"OK {table.id}: no validation findings")
    else:
        for item in diagnostics:
            print(f"{item.severity.upper():7} {item.code} {item.path}: {item.message}")
    return 1 if has_errors(diagnostics) else 0


def _eval(path: str, raw_facts: str) -> int:
    table = load_table(path)
    facts = _read_json_arg(raw_facts)
    if not isinstance(facts, dict):
        raise ValueError("--facts must resolve to a JSON object")
    result = evaluate(table, facts)
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


def _read_json_arg(value: str):
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


if __name__ == "__main__":
    raise SystemExit(main())
