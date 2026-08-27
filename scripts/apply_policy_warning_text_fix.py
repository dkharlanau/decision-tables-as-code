from pathlib import Path

cli = Path("decision_tables_as_code/cli.py")
text = cli.read_text(encoding="utf-8")
old = '''    if output_format == "json":
        rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\\n"
    elif report["ok"]:
        rendered = f"OK {table.id}: policies {', '.join(report['policy_ids'])} passed\\n"
    else:
        lines: list[str] = []
        for item in report["base_validation"]:
            lines.append(f"{item['severity'].upper():7} {item['code']} {item['path']}: {item['message']}\\n")
        for item in report["policy_diagnostics"]:
            lines.append(
                f"{item['severity'].upper():7} {item['code']} [{item['policy_id']}] {item['path']}: {item['message']}\\n"
            )
        rendered = "".join(lines)
'''
new = '''    if output_format == "json":
        rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\\n"
    elif report["base_validation"] or report["policy_diagnostics"]:
        lines: list[str] = []
        for item in report["base_validation"]:
            lines.append(f"{item['severity'].upper():7} {item['code']} {item['path']}: {item['message']}\\n")
        for item in report["policy_diagnostics"]:
            lines.append(
                f"{item['severity'].upper():7} {item['code']} [{item['policy_id']}] {item['path']}: {item['message']}\\n"
            )
        rendered = "".join(lines)
    else:
        rendered = f"OK {table.id}: policies {', '.join(report['policy_ids'])} passed\\n"
'''
if old not in text:
    raise SystemExit("expected policy-check rendering block not found")
cli.write_text(text.replace(old, new), encoding="utf-8")

tests = Path("tests/test_cli_reporting.py")
body = tests.read_text(encoding="utf-8")
addition = '''\n\ndef test_policy_check_text_shows_warning_findings_without_failing(tmp_path, capsys):
    table = tmp_path / "table.yaml"
    table.write_text(
        """version: 1
id: warning-table
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
    then: {route: eu}
""",
        encoding="utf-8",
    )
    policy = tmp_path / "warning-policy.yaml"
    policy.write_text(
        """version: 1
id: provenance-warning
severity: warning
rules:
  required_rule_fields: [owner]
""",
        encoding="utf-8",
    )

    exit_code = main(["policy-check", str(table), "--policy", str(policy)])
    rendered = capsys.readouterr().out

    assert exit_code == 0
    assert "WARNING" in rendered
    assert "POL004" in rendered
    assert "[provenance-warning]" in rendered
    assert "rules[0].owner" in rendered
    assert not rendered.startswith("OK ")


def test_policy_check_text_keeps_ok_for_zero_findings(tmp_path, capsys):
    table = tmp_path / "table.yaml"
    table.write_text(
        """version: 1
id: clean-table
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
    then: {route: eu}
""",
        encoding="utf-8",
    )
    policy = tmp_path / "clean-policy.yaml"
    policy.write_text(
        """version: 1
id: simple-policy
severity: warning
rules:
  max_rules: 10
""",
        encoding="utf-8",
    )

    exit_code = main(["policy-check", str(table), "--policy", str(policy)])
    rendered = capsys.readouterr().out

    assert exit_code == 0
    assert rendered == "OK clean-table: policies simple-policy passed\\n"
'''
if "test_policy_check_text_shows_warning_findings_without_failing" in body:
    raise SystemExit("regression tests already present")
tests.write_text(body + addition, encoding="utf-8")
