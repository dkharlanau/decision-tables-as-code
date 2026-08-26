from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.package import (
    DecisionPackage,
    LoadedPackageTable,
    PackageDependency,
    PackageTableSpec,
    diff_packages,
    evaluate_package,
    impact_analysis,
    load_package,
    package_graph,
    render_package_graph,
    topological_order,
    validate_package,
)


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "package" / "order-approval" / "package.yaml"


def test_example_package_validates_and_has_stable_topological_order():
    package = load_package(EXAMPLE)

    diagnostics = validate_package(package)

    assert not [item for item in diagnostics if item.severity == "error"]
    assert topological_order(package) == (
        "risk-classification",
        "approval-decision",
        "fulfillment-route",
    )


def test_package_evaluation_feeds_outputs_into_downstream_inputs():
    package = load_package(EXAMPLE)

    result = evaluate_package(package, {
        "customer_tier": "VIP",
        "blocked": False,
        "amount": 500,
        "region": "EU",
    })
    payload = result.to_dict()

    assert payload["order"] == ["risk-classification", "approval-decision", "fulfillment-route"]
    assert payload["tables"]["risk-classification"]["outputs"] == {"risk_level": "LOW"}
    assert payload["tables"]["approval-decision"]["facts"]["risk_level"] == "LOW"
    assert payload["tables"]["approval-decision"]["outputs"] == {"strategy": "L1"}
    assert payload["tables"]["fulfillment-route"]["facts"]["approval_strategy"] == "L1"
    assert payload["terminal_outputs"] == {"fulfillment-route": {"queue": "EU_AUTO"}}


def test_bound_dependency_output_overrides_same_named_external_fact_and_reports_it():
    package = load_package(EXAMPLE)

    result = evaluate_package(package, {
        "customer_tier": "VIP",
        "blocked": False,
        "amount": 500,
        "region": "EU",
        "risk_level": "HIGH",
    })

    assert result.to_dict()["tables"]["approval-decision"]["facts"]["risk_level"] == "LOW"
    assert result.overridden_fact_keys == ("risk_level",)


def test_package_graph_has_bindings_and_multiple_render_formats():
    package = load_package(EXAMPLE)
    graph = package_graph(package)

    assert graph["order"] == ["risk-classification", "approval-decision", "fulfillment-route"]
    assert graph["edges"] == [
        {"from": "risk-classification", "to": "approval-decision", "bind": {"risk_level": "risk_level"}},
        {"from": "approval-decision", "to": "fulfillment-route", "bind": {"approval_strategy": "strategy"}},
    ]

    dot = render_package_graph(package, "dot")
    mermaid = render_package_graph(package, "mermaid")
    assert '"risk-classification" -> "approval-decision"' in dot
    assert "risk_level -> risk_level" in dot
    assert mermaid.startswith("flowchart LR\n")
    assert "strategy -> approval_strategy" in mermaid


def test_impact_analysis_is_transitive():
    package = load_package(EXAMPLE)

    risk_impact = impact_analysis(package, ["risk-classification"])
    approval_impact = impact_analysis(package, ["approval-decision"])

    assert risk_impact["downstream_impacted"] == ["approval-decision", "fulfillment-route"]
    assert risk_impact["all_affected"] == ["risk-classification", "approval-decision", "fulfillment-route"]
    assert approval_impact["downstream_impacted"] == ["fulfillment-route"]


def test_cycle_is_reported_as_package_error():
    table_a = _simple_table("a", "out_a")
    table_b = _simple_table("b", "out_b")
    package = DecisionPackage(
        id="cycle",
        version=1,
        manifest_path=Path("package.yaml"),
        entries=(
            LoadedPackageTable(
                PackageTableSpec("a", "a.yaml", (PackageDependency("b", {}),)),
                table_a,
                Path("a.yaml"),
            ),
            LoadedPackageTable(
                PackageTableSpec("b", "b.yaml", (PackageDependency("a", {}),)),
                table_b,
                Path("b.yaml"),
            ),
        ),
    )

    diagnostics = validate_package(package)

    assert any(item.code == "PK020" and item.severity == "error" for item in diagnostics)
    assert "a -> b -> a" in next(item.message for item in diagnostics if item.code == "PK020")


def test_missing_dependency_and_bad_bindings_fail_validation():
    upstream = _simple_table("upstream", "out")
    downstream = table_from_mapping({
        "version": 1,
        "id": "downstream",
        "inputs": [{"name": "wanted", "type": "string"}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "r", "when": {"wanted": "A"}, "then": {"result": "ok"}}],
    })
    package = DecisionPackage(
        id="bad",
        version=1,
        manifest_path=Path("package.yaml"),
        entries=(
            LoadedPackageTable(PackageTableSpec("upstream", "upstream.yaml"), upstream, Path("upstream.yaml")),
            LoadedPackageTable(
                PackageTableSpec(
                    "downstream",
                    "downstream.yaml",
                    (
                        PackageDependency("missing", {}),
                        PackageDependency("upstream", {"unknown_input": "missing_output"}),
                    ),
                ),
                downstream,
                Path("downstream.yaml"),
            ),
        ),
    )

    codes = {item.code for item in validate_package(package) if item.severity == "error"}

    assert {"PK012", "PK015", "PK016"} <= codes


def test_incompatible_binding_types_fail_validation():
    upstream = table_from_mapping({
        "version": 1,
        "id": "upstream",
        "inputs": [{"name": "x", "type": "string"}],
        "outputs": [{"name": "score", "type": "number"}],
        "rules": [{"id": "r", "when": {}, "then": {"score": 1.5}}],
    })
    downstream = table_from_mapping({
        "version": 1,
        "id": "downstream",
        "inputs": [{"name": "category", "type": "string"}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "r", "when": {}, "then": {"result": "ok"}}],
    })
    package = DecisionPackage(
        id="types",
        version=1,
        manifest_path=Path("package.yaml"),
        entries=(
            LoadedPackageTable(PackageTableSpec("upstream", "upstream.yaml"), upstream, Path("upstream.yaml")),
            LoadedPackageTable(
                PackageTableSpec(
                    "downstream",
                    "downstream.yaml",
                    (PackageDependency("upstream", {"category": "score"}),),
                ),
                downstream,
                Path("downstream.yaml"),
            ),
        ),
    )

    assert any(item.code == "PK017" for item in validate_package(package))


def test_package_diff_lists_downstream_impact_for_changed_upstream_table():
    before = load_package(EXAMPLE)
    entries = list(before.entries)
    risk_index = next(index for index, entry in enumerate(entries) if entry.spec.id == "risk-classification")
    risk = entries[risk_index].table
    changed_risk = replace(
        risk,
        rules=tuple(
            replace(rule, then={"risk_level": "MEDIUM"}) if rule.id == "vip" else rule
            for rule in risk.rules
        ),
    )
    entries[risk_index] = replace(entries[risk_index], table=changed_risk)
    after = replace(before, entries=tuple(entries))

    result = diff_packages(before, after)

    assert result["changed"] is True
    assert result["semantic_changed_tables"] == ["risk-classification"]
    assert result["downstream_impacted"] == ["approval-decision", "fulfillment-route"]
    assert result["all_affected"] == ["risk-classification", "approval-decision", "fulfillment-route"]
    assert result["table_changes"]["risk-classification"]["classification"] == "potentially_breaking"


def _simple_table(table_id: str, output_name: str):
    return table_from_mapping({
        "version": 1,
        "id": table_id,
        "inputs": [{"name": "x", "type": "string"}],
        "outputs": [{"name": output_name, "type": "string"}],
        "rules": [{"id": "r", "when": {}, "then": {output_name: "value"}}],
    })
