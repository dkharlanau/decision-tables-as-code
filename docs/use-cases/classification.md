# Classification and pricing-style decision matrices

Classification, eligibility, pricing, tax, surcharge, and segmentation rules frequently share the same structure: several business dimensions select a result or a manual-review path. The exact runtime differs, but the review problem is similar.

DTAC is useful when the logic can be represented as an explicit decision table and the team wants to test gaps, overlaps, exceptions, and semantic changes outside the runtime editor.

## Runnable example

`examples/sap/tax-classification.yaml` is a fictional classification example. It is not tax guidance.

```bash
dtac validate examples/sap/tax-classification.yaml

dtac test examples/sap/tax-classification.yaml \
  examples/sap/tax-classification.scenarios.yaml
```

Expected result: all 4 scenarios pass, including the missing-tax-number case that routes a business customer to explicit review.

## Useful rule shapes

The same pattern can model:

- product/customer classification;
- discount eligibility;
- price-list or surcharge selection;
- tax-data completeness treatment;
- segmentation;
- service-level selection;
- manual-review routing.

## Make exceptions explicit

A strong rule set does not hide missing data behind a default if the business process requires review. Model the review outcome explicitly and add a scenario for it. This makes a future change from “review” to “automatic” visible in semantic diff.

## Coverage

Finite categorical dimensions can be declared as domains and analyzed for gaps/ambiguity:

```bash
dtac coverage table.yaml
```

For genuinely open values such as continuous prices, use boundary scenarios rather than inventing a misleading finite domain.

For amount thresholds, see the [approval matrix](approval-matrix.md) example; the same boundary-testing technique applies to pricing-style ranges.
