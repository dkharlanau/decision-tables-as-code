# Decision Tables as Code

Git-native validation, evaluation, coverage analysis, semantic diff, spreadsheet import, executable scenarios, business-review reports, and GitHub-native diagnostics for enterprise decision tables.

Business rules often live in Excel, configuration workbooks, migration templates, or application-specific rule editors. They are easy to change and difficult to review: duplicates are hidden, conflicting rules survive for months, coverage gaps appear only in production, and a pull request cannot explain what business logic actually changed.

Decision Tables as Code provides a small vendor-neutral format and deterministic CLI so a decision table can be treated like source code while remaining reviewable by business and functional teams.

## What works now

- canonical YAML/JSON decision-table model
- `unique`, `first`, and `collect` hit policies
- equality, membership, ranges, wildcard, existence, and regex conditions
- structural and semantic validation with stable `DTxxx` diagnostic codes
- duplicate and exact-conflict detection
- proven overlap detection for UNIQUE tables
- FIRST-policy shadowed-rule detection
- finite-domain gap and ambiguity analysis
- deterministic evaluation
- rule-aware semantic diff
- CSV/XLSX import with explicit column mapping
- executable YAML/JSON scenario packs and `dtac test`
- deterministic Markdown and standalone HTML review reports
- optional coverage and semantic-change summaries in reports
- stable rule anchors and semantic fingerprints
- SARIF 2.1.0 output for code-scanning systems
- native GitHub Actions `::error` / `::warning` annotations
- JSON Schema
- CLI suitable for CI
- runnable tests and GitHub Actions

## 60-second example

```yaml
version: 1
id: order-routing
hit_policy: unique
inputs:
  - name: country
    type: string
    domain: [DE, PL]
  - name: value
    type: integer
    domain: [500, 5000]
outputs:
  - name: route
    type: string
rules:
  - id: de-high
    when:
      country: DE
      value: {gte: 5000}
    then:
      route: enterprise
```

Install locally:

```bash
python -m pip install -e .
```

Validate:

```bash
dtac validate examples/order-routing.yaml
```

Validation includes exact conflicts plus conservative rule-relationship analysis: `DT032` reports proven UNIQUE overlaps and `DT033` reports FIRST rules that are provably unreachable because an earlier rule fully shadows them. See [rule analysis](docs/rule-analysis.md) and the [diagnostic reference](docs/diagnostics.md).

Use GitHub-native workflow annotations:

```bash
dtac validate examples/order-routing.yaml --format github
```

Generate SARIF 2.1.0 for GitHub Code Scanning or another SARIF consumer:

```bash
dtac validate examples/order-routing.yaml \
  --format sarif \
  --output dtac.sarif
```

The validator's exit code is independent of the report format: error findings still return `1`. See [GitHub Actions and Code Scanning](docs/github-integration.md).

Evaluate a decision:

```bash
dtac eval examples/order-routing.yaml \
  --facts '{"country":"DE","customer_type":"B2B","order_value":6000}'
```

Find business-rule gaps and ambiguity across declared input domains:

```bash
dtac coverage examples/order-routing.yaml
```

Compare two versions semantically rather than line-by-line:

```bash
dtac diff examples/order-routing.yaml examples/order-routing-v2.yaml
```

Import an existing spreadsheet without guessing its schema:

```bash
dtac import examples/order-routing.csv \
  --config examples/order-routing.import.yaml \
  --output /tmp/order-routing.yaml
```

The same mapping works for XLSX after installing the optional `excel` dependency. See [spreadsheet importing](docs/importing-spreadsheets.md) for the mapping format and supported cell expressions.

Run executable business scenarios:

```bash
dtac test examples/order-routing.yaml examples/order-routing.scenarios.yaml
```

Scenario packs can assert exact outputs, matched rule IDs, no-match behavior, and expected deterministic engine errors. Use `--json` for machine-readable CI output. See [scenario testing](docs/scenario-testing.md).

Render a business-readable standalone report:

```bash
dtac render examples/order-routing.yaml \
  --format html \
  --coverage \
  --output order-routing.html
```

Render the current table against a previous version to highlight semantic changes:

```bash
dtac render examples/order-routing-v2.yaml \
  --against examples/order-routing.yaml \
  --format markdown \
  --output order-routing-change.md
```

Reports include the rule matrix, diagnostics, stable rule anchors, and a semantic fingerprint. HTML is standalone: no server, JavaScript, CDN, or external assets are required. See [business review reports](docs/review-reports.md).

## Why this is useful in enterprise projects

The same pattern appears in SAP and non-SAP work: pricing matrices, partner determination, routing rules, master-data derivations, tax classifications, interface filters, migration mappings, approval matrices, cutover rules, and exception handling. The runtime may be ABAP, BRFplus, DMN, a workflow engine, middleware, or custom code, but the review problem is the same.

This repository focuses on the portable layer before runtime deployment: import or define the logic, validate it, surface findings directly in CI, prove coverage where possible, execute business regressions, render it for review, compare changes, and then export or adapt it to the target platform.

## Format design

The v1 format is intentionally small. Scalars mean equality, lists mean membership, `"*"` means any present value, and operator objects support `eq`, `ne`, `in`, `not_in`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, and `regex`.

See [the v1 specification](docs/specification.md), [diagnostic reference](docs/diagnostics.md), [rule analysis](docs/rule-analysis.md), [spreadsheet importing](docs/importing-spreadsheets.md), [scenario testing](docs/scenario-testing.md), [business review reports](docs/review-reports.md), [GitHub integration](docs/github-integration.md), and [CI integration](docs/ci.md).

## Near-term roadmap

The next high-value layers are provenance and effective dates, DMN interoperability, machine-readable inspect/explain reports, and SAP/BRFplus-oriented examples.

See [ROADMAP.md](ROADMAP.md) for the working roadmap.

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code)
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph)
- [Interface as Code](https://github.com/dkharlanau/interface-as-code)
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code)
- [Process as Code](https://github.com/dkharlanau/process-as-code)
- [Enterprise Change Graph](https://github.com/dkharlanau/enterprise-change-graph)

## Status

Working MVP. The format and CLI are usable, but v1 is still pre-stable and may evolve before a first tagged release.
