from decision_tables_as_code.reporting import diagnostics_to_github_annotations, diagnostics_to_sarif, sarif_json
from decision_tables_as_code.validate import Diagnostic


def test_sarif_contains_rule_file_logical_path_and_severity():
    finding = Diagnostic("DT032", "error", "Rules overlap", "rules[1]")
    report = diagnostics_to_sarif([finding], "examples/rules.yaml")

    assert report["version"] == "2.1.0"
    run = report["runs"][0]
    assert run["tool"]["driver"]["rules"][0]["id"] == "DT032"
    result = run["results"][0]
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "examples/rules.yaml"
    assert result["locations"][0]["logicalLocations"][0]["name"] == "rules[1]"


def test_sarif_json_is_valid_json_shape_for_empty_findings():
    rendered = sarif_json([], "examples/rules.yaml")
    assert '"version": "2.1.0"' in rendered
    assert '"results": []' in rendered


def test_github_annotations_map_error_and_warning_commands():
    findings = [
        Diagnostic("DT031", "error", "same conditions, different outputs", "rules[2]"),
        Diagnostic("DT033", "warning", "fully shadowed", "rules[3]"),
    ]
    rendered = diagnostics_to_github_annotations(findings, "examples/rules.yaml")
    assert "::error file=examples/rules.yaml,title=DT031 Conflicting exact rules::rules[2]: same conditions" in rendered
    assert "::warning file=examples/rules.yaml,title=DT033 Shadowed FIRST rule::rules[3]: fully shadowed" in rendered


def test_github_annotation_escapes_workflow_command_characters():
    finding = Diagnostic("DT040", "error", "bad%value\nnext", "rules[1].when.country")
    rendered = diagnostics_to_github_annotations([finding], "folder/a,b:rules.yaml")
    assert "file=folder/a%2Cb%3Arules.yaml" in rendered
    assert "bad%25value%0Anext" in rendered
