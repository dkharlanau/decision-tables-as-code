# SAP-oriented decision-table examples

These examples are intentionally runnable without an SAP system. They model enterprise rule patterns that commonly appear around SAP implementations while keeping the decision logic portable and testable in Git.

All business values, object names, groupings, thresholds, and policies in this directory are fictional. They demonstrate the pattern, not SAP-delivered configuration or legal/tax guidance.

## 1. Customer account-group derivation

`customer-account-group-derivation.yaml` models migration/master-data derivation from source system, business role, and employee status to a target account grouping and BP role.

```bash
dtac validate examples/sap/customer-account-group-derivation.yaml
dtac test examples/sap/customer-account-group-derivation.yaml \
  examples/sap/customer-account-group-derivation.scenarios.yaml
```

Useful for: migration mapping, MDG derivations, BP/customer harmonization, and rule-workbook replacement.

## 2. Tax classification

`tax-classification.yaml` demonstrates a controlled classification matrix with an explicit review outcome for missing source data.

```bash
dtac validate examples/sap/tax-classification.yaml
dtac test examples/sap/tax-classification.yaml \
  examples/sap/tax-classification.scenarios.yaml
```

Useful for: master-data enrichment, cutover validation, classification completeness, and exception routing. The example values are fictional and are not tax advice.

## 3. Interface replication filter

`interface-replication-filter.yaml` demonstrates cross-system routing plus a loop-prevention rule.

```bash
dtac validate examples/sap/interface-replication-filter.yaml
dtac test examples/sap/interface-replication-filter.yaml \
  examples/sap/interface-replication-filter.scenarios.yaml
```

Useful for: MDG/ERP/S/4 replication policies, outbound filtering, middleware routing, origin-system guards, and interface change reviews.

## 4. Approval matrix

`approval-matrix.yaml` models amount/risk approval thresholds and includes executable scenarios exactly on the threshold boundaries.

```bash
dtac validate examples/sap/approval-matrix.yaml
dtac test examples/sap/approval-matrix.yaml \
  examples/sap/approval-matrix.scenarios.yaml
```

Useful for: workflow decisions, release strategies, exception approvals, and business review of threshold changes.

## Review workflow

A practical project flow is:

1. Export or transcribe the existing spreadsheet/configuration into the canonical DTAC model.
2. Run `dtac validate` to detect structural problems and proven rule conflicts.
3. Add executable scenarios from known business cases and production defects.
4. Run `dtac coverage` when finite input domains are declared.
5. Use `dtac diff` in pull requests to classify semantic changes.
6. Use `dtac render` to create a business-readable review artifact.
7. Only after approval, hand the canonical table to a target-specific adapter or implementation process.

See [SAP / BRFplus interoperability](../../docs/sap-brfplus.md) for the adapter boundary and limitations.
