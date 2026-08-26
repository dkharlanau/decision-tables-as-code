# Migration and cutover rules as code

Migration projects accumulate rules across mapping workbooks, defect lists, cutover notes, and one-off scripts. The dangerous part is not only the transformation itself; it is losing the rationale and regression evidence when a rule changes late in the program.

DTAC fits the decision-table subset of migration logic: rules where explicit source facts select target values, scope, routing, or an exception outcome.

## Runnable pattern

Use the fictional master-data derivation example as a migration rule set:

```bash
dtac validate examples/sap/customer-account-group-derivation.yaml

dtac test examples/sap/customer-account-group-derivation.yaml \
  examples/sap/customer-account-group-derivation.scenarios.yaml
```

Expected result: all migration derivation scenarios pass.

For rules originating in Excel/CSV, the import path is explicit:

```bash
dtac import examples/order-routing.csv \
  --config examples/order-routing.import.yaml \
  --output /tmp/imported.yaml
```

## Useful migration decisions

- include/exclude a record from migration scope;
- derive target grouping or role;
- choose a target organization or route;
- classify a source record into a migration treatment;
- select manual-review vs automatic handling;
- apply a cutover rule before/after an effective date.

## Regression strategy

Turn production-like examples and migration defects into scenario IDs. Then a mapping change must preserve or intentionally update those cases:

```bash
dtac test rules.yaml rules.scenarios.yaml
```

For time-dependent cutover logic, put `as_of` in the scenario. See [effective-dated rules](effective-dated-rules.md).

## Change review

Before a rerun or cutover load:

```bash
dtac diff approved.yaml candidate.yaml --fail-on potentially-breaking
```

This answers a more useful question than “which workbook cells changed?”: which executable rules or contracts changed, and how risky can that change be?

DTAC does not replace field-level transformation engines or data reconciliation. It governs the decision-table layer and can compose with Mapping as Code and Reconciliation as Code for the broader migration workflow.
