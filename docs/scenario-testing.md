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

## Assertions

Each scenario has `facts` and `expect`. `expect` may assert:

- `outputs`: exact output object/list or `null` for no match
- `matched_rules`: exact ordered list of matched rule IDs
- `error`: substring of an expected deterministic evaluation error

Assertions can be combined. A scenario may assert only rule identity when the output is intentionally not part of that regression test.

## Why scenarios matter

Coverage proves that declared finite domains have no gaps or ambiguity. Scenarios prove specific business examples and regressions. They complement each other: coverage answers “is the space structurally complete?”, while scenarios answer “does this known business case still behave as intended?”.
