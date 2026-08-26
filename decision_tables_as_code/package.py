from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from .diff import semantic_diff
from .engine import evaluate
from .io import load_document, load_table
from .model import DecisionTable
from .validate import Diagnostic, has_errors, validate_table


@dataclass(frozen=True)
class PackageDependency:
    table: str
    bind: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageTableSpec:
    id: str
    path: str
    depends_on: tuple[PackageDependency, ...] = ()


@dataclass(frozen=True)
class LoadedPackageTable:
    spec: PackageTableSpec
    table: DecisionTable
    source_path: Path


@dataclass(frozen=True)
class DecisionPackage:
    id: str
    version: int
    manifest_path: Path
    entries: tuple[LoadedPackageTable, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageTableResult:
    id: str
    facts: Mapping[str, Any]
    matched_rule_ids: tuple[str, ...]
    outputs: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "facts": dict(self.facts),
            "matched_rule_ids": list(self.matched_rule_ids),
            "outputs": self.outputs,
        }


@dataclass(frozen=True)
class PackageEvaluationResult:
    package_id: str
    order: tuple[str, ...]
    table_results: tuple[PackageTableResult, ...]
    terminal_outputs: Mapping[str, Any]
    as_of: str | None = None
    overridden_fact_keys: tuple[str, ...] = ()
    unused_fact_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "package_id": self.package_id,
            "order": list(self.order),
            "as_of": self.as_of,
            "tables": {item.id: item.to_dict() for item in self.table_results},
            "terminal_outputs": dict(self.terminal_outputs),
            "overridden_fact_keys": list(self.overridden_fact_keys),
            "unused_fact_keys": list(self.unused_fact_keys),
        }


def load_package(path: str | Path) -> DecisionPackage:
    source = Path(path)
    raw = load_document(source)
    return package_from_mapping(raw, source)


def package_from_mapping(raw: Mapping[str, Any], manifest_path: str | Path) -> DecisionPackage:
    version = raw.get("version", 1)
    if not isinstance(version, int):
        raise ValueError("package version must be an integer")

    package_id = raw.get("id")
    if not isinstance(package_id, str) or not package_id.strip():
        raise ValueError("package id must be a non-empty string")

    raw_tables = raw.get("tables")
    if not isinstance(raw_tables, list):
        raise ValueError("package tables must be an array")

    metadata = raw.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise ValueError("package metadata must be an object")

    source = Path(manifest_path)
    base = source.parent
    entries: list[LoadedPackageTable] = []
    for index, raw_entry in enumerate(raw_tables):
        spec = _table_spec_from_mapping(raw_entry, index)
        table_path = (base / spec.path).resolve()
        entries.append(LoadedPackageTable(spec, load_table(table_path), table_path))

    return DecisionPackage(
        id=package_id,
        version=version,
        manifest_path=source.resolve(),
        entries=tuple(entries),
        metadata=dict(metadata),
    )


def validate_package(package: DecisionPackage) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if package.version != 1:
        diagnostics.append(Diagnostic("PK001", "error", f"Unsupported package version {package.version}", "version"))
    if not package.entries:
        diagnostics.append(Diagnostic("PK002", "error", "Package must contain at least one table", "tables"))
        return diagnostics

    id_positions: dict[str, list[int]] = {}
    for index, entry in enumerate(package.entries):
        id_positions.setdefault(entry.spec.id, []).append(index)
    duplicate_ids = {table_id for table_id, positions in id_positions.items() if len(positions) > 1}
    for table_id in sorted(duplicate_ids):
        diagnostics.append(Diagnostic(
            "PK003",
            "error",
            f"Duplicate package table id {table_id!r}",
            f"tables[{id_positions[table_id][-1]}].id",
        ))

    for index, entry in enumerate(package.entries):
        if entry.table.id != entry.spec.id:
            diagnostics.append(Diagnostic(
                "PK004",
                "error",
                f"Manifest id {entry.spec.id!r} does not match table id {entry.table.id!r}",
                f"tables[{index}].id",
            ))
        for item in validate_table(entry.table):
            diagnostics.append(Diagnostic(
                item.code,
                item.severity,
                item.message,
                f"tables[{index}].table.{item.path}",
            ))

    if duplicate_ids:
        return diagnostics

    entries = {entry.spec.id: entry for entry in package.entries}
    for index, entry in enumerate(package.entries):
        dependency_ids: set[str] = set()
        bound_inputs: dict[str, str] = {}
        for dep_index, dependency in enumerate(entry.spec.depends_on):
            dep_path = f"tables[{index}].depends_on[{dep_index}]"
            if dependency.table in dependency_ids:
                diagnostics.append(Diagnostic(
                    "PK010",
                    "error",
                    f"Duplicate dependency on {dependency.table!r}",
                    f"{dep_path}.table",
                ))
            dependency_ids.add(dependency.table)

            if dependency.table == entry.spec.id:
                diagnostics.append(Diagnostic(
                    "PK011",
                    "error",
                    "A table cannot depend on itself",
                    f"{dep_path}.table",
                ))
                continue
            upstream = entries.get(dependency.table)
            if upstream is None:
                diagnostics.append(Diagnostic(
                    "PK012",
                    "error",
                    f"Dependency references unknown table {dependency.table!r}",
                    f"{dep_path}.table",
                ))
                continue

            if dependency.bind and upstream.table.hit_policy == "collect":
                diagnostics.append(Diagnostic(
                    "PK013",
                    "error",
                    f"Cannot bind outputs from COLLECT table {dependency.table!r}; a binding requires one output object",
                    f"{dep_path}.bind",
                ))

            upstream_outputs = {item.name: item for item in upstream.table.outputs}
            downstream_inputs = {item.name: item for item in entry.table.inputs}
            for local_input, upstream_output in dependency.bind.items():
                bind_path = f"{dep_path}.bind.{local_input}"
                if local_input in bound_inputs:
                    diagnostics.append(Diagnostic(
                        "PK014",
                        "error",
                        f"Input {local_input!r} is already bound from dependency {bound_inputs[local_input]!r}",
                        bind_path,
                    ))
                else:
                    bound_inputs[local_input] = dependency.table

                local_definition = downstream_inputs.get(local_input)
                if local_definition is None:
                    diagnostics.append(Diagnostic(
                        "PK015",
                        "error",
                        f"Binding targets unknown input {local_input!r} on table {entry.spec.id!r}",
                        bind_path,
                    ))
                upstream_definition = upstream_outputs.get(upstream_output)
                if upstream_definition is None:
                    diagnostics.append(Diagnostic(
                        "PK016",
                        "error",
                        f"Binding references unknown output {upstream_output!r} on table {dependency.table!r}",
                        bind_path,
                    ))
                if local_definition is not None and upstream_definition is not None:
                    if not _types_compatible(upstream_definition.type, local_definition.type):
                        diagnostics.append(Diagnostic(
                            "PK017",
                            "error",
                            f"Cannot bind {dependency.table}.{upstream_output} ({upstream_definition.type}) to "
                            f"{entry.spec.id}.{local_input} ({local_definition.type})",
                            bind_path,
                        ))

    if not any(item.code in {"PK010", "PK011", "PK012"} and item.severity == "error" for item in diagnostics):
        cycle = _find_cycle(package)
        if cycle:
            diagnostics.append(Diagnostic(
                "PK020",
                "error",
                "Dependency cycle detected: " + " -> ".join(cycle),
                "tables",
            ))
    return diagnostics


def topological_order(package: DecisionPackage) -> tuple[str, ...]:
    _ensure_valid(package)
    return _topological_order_unchecked(package)


def evaluate_package(
    package: DecisionPackage,
    facts: Mapping[str, Any],
    *,
    as_of: str | date | datetime | None = None,
) -> PackageEvaluationResult:
    _ensure_valid(package)
    if not isinstance(facts, Mapping):
        raise ValueError("Package facts must be an object/mapping")

    order = _topological_order_unchecked(package)
    entries = {entry.spec.id: entry for entry in package.entries}
    results: dict[str, PackageTableResult] = {}
    bound_input_names: set[str] = set()
    externally_consumed: set[str] = set()

    for table_id in order:
        entry = entries[table_id]
        local_bound = {
            local_input
            for dependency in entry.spec.depends_on
            for local_input in dependency.bind
        }
        bound_input_names.update(local_bound)
        local_facts = {
            name: facts[name]
            for name in entry.table.input_names
            if name in facts and name not in local_bound
        }
        externally_consumed.update(local_facts)

        for dependency in entry.spec.depends_on:
            if not dependency.bind:
                continue
            upstream_result = results[dependency.table]
            if upstream_result.outputs is None:
                raise ValueError(
                    f"Dependency table {dependency.table!r} produced no output, but {table_id!r} requires bound inputs"
                )
            if not isinstance(upstream_result.outputs, Mapping):
                raise ValueError(
                    f"Dependency table {dependency.table!r} did not produce one output object; cannot bind into {table_id!r}"
                )
            for local_input, upstream_output in dependency.bind.items():
                if upstream_output not in upstream_result.outputs:
                    raise ValueError(
                        f"Dependency table {dependency.table!r} did not produce output {upstream_output!r}"
                    )
                local_facts[local_input] = upstream_result.outputs[upstream_output]

        decision = evaluate(entry.table, local_facts, as_of=as_of)
        results[table_id] = PackageTableResult(
            id=table_id,
            facts=local_facts,
            matched_rule_ids=decision.matched_rule_ids,
            outputs=decision.outputs,
        )

    terminal_ids = _terminal_table_ids(package)
    terminal_outputs = {table_id: results[table_id].outputs for table_id in terminal_ids}
    supplied_keys = set(facts)
    return PackageEvaluationResult(
        package_id=package.id,
        order=order,
        table_results=tuple(results[table_id] for table_id in order),
        terminal_outputs=terminal_outputs,
        as_of=_date_text(as_of),
        overridden_fact_keys=tuple(sorted(supplied_keys & bound_input_names)),
        unused_fact_keys=tuple(sorted(supplied_keys - externally_consumed - bound_input_names)),
    )


def package_graph(package: DecisionPackage) -> dict[str, Any]:
    _ensure_valid(package)
    order = _topological_order_unchecked(package)
    entries = {entry.spec.id: entry for entry in package.entries}
    edges: list[dict[str, Any]] = []
    for target_id in order:
        entry = entries[target_id]
        for dependency in entry.spec.depends_on:
            edges.append({
                "from": dependency.table,
                "to": target_id,
                "bind": dict(sorted(dependency.bind.items())),
            })
    return {
        "format_version": 1,
        "package_id": package.id,
        "order": list(order),
        "nodes": [
            {
                "id": table_id,
                "path": entries[table_id].spec.path,
                "hit_policy": entries[table_id].table.hit_policy,
                "inputs": list(entries[table_id].table.input_names),
                "outputs": list(entries[table_id].table.output_names),
            }
            for table_id in order
        ],
        "edges": edges,
    }


def render_package_graph(package: DecisionPackage, output_format: str) -> str:
    graph = package_graph(package)
    if output_format == "json":
        return json.dumps(graph, indent=2, default=str) + "\n"
    if output_format == "dot":
        lines = [f'digraph "{_dot_escape(package.id)}" {{']
        for node in graph["nodes"]:
            lines.append(f'  "{_dot_escape(node["id"])}";')
        for edge in graph["edges"]:
            label = _binding_label(edge["bind"])
            suffix = f' [label="{_dot_escape(label)}"]' if label else ""
            lines.append(
                f'  "{_dot_escape(edge["from"])}" -> "{_dot_escape(edge["to"])}"{suffix};'
            )
        lines.append("}")
        return "\n".join(lines) + "\n"
    if output_format == "mermaid":
        node_ids = {node["id"]: _mermaid_node_id(node["id"]) for node in graph["nodes"]}
        lines = ["flowchart LR"]
        for node in graph["nodes"]:
            lines.append(f'  {node_ids[node["id"]]}["{_mermaid_escape(node["id"])}"]')
        for edge in graph["edges"]:
            label = _binding_label(edge["bind"])
            if label:
                lines.append(
                    f'  {node_ids[edge["from"]]} -->|"{_mermaid_escape(label)}"| {node_ids[edge["to"]]}'
                )
            else:
                lines.append(f'  {node_ids[edge["from"]]} --> {node_ids[edge["to"]]}')
        return "\n".join(lines) + "\n"
    raise ValueError("output_format must be json, dot, or mermaid")


def impact_analysis(package: DecisionPackage, changed_table_ids: list[str] | tuple[str, ...]) -> dict[str, Any]:
    _ensure_valid(package)
    changed = _dedupe(changed_table_ids)
    known = {entry.spec.id for entry in package.entries}
    unknown = [table_id for table_id in changed if table_id not in known]
    if unknown:
        raise ValueError("Unknown changed table ids: " + ", ".join(unknown))

    order = _topological_order_unchecked(package)
    downstream = _descendants(package, set(changed)) - set(changed)
    affected = set(changed) | downstream
    return {
        "format_version": 1,
        "package_id": package.id,
        "changed": [table_id for table_id in order if table_id in changed],
        "downstream_impacted": [table_id for table_id in order if table_id in downstream],
        "all_affected": [table_id for table_id in order if table_id in affected],
    }


def diff_packages(before: DecisionPackage, after: DecisionPackage) -> dict[str, Any]:
    _ensure_valid(before)
    _ensure_valid(after)
    if before.id != after.id:
        raise ValueError(f"Cannot diff packages with different ids: {before.id!r} vs {after.id!r}")

    before_entries = {entry.spec.id: entry for entry in before.entries}
    after_entries = {entry.spec.id: entry for entry in after.entries}
    before_ids = set(before_entries)
    after_ids = set(after_entries)
    added = after_ids - before_ids
    removed = before_ids - after_ids
    shared = before_ids & after_ids

    table_changes: dict[str, Any] = {}
    dependency_changed: set[str] = set()
    semantic_changed: set[str] = set()
    for table_id in sorted(shared):
        table_diff = semantic_diff(before_entries[table_id].table, after_entries[table_id].table)
        if table_diff.changed:
            semantic_changed.add(table_id)
            table_changes[table_id] = table_diff.to_dict()
        if _dependency_signature(before_entries[table_id].spec) != _dependency_signature(after_entries[table_id].spec):
            dependency_changed.add(table_id)

    changed_ids = added | removed | semantic_changed | dependency_changed
    downstream = set()
    downstream |= _descendants(after, (changed_ids & after_ids))
    downstream |= _descendants(before, (changed_ids & before_ids))
    downstream -= changed_ids

    after_order = _topological_order_unchecked(after)
    before_order = _topological_order_unchecked(before)
    ordered_changed = [table_id for table_id in after_order if table_id in changed_ids]
    ordered_changed.extend(table_id for table_id in before_order if table_id in removed and table_id not in ordered_changed)
    ordered_downstream = [table_id for table_id in after_order if table_id in downstream]
    ordered_downstream.extend(
        table_id for table_id in before_order if table_id in downstream and table_id not in ordered_downstream
    )

    changed = bool(changed_ids or before.metadata != after.metadata)
    return {
        "format_version": 1,
        "package_id": before.id,
        "changed": changed,
        "added_tables": [table_id for table_id in after_order if table_id in added],
        "removed_tables": [table_id for table_id in before_order if table_id in removed],
        "semantic_changed_tables": [table_id for table_id in after_order if table_id in semantic_changed],
        "dependency_changed_tables": [table_id for table_id in after_order if table_id in dependency_changed],
        "changed_table_ids": ordered_changed,
        "downstream_impacted": ordered_downstream,
        "all_affected": ordered_changed + [item for item in ordered_downstream if item not in ordered_changed],
        "metadata_changed": before.metadata != after.metadata,
        "table_changes": table_changes,
    }


def _table_spec_from_mapping(raw: Any, index: int) -> PackageTableSpec:
    if not isinstance(raw, Mapping):
        raise ValueError(f"package tables[{index}] must be an object")
    table_id = raw.get("id")
    path = raw.get("path")
    if not isinstance(table_id, str) or not table_id.strip():
        raise ValueError(f"package tables[{index}].id must be a non-empty string")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"package tables[{index}].path must be a non-empty string")

    raw_dependencies = raw.get("depends_on", [])
    if raw_dependencies is None:
        raw_dependencies = []
    if not isinstance(raw_dependencies, list):
        raise ValueError(f"package tables[{index}].depends_on must be an array")

    dependencies: list[PackageDependency] = []
    for dep_index, raw_dependency in enumerate(raw_dependencies):
        if not isinstance(raw_dependency, Mapping):
            raise ValueError(
                f"package tables[{index}].depends_on[{dep_index}] must be an object"
            )
        dependency_id = raw_dependency.get("table")
        if not isinstance(dependency_id, str) or not dependency_id.strip():
            raise ValueError(
                f"package tables[{index}].depends_on[{dep_index}].table must be a non-empty string"
            )
        raw_bind = raw_dependency.get("bind", {})
        if raw_bind is None:
            raw_bind = {}
        if not isinstance(raw_bind, Mapping):
            raise ValueError(
                f"package tables[{index}].depends_on[{dep_index}].bind must be an object"
            )
        bind: dict[str, str] = {}
        for local_input, upstream_output in raw_bind.items():
            if not isinstance(local_input, str) or not local_input.strip():
                raise ValueError("package dependency bind keys must be non-empty strings")
            if not isinstance(upstream_output, str) or not upstream_output.strip():
                raise ValueError("package dependency bind values must be non-empty strings")
            bind[local_input] = upstream_output
        dependencies.append(PackageDependency(dependency_id, bind))

    return PackageTableSpec(table_id, path, tuple(dependencies))


def _ensure_valid(package: DecisionPackage) -> None:
    diagnostics = validate_package(package)
    if has_errors(diagnostics):
        errors = [item for item in diagnostics if item.severity == "error"]
        preview = "; ".join(f"{item.code} {item.path}: {item.message}" for item in errors[:5])
        if len(errors) > 5:
            preview += f"; ... {len(errors) - 5} more errors"
        raise ValueError(f"Invalid decision package: {preview}")


def _topological_order_unchecked(package: DecisionPackage) -> tuple[str, ...]:
    manifest_order = [entry.spec.id for entry in package.entries]
    order_index = {table_id: index for index, table_id in enumerate(manifest_order)}
    dependencies = {
        entry.spec.id: {dependency.table for dependency in entry.spec.depends_on}
        for entry in package.entries
    }
    dependents: dict[str, set[str]] = {table_id: set() for table_id in manifest_order}
    for target, upstreams in dependencies.items():
        for upstream in upstreams:
            dependents.setdefault(upstream, set()).add(target)

    ready = sorted(
        (table_id for table_id in manifest_order if not dependencies[table_id]),
        key=order_index.__getitem__,
    )
    result: list[str] = []
    while ready:
        table_id = ready.pop(0)
        result.append(table_id)
        for dependent in sorted(dependents.get(table_id, ()), key=order_index.__getitem__):
            dependencies[dependent].discard(table_id)
            if not dependencies[dependent] and dependent not in ready and dependent not in result:
                ready.append(dependent)
                ready.sort(key=order_index.__getitem__)
    if len(result) != len(manifest_order):
        cycle = _find_cycle(package)
        raise ValueError("Dependency cycle detected: " + " -> ".join(cycle or ("unknown",)))
    return tuple(result)


def _find_cycle(package: DecisionPackage) -> tuple[str, ...] | None:
    graph = {
        entry.spec.id: [dependency.table for dependency in entry.spec.depends_on]
        for entry in package.entries
    }
    known = set(graph)
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> tuple[str, ...] | None:
        state[node] = 1
        stack.append(node)
        for dependency in graph.get(node, []):
            if dependency not in known:
                continue
            if state.get(dependency, 0) == 0:
                found = visit(dependency)
                if found:
                    return found
            elif state.get(dependency) == 1:
                start = stack.index(dependency)
                return tuple(stack[start:] + [dependency])
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None


def _descendants(package: DecisionPackage, roots: set[str] | list[str] | tuple[str, ...]) -> set[str]:
    dependents: dict[str, set[str]] = {entry.spec.id: set() for entry in package.entries}
    for entry in package.entries:
        for dependency in entry.spec.depends_on:
            dependents.setdefault(dependency.table, set()).add(entry.spec.id)
    seen: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        for downstream in dependents.get(current, ()):
            if downstream not in seen:
                seen.add(downstream)
                queue.append(downstream)
    return seen


def _terminal_table_ids(package: DecisionPackage) -> tuple[str, ...]:
    depended_on = {
        dependency.table
        for entry in package.entries
        for dependency in entry.spec.depends_on
    }
    order = _topological_order_unchecked(package)
    return tuple(table_id for table_id in order if table_id not in depended_on)


def _types_compatible(upstream_type: str, downstream_type: str) -> bool:
    if upstream_type == "any" or downstream_type == "any":
        return True
    if upstream_type == downstream_type:
        return True
    return upstream_type == "integer" and downstream_type == "number"


def _dependency_signature(spec: PackageTableSpec) -> tuple[Any, ...]:
    return tuple(
        (dependency.table, tuple(sorted(dependency.bind.items())))
        for dependency in spec.depends_on
    )


def _binding_label(bind: Mapping[str, str]) -> str:
    return ", ".join(
        f"{upstream_output} -> {local_input}"
        for local_input, upstream_output in sorted(bind.items())
    )


def _dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _date_text(value: str | date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _mermaid_node_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return "n_" + digest


def _mermaid_escape(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ")
