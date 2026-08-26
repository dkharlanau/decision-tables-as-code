from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_tables_as_code.release import create_release_bundle, verify_release_bundle


ROOT = Path(__file__).parents[1]
TABLE = ROOT / "examples" / "order-routing.yaml"
SCENARIOS = ROOT / "examples" / "order-routing.scenarios.yaml"
BASELINE = ROOT / "examples" / "order-routing-v2.yaml"


def test_release_bundle_is_reproducible_and_self_verifying(tmp_path: Path):
    first = tmp_path / "release-a"
    second = tmp_path / "release-b"

    first_manifest = create_release_bundle(
        TABLE,
        first,
        scenarios_path=SCENARIOS,
        against_path=BASELINE,
        include_javascript=True,
    )
    second_manifest = create_release_bundle(
        TABLE,
        second,
        scenarios_path=SCENARIOS,
        against_path=BASELINE,
        include_javascript=True,
    )

    assert first_manifest == second_manifest
    assert _tree_bytes(first) == _tree_bytes(second)

    verification = verify_release_bundle(first)
    assert verification["ok"] is True
    assert verification["table_id"] == "order-routing"
    assert verification["verified_files"] == len(first_manifest["files"]) + 1

    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenarios"] == {
        "ok": True,
        "total": 5,
        "passed": 5,
        "failed": 0,
        "definition_path": "scenarios.yaml",
        "report_path": "evidence/scenario-report.json",
    }
    assert manifest["semantic_diff"]["changed"] is True
    assert manifest["semantic_diff"]["report_path"] == "evidence/semantic-diff.json"
    assert {item["kind"] for item in manifest["runtimes"]} == {
        "javascript-esm",
        "typescript-declaration",
    }
    assert (first / "SHA256SUMS").is_file()
    assert (first / "review.md").is_file()
    assert (first / "baseline.yaml").is_file()
    assert (first / "scenarios.yaml").is_file()


def test_release_verify_detects_modified_artifact(tmp_path: Path):
    bundle = tmp_path / "release"
    create_release_bundle(TABLE, bundle, scenarios_path=SCENARIOS)

    review = bundle / "review.md"
    review.write_text(review.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Checksum mismatch for review.md"):
        verify_release_bundle(bundle)


def test_release_verify_detects_modified_manifest(tmp_path: Path):
    bundle = tmp_path / "release"
    create_release_bundle(TABLE, bundle)

    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["table"]["name"] = "tampered"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA256SUMS mismatch for manifest.json"):
        verify_release_bundle(bundle)


def test_release_verify_detects_unexpected_file(tmp_path: Path):
    bundle = tmp_path / "release"
    create_release_bundle(TABLE, bundle)
    (bundle / "unexpected.txt").write_text("not declared\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected: unexpected.txt"):
        verify_release_bundle(bundle)


def test_release_build_refuses_failing_scenarios(tmp_path: Path):
    scenarios = tmp_path / "bad.scenarios.yaml"
    scenarios.write_text(
        """version: 1
table: order-routing
scenarios:
  - id: deliberately-wrong
    facts:
      country: DE
      customer_type: B2B
      order_value: 6000
    expect:
      outputs:
        route: wrong
        approval: wrong
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="failing scenarios: deliberately-wrong"):
        create_release_bundle(TABLE, tmp_path / "release", scenarios_path=scenarios)


def test_release_output_must_be_new_directory(tmp_path: Path):
    existing = tmp_path / "release"
    existing.mkdir()

    with pytest.raises(ValueError, match="output already exists"):
        create_release_bundle(TABLE, existing)


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
