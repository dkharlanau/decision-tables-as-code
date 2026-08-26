# Routing and fulfillment decision tables

Routing rules combine several business dimensions to select a route, desk, workflow, system, or fulfillment treatment. They are a good fit for decision-table testing because small condition changes can create gaps or overlapping matches.

## Runnable example

`examples/order-routing.yaml` is the general vendor-neutral routing example used throughout the repository.

```bash
dtac validate examples/order-routing.yaml

dtac test examples/order-routing.yaml \
  examples/order-routing.scenarios.yaml

dtac coverage examples/order-routing.yaml
```

Expected result: validation succeeds, all 5 scenarios pass, and the declared finite domain has complete unambiguous coverage.

## Review a routing change

The repository also contains `examples/order-routing-v2.yaml` so semantic diff can be exercised directly:

```bash
dtac diff examples/order-routing.yaml examples/order-routing-v2.yaml \
  --fail-on never
```

Expected result: `changed: true` with a classified semantic change report.

Render the candidate against the current rule set:

```bash
dtac render examples/order-routing-v2.yaml \
  --against examples/order-routing.yaml \
  --format html \
  --output routing-change.html
```

## Typical applications

- order or fulfillment routing;
- case/work-queue assignment;
- channel selection;
- service-level selection;
- interface destination selection;
- exception routing;
- regional/organizational treatment.

For a system-to-system variant with loop prevention, see [interface filtering and routing](interface-filtering.md).
