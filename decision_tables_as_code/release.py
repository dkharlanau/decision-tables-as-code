from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .diff import semantic_diff
from .importer import dump_yaml
from .inspect import inspect_table
from .io import load_table
from .javascript import generate_javascript, generate_typescript_declaration
from .render import render_markdown, table_fingerprint
from .scenarios import load_scenarios, run_scenarios
from .validate import has_errors, validate_table


BUNDLE_FORMAT_VERSION = 1
_RESERVED_PATHS = {"manifest.json", "SHA256SUMS"}


def create_release_bundle(
    table_path: str | Path,
    output_dir: str | Path,
    *,
    scenarios_path: str | Path | None = None,
    against_path: str | Path | None = None,
    include_javascript: bool = False,
) -> dict[str, Any]:
    """Create a deterministic, self-verifying decision release directory."""
    table = load_table(table_path)
    diagnostics = validate_table(table)
    if has_errors(diagnostics):
        errors = "; ".join(
            f"{item.code} {item.path}: {item.message}"
            for item in diagnostics
            if item.severity == "error"
        )
        raise ValueError(f"Cannot create release bundle for an invalid table: {errors}")

    output = Path(output_dir)
    if output.exists():
        raise ValueError(f"Release bundle output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    scenario_document: Mapping[str, Any] | None = None
    scenario_report = None
    if scenarios_path is not None:
        scenario_document = load_scenarios(scenarios_path)
        scenario_report = run_scenarios(table, scenario_document)
        if not scenario_report.ok:
            failed = [item.id for item in scenario_report.results if not item.passed]
            raise ValueError(
                "Cannot create release bundle with failing scenarios: " + ", ".join(failed)
            )

    baseline = load_table(against_path) if against_path is not None else None
    diff = semantic_diff(baseline, table) if baseline is not None else None

    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temporary:
        root = Path(temporary)
        _write_text(root, "table.yaml", dump_yaml(_plain(asdict(table))))
        _write_json(root, "evidence/validation.json", [item.to_dict() for item in diagnostics])
        _write_json(root, "evidence/inspect.json", inspect_table(table))

        if scenario_document is not None and scenario_report is not None:
            _write_text(root, "scenarios.yaml", dump_yaml(_plain(dict(scenario_document))))
            _write_json(root, "evidence/scenario-report.json", scenario_report.to_dict())

        if baseline is not None and diff is not None:
            _write_text(root, "baseline.yaml", dump_yaml(_plain(asdict(baseline))))
            _write_json(root, "evidence/semantic-diff.json", diff.to_dict())

        _write_text(root, "review.md", render_markdown(table, diagnostics, diff=diff))

        runtimes: list[dict[str, Any]] = []
        if include_javascript:
            js_path = "runtime/decision.mjs"
            types_path = "runtime/decision.d.ts"
            _write_text(root, js_path, generate_javascript(table))
            _write_text(root, types_path, generate_typescript_declaration(table))
            runtimes.extend([
                {"kind": "javascript-esm", "path": js_path},
                {"kind": "typescript-declaration", "path": types_path},
            ])

        file_records = _artifact_records(root)
        by_path = {item["path"]: item for item in file_records}
        for runtime in runtimes:
            runtime.update({
                "sha256": by_path[runtime["path"]]["sha256"],
                "bytes": by_path[runtime["path"]]["bytes"],
            })

        severity_counts: dict[str, int] = {}
        for item in diagnostics:
            severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1

        manifest: dict[str, Any] = {
            "format_version": BUNDLE_FORMAT_VERSION,
            "bundle_type": "decision-table-release",
            "table": {
                "id": table.id,
                "name": table.name,
                "format_version": table.version,
                "hit_policy": table.hit_policy,
                "semantic_fingerprint": table_fingerprint(table),
            },
            "validation": {
                "ok": not has_errors(diagnostics),
                "finding_count": len(diagnostics),
                "severity_counts": dict(sorted(severity_counts.items())),
                "path": "evidence/validation.json",
            },
            "scenarios": (
                {
                    "ok": scenario_report.ok,
                    "total": scenario_report.total,
                    "passed": scenario_report.passed,
                    "failed": scenario_report.failed,
                    "definition_path": "scenarios.yaml",
                    "report_path": "evidence/scenario-report.json",
                }
                if scenario_report is not None
                else None
            ),
            "semantic_diff": (
                {
                    "changed": diff.changed,
                    "classification": diff.classification,
                    "baseline_fingerprint": table_fingerprint(baseline),
                    "baseline_path": "baseline.yaml",
                    "report_path": "evidence/semantic-diff.json",
                }
                if diff is not None and baseline is not None
                else None
            ),
            "review": {"path": "review.md"},
            "provenance": [
                {
                    "rule_id": rule.id,
                    "owner": rule.owner,
                    "source": rule.source,
                    "ticket": rule.ticket,
                    "rationale": rule.rationale,
                    "effective_from": rule.effective_from,
                    "effective_to": rule.effective_to,
                    "metadata": _plain(dict(rule.metadata)),
                }
                for rule in table.rules
                if any((
                    rule.owner,
                    rule.source,
                    rule.ticket,
                    rule.rationale,
                    rule.effective_from,
                    rule.effective_to,
                    rule.metadata,
                ))
            ],
            "runtimes": runtimes,
            "files": file_records,
        }
        _write_json(root, "manifest.json", manifest)

        checksum_records = [
            *file_records,
            _file_record(root, "manifest.json", allow_reserved=True),
        ]
        checksum_text = "".join(
            f'{item["sha256"]}  {item["path"]}\n'
            for item in sorted(checksum_records, key=lambda item: item["path"])
        )
        _write_text(root, "SHA256SUMS", checksum_text)

        root.replace(output)

    return manifest


def verify_release_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    """Verify declared files, checksums, semantic fingerprint, and unexpected files."""
    root = Path(bundle_dir)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Release bundle must be a real directory")
    _reject_symlinks(root)

    manifest_path = root / "manifest.json"
    sums_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise ValueError("Release bundle must contain manifest.json and SHA256SUMS")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format_version") != BUNDLE_FORMAT_VERSION:
        raise ValueError("Unsupported or invalid release bundle manifest")
    if manifest.get("bundle_type") != "decision-table-release":
        raise ValueError("Unsupported release bundle type")

    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("manifest.files must be an array")

    expected_artifacts: set[str] = set()
    for index, raw in enumerate(raw_files):
        if not isinstance(raw, dict):
            raise ValueError(f"manifest.files[{index}] must be an object")
        relative = raw.get("path")
        expected_hash = raw.get("sha256")
        expected_bytes = raw.get("bytes")
        _validate_relative_bundle_path(relative)
        if relative in _RESERVED_PATHS:
            raise ValueError(f"manifest.files cannot declare reserved path {relative!r}")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError(f"manifest.files[{index}].sha256 is invalid")
        if not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise ValueError(f"manifest.files[{index}].bytes is invalid")
        if relative in expected_artifacts:
            raise ValueError(f"Duplicate manifest file path {relative!r}")
        expected_artifacts.add(relative)
        actual = _file_record(root, relative)
        if actual["sha256"] != expected_hash:
            raise ValueError(f"Checksum mismatch for {relative}")
        if actual["bytes"] != expected_bytes:
            raise ValueError(f"Size mismatch for {relative}")

    actual_artifacts = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in _RESERVED_PATHS:
            actual_artifacts.add(relative)
    if actual_artifacts != expected_artifacts:
        missing = sorted(expected_artifacts - actual_artifacts)
        extra = sorted(actual_artifacts - expected_artifacts)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        raise ValueError("Bundle file set mismatch (" + "; ".join(details) + ")")

    declared_sums = _parse_checksum_file(sums_path.read_text(encoding="utf-8"))
    expected_sum_paths = expected_artifacts | {"manifest.json"}
    if set(declared_sums) != expected_sum_paths:
        raise ValueError("SHA256SUMS file set does not match manifest")
    for relative, expected_hash in declared_sums.items():
        actual_hash = _sha256_file(root / relative)
        if actual_hash != expected_hash:
            raise ValueError(f"SHA256SUMS mismatch for {relative}")

    table = load_table(root / "table.yaml")
    declared_fingerprint = manifest.get("table", {}).get("semantic_fingerprint")
    actual_fingerprint = table_fingerprint(table)
    if declared_fingerprint != actual_fingerprint:
        raise ValueError("Canonical table semantic fingerprint does not match manifest")

    return {
        "format_version": 1,
        "ok": True,
        "table_id": table.id,
        "semantic_fingerprint": actual_fingerprint,
        "verified_files": len(expected_artifacts) + 1,
        "manifest_sha256": _sha256_file(manifest_path),
    }


def _artifact_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in _RESERVED_PATHS:
            continue
        records.append(_file_record(root, relative))
    return records


def _file_record(root: Path, relative: str, *, allow_reserved: bool = False) -> dict[str, Any]:
    _validate_relative_bundle_path(relative)
    if relative in _RESERVED_PATHS and not allow_reserved:
        raise ValueError(f"Reserved bundle path cannot be an artifact: {relative}")
    path = root / relative
    if path.is_symlink():
        raise ValueError(f"Bundle file must not be a symlink: {relative}")
    if not path.is_file():
        raise ValueError(f"Bundle file is missing: {relative}")
    return {
        "path": relative,
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _sha256_file(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"Bundle checksum target must not be a symlink: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(root: Path, relative: str, content: str) -> None:
    _validate_relative_bundle_path(relative)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_json(root: Path, relative: str, payload: Any) -> None:
    rendered = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ) + "\n"
    _write_text(root, relative, rendered)


def _parse_checksum_file(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line:
            continue
        if "  " not in line:
            raise ValueError(f"Invalid SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        _validate_relative_bundle_path(relative)
        if relative == "SHA256SUMS":
            raise ValueError("SHA256SUMS must not contain a checksum for itself")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"Invalid SHA256SUMS digest on line {line_number}")
        if relative in result:
            raise ValueError(f"Duplicate SHA256SUMS path {relative!r}")
        result[relative] = digest
    return result


def _reject_symlinks(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(
                "Release bundle must not contain symlinks: "
                + path.relative_to(root).as_posix()
            )


def _validate_relative_bundle_path(value: Any) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Invalid bundle-relative path {value!r}")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError(f"Invalid bundle-relative path {value!r}")


def _plain(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))
