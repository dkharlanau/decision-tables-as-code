# Approval matrix as code

Approval and release matrices often fail at their boundaries: `999` vs `1000`, one risk class added without updating the neighboring rule, or overlapping ranges that appear only when a real document is processed.

DTAC makes those thresholds executable and reviewable in Git.

## Runnable example

The fictional SAP-oriented example uses amount and risk level to derive an approval strategy:

`examples/sap/approval-matrix.yaml`

Validate it:

```bash
dtac validate examples/sap/approval-matrix.yaml
```

Run boundary-value scenarios:

```bash
dtac test examples/sap/approval-matrix.yaml \
  examples/sap/approval-matrix.scenarios.yaml
```

Expected result: all 5 scenarios pass, including amounts exactly at `1000`, `10000`, and the high-risk `5000` threshold.

## Why this is better than reviewing threshold cells

A useful approval-rule pull request can show:

- the changed threshold in the canonical table;
- explicit scenarios immediately below, at, and above the threshold;
- validator findings for overlaps;
- a semantic diff showing which rule behavior changed;
- an HTML/Markdown matrix for business approval;
- owner/source/ticket/rationale metadata.

## Typical enterprise applications

The same pattern applies to:

- purchase/requisition approval levels;
- credit or exception approval;
- workflow escalation;
- release strategies;
- discount or manual-review thresholds;
- risk-based routing.

The example values are fictional; the point is the testing and governance pattern, not a delivered SAP approval configuration.
