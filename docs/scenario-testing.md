# Executable decision scenarios

Scenario files keep business examples beside the decision table and make them executable in local development and CI.

```yaml
version: 1
table: order-routing
scenarios:
  - id: de-b2b-high-value
    facts:
      country: DE
      customer_type: B2B
      order_value: 6000
    expect:
      matched_rules: [de-b2b-high]
      outputs:
        route: enterprise-desk
        approval: senior
```

Run the pack:

```bash
dtac test examples/order-routing.yaml examples/order-routing.scenarios.yaml
```

Use `--json` for a stable machine-readable report.

## Effective-dated scenarios

A scenario can provide an explicit `as_of` date. This is the same deterministic date used by `dtac eval --as-of`; the scenario runner never reads the system clock.

```yaml
version: 1
table: effective-routing
scenarios:
  - id: before-cutover
    as_of: 2026-12-31
    facts:
      country: DE
    expect:
      matched_rules: [de-legacy]
      outputs:
        route: legacy-eu

  - id: after-cutover
    as_of: 2027-01-01
    facts:
      country: DE
    expect:
      matched_rules: [de-new]
      outputs:
        route: eu-new
```

This makes cutover dates, future-effective rules, and expiry boundaries executable regression cases instead of review comments.

## Assertions

Each scenario has `facts` and `expect`. `expect` may assert:

- `outputs`: exact output object/list or `null` for no match
- `matched_rules`: exact ordered list of matched rule IDs
- `error`: substring of an expected deterministic evaluation error

Assertions can be combined. A scenario may assert only rule identity when the output is intentionally not part of that regression test.

## Why scenarios matter

Coverage proves that declared finite domains have no gaps or ambiguity. Scenarios prove specific business examples and regressions. They complement each other: coverage answers “is the space structurally complete?”, while scenarios answer “does this known business case still behave as intended?”. Effective-dated scenarios add a third dimension: “does the same fact set behave correctly before and after a planned rule transition?”.
