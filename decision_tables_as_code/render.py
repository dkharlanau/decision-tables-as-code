from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict
from typing import Any, Iterable

from .coverage import CoverageReport
from .diff import TableDiff
from .model import DecisionTable, Rule
from .validate import Diagnostic


def table_fingerprint(table: DecisionTable) -> str:
    payload = json.dumps(asdict(table), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rule_anchor(rule_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", rule_id.lower()).strip("-") or "rule"
    suffix = hashlib.sha1(rule_id.encode("utf-8")).hexdigest()[:8]
    return f"rule-{slug}-{suffix}"


def render_markdown(
    table: DecisionTable,
    diagnostics: Iterable[Diagnostic] = (),
    *,
    coverage: CoverageReport | None = None,
    diff: TableDiff | None = None,
) -> str:
    diagnostics = tuple(diagnostics)
    status = _rule_statuses(table, diff)
    lines: list[str] = [
        f"# {table.name}",
        "",
        table.description or f"Decision table `{table.id}`.",
        "",
        "## Summary",
        "",
        f"- Table ID: `{table.id}`",
        f"- Format version: `{table.version}`",
        f"- Hit policy: `{table.hit_policy}`",
        f"- Rules: `{len(table.rules)}`",
        f"- Semantic fingerprint: `{table_fingerprint(table)}`",
    ]
    if table.metadata:
        lines.extend(["", "## Metadata", ""])
        for key in sorted(table.metadata):
            lines.append(f"- **{_md_escape(str(key))}:** `{_md_escape(_format_value(table.metadata[key]))}`")

    if coverage is not None:
        lines.extend([
            "",
            "## Coverage",
            "",
            f"- Evaluated combinations: `{coverage.evaluated_combinations}`",
            f"- Covered combinations: `{coverage.covered_combinations}`",
            f"- Coverage: `{coverage.coverage_percent}%`",
            f"- Uncovered combinations: `{len(coverage.uncovered)}`",
            f"- Ambiguous combinations: `{len(coverage.ambiguous)}`",
        ])

    if diff is not None:
        lines.extend([
            "",
            "## Change summary",
            "",
            f"- Added rules: `{len(diff.added_rules)}`",
            f"- Removed rules: `{len(diff.removed_rules)}`",
            f"- Changed rules: `{len(diff.changed_rules)}`",
            f"- Changed table properties: `{len(diff.changed_properties)}`",
        ])
        if diff.removed_rules:
            lines.append(f"- Removed rule IDs: {', '.join(f'`{_md_escape(item)}`' for item in diff.removed_rules)}")

    lines.extend(["", "## Rule matrix", ""])
    headers = ["Rule", "Priority"] + [_display_name(item.name) for item in table.inputs] + [_display_name(item.name) for item in table.outputs]
    if diff is not None:
        headers.append("Change")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for rule in table.rules:
        anchor = rule_anchor(rule.id)
        cells = [
            f'<a id="{anchor}"></a> **{_md_escape(rule.id)}**',
            "" if rule.priority is None else str(rule.priority),
        ]
        cells.extend(_md_escape(_format_condition(rule.when.get(item.name, _ABSENT))) for item in table.inputs)
        cells.extend(_md_escape(_format_value(rule.then.get(item.name, _ABSENT))) for item in table.outputs)
        if diff is not None:
            cells.append(status.get(rule.id, "unchanged"))
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## Rule index", ""])
    for rule in table.rules:
        lines.append(f"- [{_md_escape(rule.id)}](#{rule_anchor(rule.id)})")

    governed_rules = [(rule, _rule_governance_items(rule)) for rule in table.rules]
    governed_rules = [(rule, items) for rule, items in governed_rules if items]
    if governed_rules:
        lines.extend(["", "## Rule governance", ""])
        for rule, items in governed_rules:
            lines.extend([f"### {_md_escape(rule.id)}", ""])
            for label, value in items:
                lines.append(f"- **{_md_escape(label)}:** `{_md_escape(_format_value(value))}`")
            lines.append("")

    lines.extend(["", "## Diagnostics", ""])
    if not diagnostics:
        lines.append("No validation findings.")
    else:
        for item in diagnostics:
            lines.append(f"- **{item.severity.upper()} {item.code}** `{_md_escape(item.path)}` — {_md_escape(item.message)}")

    return "\n".join(lines).rstrip() + "\n"


def render_html(
    table: DecisionTable,
    diagnostics: Iterable[Diagnostic] = (),
    *,
    coverage: CoverageReport | None = None,
    diff: TableDiff | None = None,
) -> str:
    diagnostics = tuple(diagnostics)
    status = _rule_statuses(table, diff)
    headers = ["Rule", "Priority"] + [_display_name(item.name) for item in table.inputs] + [_display_name(item.name) for item in table.outputs]
    if diff is not None:
        headers.append("Change")

    rows: list[str] = []
    for rule in table.rules:
        cells = [
            f'<th scope="row"><a class="rule-link" id="{rule_anchor(rule.id)}" href="#{rule_anchor(rule.id)}">{html.escape(rule.id)}</a></th>',
            f"<td>{'' if rule.priority is None else rule.priority}</td>",
        ]
        cells.extend(f"<td><code>{html.escape(_format_condition(rule.when.get(item.name, _ABSENT)))}</code></td>" for item in table.inputs)
        cells.extend(f"<td><code>{html.escape(_format_value(rule.then.get(item.name, _ABSENT)))}</code></td>" for item in table.outputs)
        if diff is not None:
            change = status.get(rule.id, "unchanged")
            cells.append(f'<td><span class="change {html.escape(change)}">{html.escape(change)}</span></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")

    metadata = "".join(
        f"<dt>{html.escape(str(key))}</dt><dd>{html.escape(_format_value(table.metadata[key]))}</dd>"
        for key in sorted(table.metadata)
    ) or "<dt>Metadata</dt><dd>None</dd>"

    diagnostics_html = "".join(
        f'<li class="diagnostic {html.escape(item.severity)}"><strong>{html.escape(item.severity.upper())} {html.escape(item.code)}</strong> '
        f'<code>{html.escape(item.path)}</code><span>{html.escape(item.message)}</span></li>'
        for item in diagnostics
    ) or "<li>No validation findings.</li>"

    coverage_html = ""
    if coverage is not None:
        coverage_html = f"""
<section id="coverage">
  <h2>Coverage</h2>
  <div class="metrics">
    {_metric("Coverage", f"{coverage.coverage_percent}%")}
    {_metric("Evaluated", coverage.evaluated_combinations)}
    {_metric("Uncovered", len(coverage.uncovered))}
    {_metric("Ambiguous", len(coverage.ambiguous))}
  </div>
</section>"""

    diff_html = ""
    if diff is not None:
        removed = "".join(f"<li><code>{html.escape(item)}</code></li>" for item in diff.removed_rules) or "<li>None</li>"
        diff_html = f"""
<section id="changes">
  <h2>Change summary</h2>
  <div class="metrics">
    {_metric("Added", len(diff.added_rules))}
    {_metric("Removed", len(diff.removed_rules))}
    {_metric("Changed", len(diff.changed_rules))}
    {_metric("Table properties", len(diff.changed_properties))}
  </div>
  <details><summary>Removed rules</summary><ul>{removed}</ul></details>
</section>"""

    governance_cards: list[str] = []
    for rule in table.rules:
        items = _rule_governance_items(rule)
        if not items:
            continue
        detail_html = "".join(
            f"<dt>{html.escape(label)}</dt><dd>{html.escape(_format_value(value))}</dd>"
            for label, value in items
        )
        governance_cards.append(
            f'<article class="governance-card"><h3><a href="#{rule_anchor(rule.id)}">{html.escape(rule.id)}</a></h3><dl>{detail_html}</dl></article>'
        )
    governance_html = ""
    if governance_cards:
        governance_html = f"""
<section id="governance">
  <h2>Rule governance</h2>
  <div class="governance-grid">{''.join(governance_cards)}</div>
</section>"""

    index_html = "".join(
        f'<a href="#{rule_anchor(rule.id)}">{html.escape(rule.id)}</a>' for rule in table.rules
    )
    header_cells = "".join(f"<th scope=\"col\">{html.escape(value)}</th>" for value in headers)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(table.name)} — Decision Tables as Code</title>
<style>
:root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color-scheme: light dark; }}
body {{ margin: 0; line-height: 1.5; }}
main {{ max-width: 1440px; margin: 0 auto; padding: 32px 24px 64px; }}
h1 {{ margin-bottom: 4px; }} h2 {{ margin-top: 36px; }}
.subtle {{ opacity: .72; }}
.summary, .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
.card {{ border: 1px solid currentColor; border-radius: 10px; padding: 12px 14px; }}
.card strong {{ display: block; font-size: 1.25rem; overflow-wrap: anywhere; }}
dl {{ display: grid; grid-template-columns: minmax(120px, 220px) 1fr; gap: 6px 16px; }} dt {{ font-weight: 700; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
.rule-index {{ display: flex; gap: 8px; flex-wrap: wrap; }} .rule-index a {{ border: 1px solid currentColor; border-radius: 999px; padding: 4px 9px; text-decoration: none; }}
.table-wrap {{ overflow: auto; border: 1px solid currentColor; border-radius: 10px; max-height: 70vh; }}
table {{ border-collapse: collapse; width: max-content; min-width: 100%; }} th, td {{ border-bottom: 1px solid currentColor; padding: 9px 12px; text-align: left; vertical-align: top; }} thead th {{ position: sticky; top: 0; background: Canvas; z-index: 2; }} tbody th {{ position: sticky; left: 0; background: Canvas; z-index: 1; }}
code {{ white-space: nowrap; }} .rule-link {{ color: inherit; }}
.governance-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }}
.governance-card {{ border: 1px solid currentColor; border-radius: 10px; padding: 14px; }} .governance-card h3 {{ margin-top: 0; }}
.change {{ font-weight: 700; }} .diagnostic {{ margin-bottom: 8px; }} .diagnostic span {{ margin-left: 8px; }}
footer {{ margin-top: 40px; font-size: .9rem; opacity: .7; }}
</style>
</head>
<body>
<main>
<header>
  <p class="subtle">Decision Tables as Code review artifact</p>
  <h1>{html.escape(table.name)}</h1>
  <p>{html.escape(table.description or f'Decision table {table.id}.')}</p>
</header>
<section id="summary">
  <h2>Summary</h2>
  <div class="summary">
    {_metric("Table ID", table.id)}
    {_metric("Hit policy", table.hit_policy)}
    {_metric("Rules", len(table.rules))}
    {_metric("Fingerprint", table_fingerprint(table))}
  </div>
</section>
<section id="metadata"><h2>Metadata</h2><dl>{metadata}</dl></section>
{coverage_html}
{diff_html}
<section id="rules">
  <h2>Rule matrix</h2>
  <details><summary>Rule index ({len(table.rules)})</summary><nav class="rule-index">{index_html}</nav></details>
  <div class="table-wrap"><table><thead><tr>{header_cells}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</section>
{governance_html}
<section id="diagnostics"><h2>Diagnostics</h2><ul>{diagnostics_html}</ul></section>
<footer>Semantic fingerprint: <code>{table_fingerprint(table)}</code></footer>
</main>
</body>
</html>
"""


def _rule_statuses(table: DecisionTable, diff: TableDiff | None) -> dict[str, str]:
    if diff is None:
        return {}
    statuses = {rule.id: "unchanged" for rule in table.rules}
    for rule_id in diff.added_rules:
        statuses[rule_id] = "added"
    for item in diff.changed_rules:
        statuses[item["id"]] = "changed"
    return statuses


def _rule_governance_items(rule: Rule) -> list[tuple[str, Any]]:
    values = [
        ("Owner", rule.owner),
        ("Source", rule.source),
        ("Ticket", rule.ticket),
        ("Rationale", rule.rationale),
        ("Effective from", rule.effective_from),
        ("Effective to", rule.effective_to),
    ]
    items = [(label, value) for label, value in values if value is not None]
    if rule.metadata:
        items.append(("Metadata", dict(rule.metadata)))
    return items


def _format_condition(value: Any) -> str:
    if isinstance(value, _Absent):
        return "—"
    if value == "*":
        return "*"
    if isinstance(value, list):
        return "in(" + ", ".join(_format_value(item) for item in value) + ")"
    if isinstance(value, dict):
        operator_labels = {
            "eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
        }
        parts: list[str] = []
        for key in sorted(value):
            item = value[key]
            if key in operator_labels:
                parts.append(operator_labels[key] + _format_value(item))
            elif key in {"in", "not_in", "between"} and isinstance(item, (list, tuple)):
                parts.append(f"{key}({', '.join(_format_value(part) for part in item)})")
            else:
                parts.append(f"{key}({_format_value(item)})")
        return " AND ".join(parts)
    return _format_value(value)


def _format_value(value: Any) -> str:
    if isinstance(value, _Absent):
        return "—"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return str(value)


def _display_name(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _md_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _metric(label: str, value: Any) -> str:
    return f'<div class="card"><span>{html.escape(str(label))}</span><strong>{html.escape(str(value))}</strong></div>'


class _Absent:
    pass


_ABSENT = _Absent()
