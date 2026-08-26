# Enterprise use-case gallery

These pages start from business-rule problems rather than DTAC features. Every page points to an example that is already executed in repository CI.

| Use case | Typical source | What DTAC adds | Example |
| --- | --- | --- | --- |
| [Excel decision table validation](excel-decision-table-validation.md) | XLSX/CSV workbook | explicit import, validation, scenarios, semantic diff | `examples/order-routing.csv` |
| [Approval matrix](approval-matrix.md) | workflow/release spreadsheet | boundary tests, overlap detection, reviewable threshold changes | `examples/sap/approval-matrix.yaml` |
| [Master-data derivation](master-data-derivation.md) | MDG/migration rules | provenance, deterministic derivation tests | `examples/sap/customer-account-group-derivation.yaml` |
| [Migration rules](migration-rules.md) | cutover/mapping workbook | executable mappings and regression evidence | `examples/sap/customer-account-group-derivation.yaml` |
| [Interface filtering and routing](interface-filtering.md) | integration filter/config | loop-prevention tests and semantic change review | `examples/sap/interface-replication-filter.yaml` |
| [Classification and pricing-style matrices](classification.md) | tax/classification/pricing matrix | missing-data cases, boundaries, coverage | `examples/sap/tax-classification.yaml` |
| [Effective-dated rules](effective-dated-rules.md) | cutover/change schedule | explicit before/after regression cases | `examples/effective-routing.yaml` |
| [Order routing](routing.md) | routing/fulfillment matrix | multi-input rule validation and coverage | `examples/order-routing.yaml` |

All SAP-oriented examples contain fictional values and demonstrate governance patterns rather than delivered SAP configuration, tax guidance, or legal rules.
