# Decision Tables as Code

Git-native validation, testing, governance, semantic diff, and review for enterprise decision tables stored in spreadsheets or structured files.

Business rules often live in Excel, migration workbooks, configuration tables, middleware filters, or runtime-specific rule editors. They are easy to change and difficult to review: conflicts hide between rows, boundary cases are tested manually, provenance disappears, and a pull request cannot explain what business behavior actually changed.

Decision Tables as Code (`dtac`) provides a small vendor-neutral model and deterministic CLI so decision logic can be treated like source code without becoming unreadable to functional and business reviewers.

## Start from a real problem

| Problem | Guide | Runnable example |
| --- | --- | --- |
| Validate an Excel rule workbook | [Excel decision table validation](docs/use-cases/excel-decision-table-validation.md) | `examples/order-routing.csv` |
| Test approval/release thresholds | [Approval matrix](docs/use-cases/approval-matrix.md) | `examples/sap/approval-matrix.yaml` |
| Govern master-data derivations | [Master-data derivation](docs/use-cases/master-data-derivation.md) | `examples/sap/customer-account-group-derivation.yaml` |
| Make migration/cutover rules executable | [Migration rules](docs/use-cases/migration-rules.md) | `examples/effective-routing.yaml` |
| Review interface filters and loop prevention | [Interface filtering](docs/use-cases/interface-filtering.md) | `examples/sap/interface-replication-filter.yaml` |
| Test classification/pricing-style matrices | [Classification rules](docs/use-cases/classification.md) | `examples/sap/tax-classification.yaml` |
| Prove before/after effective-date behavior | [Effective-dated rules](docs/use-cases/effective-dated-rules.md) | `examples/effective-routing.yaml` |
| Review routing/fulfillment logic | [Routing](docs/use-cases/routing.md) | `examples/order-routing.yaml` |

See the [documentation home](docs/index.md), [architecture](docs/architecture.md), and [adoption guide](docs/adoption-guide.md).

## What works now

- canonical YAML/JSON decision-table model
- `unique`, `first`, and `collect` hit policies
- equality, membership, ranges, wildcard, existence, and regex conditions
- stable `DTxxx` structural/semantic diagnostics
- duplicate, exact-conflict, proven UNIQUE-overlap, and FIRST-shadow analysis
- finite-domain gap and ambiguity analysis
- deterministic evaluation with explicit effective dates and no hidden system clock
- rule provenance: owner, source, ticket, rationale, metadata, effective window
- executable scenario packs, including explicit `as_of` cutover cases
- classified semantic diff: `breaking`, `potentially_breaking`, `non_breaking`, `governance_only`
- machine-readable `dtac inspect` and rule-level `dtac explain`
- CSV/XLSX import with explicit column mapping
- deterministic Markdown/standalone HTML business-review reports
- SARIF 2.1.0 and GitHub Actions annotations
- JSON Schema and CI-ready CLI
- runnable SAP-oriented derivation, classification, replication-filter, and approval examples
- documented SAP/BRFplus adapter boundary without pretending generic SAP deployment compatibility

## 60-second workflow

Install locally:

```bash
python -m pip install -e .
```

Validate a table:

```bash
dtac validate examples/order-routing.yaml
```

Run business scenarios:

```bash
dtac test examples/order-routing.yaml examples/order-routing.scenarios.yaml
```

Check finite-domain coverage:

```bash
dtac coverage examples/order-routing.yaml
```

Explain one decision:

```bash
dtac explain examples/order-routing.yaml \
  --facts '{"country":"DE","customer_type":"B2B","order_value":6000}'
```

Compare a candidate semantically rather than line-by-line:

```bash
dtac diff examples/order-routing.yaml examples/order-routing-v2.yaml \
  --fail-on never \
  --output semantic-diff.json
```

Render a business-readable review artifact:

```bash
dtac render examples/order-routing-v2.yaml \
  --against examples/order-routing.yaml \
  --format html \
  --output order-routing-change.html
```

## Excel to Git

Import an existing spreadsheet with an explicit column contract:

```bash
dtac import examples/order-routing.csv \
  --config examples/order-routing.import.yaml \
  --output /tmp/order-routing.yaml
```

The same mapping works for XLSX after installing the optional `excel` dependency. See [spreadsheet importing](docs/importing-spreadsheets.md).

## Effective-dated rules

Effective dates are explicit inputs to evaluation. The engine never substitutes today's date:

```bash
dtac eval examples/effective-routing.yaml \
  --facts '{"country":"DE"}' \
  --as-of 2027-01-01
```

Scenario packs can carry `as_of` too, making cutover boundaries repeatable in CI. YAML-native date values are normalized to ISO dates.

## SAP / BRFplus-oriented workflow

The [SAP example gallery](examples/sap/README.md) contains four locally executable enterprise patterns:

- customer/account-group and BP-role derivation
- classification with explicit missing-data review
- cross-system replication routing and origin-system loop prevention
- amount/risk approval thresholds with boundary-value scenarios

The [SAP / BRFplus interoperability guide](docs/sap-brfplus.md) defines the conceptual mapping, representability gate, adapter boundary, transport strategy, and limitations. No SAP credentials or licensed system are required to run the examples.

## Product boundary

DTAC governs the portable layer before runtime deployment:

```text
source -> canonical decision table -> validate/test/coverage/diff -> review -> target adapter
```

The target runtime may be BRFplus, DMN, ABAP, workflow, middleware, or custom code. DTAC does not claim those systems have identical semantics. A target adapter must explicitly prove that the table's types, operators, hit policy, provenance, and effective-date behavior are representable.

See [architecture](docs/architecture.md) and the [staged adoption guide](docs/adoption-guide.md).

## Reference

- [CLI reference](docs/cli-reference.md) — generated from the actual parser and checked in CI
- [v1 specification](docs/specification.md)
- [diagnostics](docs/diagnostics.md)
- [rule analysis](docs/rule-analysis.md)
- [rule governance](docs/rule-governance.md)
- [scenario testing](docs/scenario-testing.md)
- [classified semantic diff](docs/semantic-diff.md)
- [business review reports](docs/review-reports.md)
- [GitHub integration](docs/github-integration.md)
- [CI integration](docs/ci.md)

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code)
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph)
- [Interface as Code](https://github.com/dkharlanau/interface-as-code)
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code)
- [Process as Code](https://github.com/dkharlanau/process-as-code)
- [Enterprise Change Graph](https://github.com/dkharlanau/enterprise-change-graph)

## Roadmap and status

Working MVP. The model and CLI are usable, but v1 is still pre-stable. DMN interoperability, multi-table decision graphs, generated runtime adapters, and stronger compatibility proofs remain roadmap work.

See [ROADMAP.md](ROADMAP.md).
