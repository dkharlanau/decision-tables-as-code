import json

from decision_tables_as_code.cli import main


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
