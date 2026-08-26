# Effective-dated rules and cutover testing

A rule change that starts on a specific date is easy to describe and surprisingly easy to implement incorrectly: old and new rules can overlap, leave a gap, or depend on the current system clock during testing.

DTAC makes time an explicit evaluation input.

## Runnable example

`examples/effective-routing.yaml` contains one German routing rule valid through 2026 and a successor starting in 2027.

Run the executable cutover scenarios:

```bash
dtac test examples/effective-routing.yaml \
  examples/effective-routing.scenarios.yaml
```

Expected result: all 4 scenarios pass. The same DE facts select `de-legacy` on `2026-12-31` and `de-new` on `2027-01-01`.

Evaluate a single date directly:

```bash
dtac eval examples/effective-routing.yaml \
  --facts '{"country":"DE"}' \
  --as-of 2027-01-01
```

Expected selected rule: `de-new`.

## Determinism rule

If any rule has `effective_from` or `effective_to`, evaluation requires an explicit `as_of`. The engine never substitutes today's date. Therefore the same commit and facts remain reproducible in local development, CI, and later audits.

Unquoted YAML dates are accepted and normalized to ISO dates, so normal YAML syntax does not create a parser/runtime mismatch.

## Review evidence

`dtac render` exposes owner, source, ticket, rationale, and effective window in the Rule governance section:

```bash
dtac render examples/effective-routing.yaml --format html --output review.html
```

This is useful for cutover rules, future policy activation, temporary exceptions, phased rollout, and sunset logic.
