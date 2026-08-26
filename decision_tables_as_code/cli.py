from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .compatibility import analyze_compatibility
from .coverage import analyze_coverage
from .diff import semantic_diff
from .dmn import dumps_dmn, load_dmn, table_to_document
from .engine import evaluate
from .explain import explain_table
from .importer import dump_yaml, import_spreadsheet, load_import_config
from .inspect import inspect_table
from .io import load_table
from .javascript import generate_javascript, generate_typescript_declaration
from .model import table_from_mapping
from .package import (
    diff_packages,
    evaluate_package,
    impact_analysis,
    load_package,
    render_package_graph,
    validate_package,
)
from .release import create_release_bundle, verify_release_bundle
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

    explain_parser = sub.add_parser("explain", help="Explain why rules matched or were rejected")
    explain_parser.add_argument("table")
    explain_parser.add_argument("--facts", required=True, help="JSON object or @path/to/facts.json")
    explain_parser.add_argument("--as-of", help="Explicit YYYY-MM-DD date used for effective-dated rules")
    explain_parser.add_argument("--output", help="Write JSON explanation to a file instead of stdout")

    inspect_parser = sub.add_parser("inspect", help="Inspect a decision table as stable machine-readable JSON")
    inspect_parser.add_argument("table")
    inspect_parser.add_argument("--output", help="Write JSON inspection output to a file instead of stdout")

    diff_parser = sub.add_parser("diff", help="Create a classified semantic diff between two tables")
    diff_parser.add_argument("before")
    diff_parser.add_argument("after")
    diff_parser.add_argument("--output", help="Write JSON semantic diff to a file instead of stdout")
    diff_parser.add_argument(
        "--fail-on",
        choices=("any", "potentially-breaking", "breaking", "never"),
        default="any",
        help="Exit 1 for the selected change threshold; default preserves legacy behavior and fails on any change",
    )

    compatibility_parser = sub.add_parser("compatibility", help="Exhaustively prove behavioral equivalence over declared finite domains")
    compatibility_parser.add_argument("before")
    compatibility_parser.add_argument("after")
    compatibility_parser.add_argument("--as-of", help="Explicit YYYY-MM-DD date for effective-dated rules")
    compatibility_parser.add_argument("--max-combinations", type=int, default=10_000)
    compatibility_parser.add_argument("--max-witnesses", type=int, default=100)
    compatibility_parser.add_argument("--fail-on-change", action="store_true", help="Exit 1 when a proven behavior change exists; exit 2 when proof is impossible")
    compatibility_parser.add_argument("--output", help="Write versioned compatibility JSON to a file instead of stdout")

    coverage_parser = sub.add_parser("coverage", help="Evaluate finite input domains for gaps and ambiguity")
    coverage_parser.add_argument("table")
    coverage_parser.add_argument("--max-combinations", type=int, default=10_000)

    import_parser = sub.add_parser("import", help="Import a CSV/XLSX decision table using an explicit mapping config")
    import_parser.add_argument("source")
    import_parser.add_argument("--config", required=True)
    import_parser.add_argument("--output")

    dmn_import_parser = sub.add_parser("dmn-import", help="Import the supported DMN 1.4 decision-table subset")
    dmn_import_parser.add_argument("source")
    dmn_import_parser.add_argument("--decision", help="Decision id when the DMN document contains multiple decision tables")
    dmn_import_parser.add_argument("--output", help="Write canonical YAML to a file instead of stdout")

    dmn_export_parser = sub.add_parser("dmn-export", help="Export a representable canonical table as DMN 1.4")
    dmn_export_parser.add_argument("table")
    dmn_export_parser.add_argument("--model-namespace", help="DMN definitions namespace; defaults to a deterministic urn:dtac namespace")
    dmn_export_parser.add_argument("--output", help="Write DMN XML to a file instead of stdout")

    js_export_parser = sub.add_parser("js-export", help="Generate a dependency-free JavaScript ESM runtime")
    js_export_parser.add_argument("table")
    js_export_parser.add_argument("--output", help="Write JavaScript ESM to a file instead of stdout")
    js_export_parser.add_argument("--types-output", help="Also write a TypeScript declaration file")

    bundle_parser = sub.add_parser("bundle", help="Build a deterministic decision release bundle")
    bundle_parser.add_argument("table")
    bundle_parser.add_argument("--output", required=True, help="Output directory; must not already exist")
    bundle_parser.add_argument("--scenarios", help="Scenario pack to preserve and execute as release evidence")
    bundle_parser.add_argument("--against", help="Approved/baseline table for semantic change evidence")
    bundle_parser.add_argument("--javascript", action="store_true", help="Include generated JavaScript ESM and TypeScript declaration")

    bundle_verify_parser = sub.add_parser("bundle-verify", help="Verify release bundle checksums and semantic fingerprint")
    bundle_verify_parser.add_argument("bundle")
    bundle_verify_parser.add_argument("--output", help="Write verification JSON to a file instead of stdout")

    package_validate_parser = sub.add_parser("package-validate", help="Validate a multi-table decision package")
    package_validate_parser.add_argument("manifest")
    package_validate_parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    package_validate_parser.add_argument("--output", help="Write validation output to a file instead of stdout")

    package_eval_parser = sub.add_parser("package-eval", help="Evaluate a decision package in dependency order")
    package_eval_parser.add_argument("manifest")
    package_eval_parser.add_argument("--facts", required=True, help="JSON object or @path/to/facts.json")
    package_eval_parser.add_argument("--as-of", help="Explicit YYYY-MM-DD date passed to effective-dated tables")
    package_eval_parser.add_argument("--output", help="Write package result JSON to a file instead of stdout")

    package_graph_parser = sub.add_parser("package-graph", help="Render the decision dependency graph")
    package_graph_parser.add_argument("manifest")
    package_graph_parser.add_argument("--format", choices=("json", "dot", "mermaid"), default="json", dest="output_format")
    package_graph_parser.add_argument("--output", help="Write graph output to a file instead of stdout")

    package_impact_parser = sub.add_parser("package-impact", help="List downstream decisions impacted by changed tables")
    package_impact_parser.add_argument("manifest")
    package_impact_parser.add_argument("--changed", action="append", required=True, help="Changed table id; repeat for multiple tables")
    package_impact_parser.add_argument("--output", help="Write impact JSON to a file instead of stdout")

    package_diff_parser = sub.add_parser("package-diff", help="Compare package tables/dependencies and report downstream impact")
    package_diff_parser.add_argument("before")
    package_diff_parser.add_argument("after")
    package_diff_parser.add_argument("--output", help="Write package diff JSON to a file instead of stdout")
    package_diff_parser.add_argument("--fail-on", choices=("any", "never"), default="any")

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
        if args.command == "explain":
            return _explain(args.table, args.facts, args.as_of, args.output)
        if args.command == "inspect":
            return _inspect(args.table, args.output)
        if args.command == "diff":
            return _diff(args.before, args.after, args.output, args.fail_on)
        if args.command == "compatibility":
            return _compatibility(args.before, args.after, args.as_of, args.max_combinations, args.max_witnesses, args.fail_on_change, args.output)
        if args.command == "coverage":
            return _coverage(args.table, args.max_combinations)
        if args.command == "import":
            return _import(args.source, args.config, args.output)
        if args.command == "dmn-import":
            return _dmn_import(args.source, args.decision, args.output)
        if args.command == "dmn-export":
            return _dmn_export(args.table, args.model_namespace, args.output)
        if args.command == "js-export":
            return _js_export(args.table, args.output, args.types_output)
        if args.command == "bundle":
            return _bundle(args.table, args.output, args.scenarios, args.against, args.javascript)
        if args.command == "bundle-verify":
            return _bundle_verify(args.bundle, args.output)
        if args.command == "package-validate":
            return _package_validate(args.manifest, args.output_format, args.output)
        if args.command == "package-eval":
            return _package_eval(args.manifest, args.facts, args.as_of, args.output)
        if args.command == "package-graph":
            return _package_graph(args.manifest, args.output_format, args.output)
        if args.command == "package-impact":
            return _package_impact(args.manifest, args.changed, args.output)
        if args.command == "package-diff":
            return _package_diff(args.before, args.after, args.output, args.fail_on)
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

    return _emit(rendered, output_path, error_status=1 if has_errors(diagnostics) else 0)


def _eval(path: str, raw_facts: str, as_of: str | None = None) -> int:
    table = load_table(path)
    facts = _read_json_arg(raw_facts)
    if not isinstance(facts, dict):
        raise ValueError("--facts must resolve to a JSON object")
    result = evaluate(table, facts, as_of=as_of)
    print(json.dumps(asdict(result), indent=2, default=str))
    return 0


def _explain(path: str, raw_facts: str, as_of: str | None, output_path: str | None) -> int:
    facts = _read_json_arg(raw_facts)
    if not isinstance(facts, dict):
        raise ValueError("--facts must resolve to a JSON object")
    payload = json.dumps(explain_table(load_table(path), facts, as_of=as_of), indent=2, default=str) + "\n"
    return _emit(payload, output_path)


def _inspect(path: str, output_path: str | None = None) -> int:
    payload = json.dumps(inspect_table(load_table(path)), indent=2, default=str) + "\n"
    return _emit(payload, output_path)


def _diff(before_path: str, after_path: str, output_path: str | None = None, fail_on: str = "any") -> int:
    result = semantic_diff(load_table(before_path), load_table(after_path))
    payload = json.dumps(result.to_dict(), indent=2, default=str) + "\n"
    should_fail = {
        "any": result.changed,
        "potentially-breaking": result.classification in {"potentially_breaking", "breaking"},
        "breaking": result.classification == "breaking",
        "never": False,
    }[fail_on]
    return _emit(payload, output_path, error_status=1 if should_fail else 0)


def _compatibility(
    before_path: str,
    after_path: str,
    as_of: str | None,
    max_combinations: int,
    max_witnesses: int,
    fail_on_change: bool,
    output_path: str | None,
) -> int:
    report = analyze_compatibility(
        load_table(before_path),
        load_table(after_path),
        as_of=as_of,
        max_combinations=max_combinations,
        max_witnesses=max_witnesses,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    if fail_on_change:
        if not report["provable"]:
            status = 2
        elif report["changed"]:
            status = 1
        else:
            status = 0
    else:
        status = 0
    return _emit(rendered, output_path, error_status=status)


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
    return _emit(dump_yaml(document), output_path)


def _dmn_import(source: str, decision_id: str | None, output_path: str | None) -> int:
    table = load_dmn(source, decision_id=decision_id)
    diagnostics = validate_table(table)
    if has_errors(diagnostics):
        for item in diagnostics:
            print(f"{item.severity.upper():7} {item.code} {item.path}: {item.message}", file=sys.stderr)
        return 1
    return _emit(dump_yaml(table_to_document(table)), output_path)


def _dmn_export(table_path: str, model_namespace: str | None, output_path: str | None) -> int:
    return _emit(dumps_dmn(load_table(table_path), model_namespace=model_namespace), output_path)


def _js_export(table_path: str, output_path: str | None, types_output_path: str | None) -> int:
    table = load_table(table_path)
    rendered = generate_javascript(table)
    if types_output_path:
        Path(types_output_path).write_text(generate_typescript_declaration(table), encoding="utf-8")
        print(f"Wrote {types_output_path}")
    return _emit(rendered, output_path)


def _bundle(
    table_path: str,
    output_dir: str,
    scenarios_path: str | None,
    against_path: str | None,
    include_javascript: bool,
) -> int:
    manifest = create_release_bundle(
        table_path,
        output_dir,
        scenarios_path=scenarios_path,
        against_path=against_path,
        include_javascript=include_javascript,
    )
    print(json.dumps({
        "ok": True,
        "bundle": str(output_dir),
        "table_id": manifest["table"]["id"],
        "semantic_fingerprint": manifest["table"]["semantic_fingerprint"],
        "files": len(manifest["files"]),
    }, indent=2))
    return 0


def _bundle_verify(bundle_dir: str, output_path: str | None) -> int:
    payload = json.dumps(verify_release_bundle(bundle_dir), indent=2, sort_keys=True) + "\n"
    return _emit(payload, output_path)


def _package_validate(manifest_path: str, output_format: str, output_path: str | None) -> int:
    package = load_package(manifest_path)
    diagnostics = validate_package(package)
    if output_format == "json":
        rendered = json.dumps([item.to_dict() for item in diagnostics], indent=2) + "\n"
    elif not diagnostics:
        rendered = f"OK {package.id}: no package validation findings\n"
    else:
        rendered = "".join(
            f"{item.severity.upper():7} {item.code} {item.path}: {item.message}\n"
            for item in diagnostics
        )
    return _emit(rendered, output_path, error_status=1 if has_errors(diagnostics) else 0)


def _package_eval(manifest_path: str, raw_facts: str, as_of: str | None, output_path: str | None) -> int:
    facts = _read_json_arg(raw_facts)
    if not isinstance(facts, dict):
        raise ValueError("--facts must resolve to a JSON object")
    result = evaluate_package(load_package(manifest_path), facts, as_of=as_of)
    payload = json.dumps(result.to_dict(), indent=2, default=str) + "\n"
    return _emit(payload, output_path)


def _package_graph(manifest_path: str, output_format: str, output_path: str | None) -> int:
    rendered = render_package_graph(load_package(manifest_path), output_format)
    return _emit(rendered, output_path)


def _package_impact(manifest_path: str, changed: list[str], output_path: str | None) -> int:
    payload = json.dumps(impact_analysis(load_package(manifest_path), changed), indent=2, default=str) + "\n"
    return _emit(payload, output_path)


def _package_diff(before_path: str, after_path: str, output_path: str | None, fail_on: str) -> int:
    payload = diff_packages(load_package(before_path), load_package(after_path))
    rendered = json.dumps(payload, indent=2, default=str) + "\n"
    should_fail = payload["changed"] and fail_on == "any"
    return _emit(rendered, output_path, error_status=1 if should_fail else 0)


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
    return _emit(rendered, output_path)


def _emit(content: str, output_path: str | None, *, error_status: int = 0) -> int:
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(content, end="")
    return error_status


def _read_json_arg(value: str):
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


if __name__ == "__main__":
    raise SystemExit(main())