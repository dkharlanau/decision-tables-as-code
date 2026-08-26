# Master-data derivation rules as code

Master-data projects repeatedly contain derivation logic such as: source account type + business role + flags → target grouping, role, classification, or governance path. The logic may begin in a migration workbook and later move into MDG, BRFplus, ABAP, middleware, or custom code.

DTAC keeps the derivation itself portable and testable before runtime implementation.

## Runnable example

`examples/sap/customer-account-group-derivation.yaml` is a fictional customer/BP harmonization example.

```bash
dtac validate examples/sap/customer-account-group-derivation.yaml

dtac test examples/sap/customer-account-group-derivation.yaml \
  examples/sap/customer-account-group-derivation.scenarios.yaml
```

Expected result: all 4 scenarios pass, including employee handling and different source-system/customer-role combinations.

## What belongs in the table

Good candidates are deterministic derivations whose inputs and outputs can be named explicitly:

```text
source facts -> business rule -> derived target values
```

Examples include account group, BP role, sales classification, target organization, migration scope, enrichment status, or exception route.

## What should stay outside

Do not force runtime-specific mechanics into the portable table. Database reads, API calls, custom exits, SAP object IDs, authorizations, and transport requests should remain in the adapter/runtime layer.

## Governance value

Rule-level `owner`, `source`, `ticket`, `rationale`, and effective dates preserve why a derivation exists. `dtac explain` can then show why a concrete master-data record matched a rule, which is useful during migration defect analysis and functional review.
