# Decision Tables as Code — documentation

Decision Tables as Code is a Git-native workflow for enterprise business rules that are currently difficult to review because they live in Excel workbooks, migration files, configuration tables, or runtime-specific rule systems.

The core idea is simple: keep a small canonical decision-table model in Git, then make validation, business scenarios, coverage, semantic change review, provenance, interoperability, and target-system adaptation reproducible around it.

## Start from the problem you have

| Problem | Start here | Runnable example |
| --- | --- | --- |
| Validate an Excel decision table before deployment | [Excel decision table validation](use-cases/excel-decision-table-validation.md) | `examples/order-routing.csv` |
| Govern an approval or release matrix | [Approval matrices](use-cases/approval-matrix.md) | `examples/sap/approval-matrix.yaml` |
| Derive target master-data values during migration | [Master-data derivation](use-cases/master-data-derivation.md) | `examples/sap/customer-account-group-derivation.yaml` |
| Review interface routing, filtering, or loop-prevention rules | [Interface filters and routing](use-cases/interface-filtering.md) | `examples/sap/interface-replication-filter.yaml` |
| Control tax/classification enrichment rules | [Classification rules](use-cases/classification.md) | `examples/sap/tax-classification.yaml` |
| Put effective-dated cutover logic under regression test | [Effective-dated rules](use-cases/effective-dated-rules.md) | `examples/effective-routing.yaml` |
| Import/export an ordinary DMN decision table for Git review | [DMN 1.4 subset](dmn.md) | `examples/dmn/routing-unique.dmn` |
| Use Git around SAP BRFplus-oriented rule work | [SAP / BRFplus workflow](sap-brfplus.md) | `examples/sap/` |
| Let CI or an AI agent inspect rule logic without parsing prose | [Machine inspection](inspect.md) and [explanations](explain.md) | `dtac inspect`, `dtac explain` |

## Core workflow

```text
Excel / DMN / YAML / JSON / exported configuration
                     |
                     v
             canonical decision table
                     |
       +-------------+---------+----------+-----------+
       |                       |          |           |
       v                       v          v           v
   validate                 scenarios   coverage   semantic diff
       |                       |          |           |
       +-----------------------+----------+-----------+
                              |
                              v
                        business review
                              |
                              v
                    target-specific adapter
```

The repository does not require a hosted service. The CLI, scenarios, reports, DMN fixtures, and enterprise examples run locally and in ordinary GitHub Actions.

## Adoption paths

- Existing workbook: [import spreadsheets](importing-spreadsheets.md) → validate → scenarios → semantic diff → review report.
- Existing DMN 1.4 decision table: [DMN interoperability subset](dmn.md) → import → validate/test/diff → optional strict export.
- New rule set: [v1 specification](specification.md) → [scenario testing](scenario-testing.md) → CI.
- SAP/BRFplus-oriented project: [SAP interoperability boundary](sap-brfplus.md) → runnable SAP examples → customer-specific adapter.
- Agent/automation workflow: [inspect](inspect.md) → [explain](explain.md) → [classified semantic diff](semantic-diff.md).

See [architecture](architecture.md) for the product boundary and [adoption guide](adoption-guide.md) for a staged rollout from spreadsheet or existing rule source to governed rules-as-code.

## Reference

- [CLI reference](cli-reference.md)
- [DMN 1.4 interoperability subset](dmn.md)
- [Decision-table v1 specification](specification.md)
- [Diagnostics](diagnostics.md)
- [Rule analysis](rule-analysis.md)
- [Rule governance and effective dates](rule-governance.md)
- [Scenario testing](scenario-testing.md)
- [Business review reports](review-reports.md)
- [GitHub integration](github-integration.md)
- [CI integration](ci.md)

## Search vocabulary

This project intentionally documents the concrete terms teams use when they look for this problem: **decision tables as code**, **business rules in Git**, **Excel decision table validation**, **decision table testing**, **DMN Git workflow**, **DMN 1.4 decision table import export**, **SAP BRFplus testing**, **approval matrix testing**, **master-data derivation rules**, **interface filtering rules**, and **semantic diff for business rules**.
