import json
from pathlib import Path

from decision_tables_as_code.cli import main


ROOT = Path(__file__).parents[1]


def _write_invalid_table(path):
    path.write_text(
        """version: 1
id: invalid-overlap
hit_policy: unique
inputs:
  - name: country
    type: string
outputs:
  - name: route
    type: string
rules:
  - id: de
    when: {country: DE}
    then: {route: A}
  - id: dach
    when: {country: [DE, AT]}
    then: {route: B}
""",
        encoding="utf-8",
    )


def test_validate_sarif_writes_report_and_preserves_error_exit_code(tmp_path):
    table = tmp_path / "invalid.yaml"
    output = tmp_path / "dtac.sarif"
    _write_invalid_table(table)

    exit_code = main(["validate", str(table), "--format", "sarif", "--output", str(output)])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["version"] == "2.1.0"
    assert report["runs"][0]["results"][0]["ruleId"] == "DT032"


def test_validate_github_emits_workflow_annotation_and_error_exit_code(tmp_path, capsys):
    table = tmp_path / "invalid.yaml"
    _write_invalid_table(table)

    exit_code = main(["validate", str(table), "--format", "github"])
    rendered = capsys.readouterr().out

    assert exit_code == 1
    assert "::error" in rendered
    assert "DT032 Proven UNIQUE overlap" in rendered
    assert "rules[1]" in rendered


def test_legacy_json_flag_remains_supported(tmp_path, capsys):
    table = tmp_path / "invalid.yaml"
    _write_invalid_table(table)

    exit_code = main(["validate", str(table), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload[0]["code"] == "DT032"


def test_compatibility_writes_versioned_report_without_failing_by_default(tmp_path):
    output = tmp_path / "compatibility.json"

    exit_code = main([
        "compatibility",
        str(ROOT / "examples" / "order-routing.yaml"),
        str(ROOT / "examples" / "order-routing-v2.yaml"),
        "--output", str(output),
    ])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["format_version"] == 1
    assert report["provable"] is True
    assert report["changed"] is True
    assert report["changed_combinations"] == 1


def test_compatibility_fail_on_change_returns_one_for_proven_change(tmp_path):
    output = tmp_path / "compatibility.json"

    exit_code = main([
        "compatibility",
        str(ROOT / "examples" / "order-routing.yaml"),
        str(ROOT / "examples" / "order-routing-v2.yaml"),
        "--fail-on-change",
        "--output", str(output),
    ])

    assert exit_code == 1
    assert json.loads(output.read_text(encoding="utf-8"))["changed"] is True


def test_compatibility_fail_on_change_returns_two_when_proof_is_impossible(tmp_path):
    table = tmp_path / "no-domain.yaml"
    table.write_text(
        """version: 1
id: no-domain
inputs:
  - name: country
    type: string
outputs:
  - name: route
    type: string
rules:
  - id: de
    when: {country: DE}
    then: {route: A}
""",
        encoding="utf-8",
    )
    output = tmp_path / "compatibility.json"

    exit_code = main([
        "compatibility",
        str(table),
        str(table),
        "--fail-on-change",
        "--output", str(output),
    ])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 2
    assert report["provable"] is False
    assert report["blocking_reasons"][0]["code"] == "missing_finite_domain"
