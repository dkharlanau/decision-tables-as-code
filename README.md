# Decision Tables as Code

Git-native validation, evaluation, coverage analysis, semantic diff, and spreadsheet import for enterprise decision tables.

Business rules often live in Excel, configuration workbooks, migration templates, or application-specific rule editors. They are easy to change and difficult to review: duplicates are hidden, conflicting rules survive for months, coverage gaps appear only in production, and a pull request cannot explain what business logic actually changed.

Decision Tables as Code provides a small vendor-neutral format and deterministic CLI so a decision table can be treated like source code.

## What works now

- canonical YAML/JSON decision-table model
- `unique`, `first`, and `collect` hit policies
- equality, membership, ranges, wildcard, existence, and regex conditions
- structural and semantic validation
- duplicate and exact-conflict detection
- finite-domain gap and ambiguity analysis
- deterministic evaluation
- rule-aware semantic diff
- CSV/XLSX import with explicit column mapping
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

## Why this is useful in enterprise projects

The same pattern appears in SAP and non-SAP work: pricing matrices, partner determination, routing rules, master-data derivations, tax classifications, interface filters, migration mappings, approval matrices, cutover rules, and exception handling. The runtime may be ABAP, BRFplus, DMN, a workflow engine, middleware, or custom code, but the review problem is the same.

This repository focuses on the portable layer before runtime deployment: import or define the logic, validate it, prove coverage where possible, review changes, and then export or adapt it to the target platform.

## Format design

The v1 format is intentionally small. Scalars mean equality, lists mean membership, `"*"` means any present value, and operator objects support `eq`, `ne`, `in`, `not_in`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, and `regex`.

See [the v1 specification](docs/specification.md), [spreadsheet importing](docs/importing-spreadsheets.md), and [CI integration](docs/ci.md).

## Near-term roadmap

The next high-value layers are executable scenario files, stronger overlap/shadow analysis, generated Markdown/HTML views, DMN interoperability, and machine-readable change reports for agents and CI.

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
