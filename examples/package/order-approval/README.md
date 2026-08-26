# Order approval decision package

This example demonstrates a three-stage decision graph:

```text
risk-classification -> approval-decision -> fulfillment-route
```

The values are fictional. The purpose is to show explicit decision-to-decision bindings and transitive impact analysis.

## Validate

```bash
dtac package-validate examples/package/order-approval/package.yaml
```

Expected result: no package validation findings.

## Evaluate

```bash
dtac package-eval examples/package/order-approval/package.yaml \
  --facts '{"customer_tier":"VIP","blocked":false,"amount":500,"region":"EU"}'
```

Expected dataflow:

1. `risk-classification` returns `risk_level: LOW`.
2. The package binds that output into `approval-decision.risk_level`.
3. `approval-decision` returns `strategy: L1`.
4. The package binds that output into `fulfillment-route.approval_strategy`.
5. `fulfillment-route` returns terminal output `queue: EU_AUTO`.

## Show the graph

```bash
dtac package-graph examples/package/order-approval/package.yaml --format mermaid
```

## Impact

```bash
dtac package-impact examples/package/order-approval/package.yaml \
  --changed risk-classification
```

Expected downstream impacted decisions:

- `approval-decision`
- `fulfillment-route`

Changing only `approval-decision` impacts `fulfillment-route` but not the upstream risk classification.

See [multi-table decision packages](../../../docs/decision-packages.md) for the manifest contract, validation rules, package diff, and execution semantics.
