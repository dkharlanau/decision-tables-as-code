# Excel decision table validation in Git

A common enterprise rule set starts as an Excel workbook: columns are conditions/results, rows are rules, and review happens by comparing two files or visually scanning hundreds of cells. That is workable for editing but weak for proving correctness and change impact.

DTAC keeps Excel as an intake format while moving the reviewable rule model into Git.

## Runnable example

The repository contains a CSV representation plus an explicit import mapping:

- `examples/order-routing.csv`
- `examples/order-routing.import.yaml`

Import it:

```bash
dtac import examples/order-routing.csv \
  --config examples/order-routing.import.yaml \
  --output /tmp/order-routing.yaml
```

Validate the imported decision table:

```bash
dtac validate /tmp/order-routing.yaml
```

Expected result: validation exits successfully with no error findings.

Check the declared finite domain:

```bash
dtac coverage /tmp/order-routing.yaml
```

Expected result: the example has complete, unambiguous coverage for its declared domain.

## What this catches before deployment

Depending on the table, DTAC can surface:

- duplicate rule IDs;
- unknown input/output references;
- exact duplicate conditions;
- same-condition/different-output conflicts;
- proven overlaps under UNIQUE semantics;
- fully shadowed FIRST-policy rules;
- malformed conditions;
- finite-domain gaps and ambiguity.

## Why explicit import mapping matters

The importer does not guess which spreadsheet columns are inputs, outputs, IDs, priorities, or descriptions. The mapping file makes that interpretation versionable and reviewable. If a workbook layout changes, the import contract changes explicitly too.

For XLSX, install the optional Excel dependency and use the same mapping approach. See [spreadsheet importing](../importing-spreadsheets.md).

## Pull-request workflow

After the first canonical version is approved:

```bash
dtac diff baseline.yaml candidate.yaml --fail-on potentially-breaking
```

This turns a workbook change into a classified semantic change report rather than a binary-file comparison.
