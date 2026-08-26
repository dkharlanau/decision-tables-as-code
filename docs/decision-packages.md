# Multi-table decision packages

A decision package turns several canonical tables into one explicit decision system. The package manifest declares which table depends on which upstream decision and exactly which upstream outputs feed downstream inputs.

The package layer does not introduce a hidden global rules engine. Each table still evaluates with the normal DTAC semantics; the package adds validated dataflow and dependency order around those tables.

## Manifest

```yaml
version: 1
id: order-approval-flow
metadata:
  owner: Order Operations
tables:
  - id: risk-classification
    version: 1
    path: risk-classification.yaml

  - id: approval-decision
    version: 1
    path: approval-decision.yaml
    depends_on:
      - table: risk-classification
        bind:
          risk_level: risk_level
```

Table paths are relative to the manifest file. Each entry also records the canonical table format version. In package v1 this is `1`; keeping it explicit makes the manifest self-describing and lets schema/tooling reject a future incompatible table format rather than guessing.

`bind` is always:

```text
downstream_input: upstream_output
```

In the example, `approval-decision.risk_level` receives `risk-classification.risk_level`.

A dependency may omit `bind` when it exists only to express ordering/impact rather than pass a value.

## Validate a package

```bash
dtac package-validate examples/package/order-approval/package.yaml
```

Validation checks both the package graph and every table. Package-specific checks include:

- duplicate package table IDs;
- manifest/table ID mismatch;
- missing or self dependencies;
- duplicate dependencies;
- dependency cycles;
- unknown upstream outputs;
- unknown downstream inputs;
- one downstream input bound from multiple dependencies;
- incompatible upstream-output/downstream-input types;
- binding from a `collect` table, which has no single output object to bind.

Underlying `DTxxx` table diagnostics are returned with package-qualified paths. Package diagnostics use `PKxxx` codes. The JSON Schema additionally requires each manifest entry to pin a supported table format version.

Use JSON when another tool consumes the result:

```bash
dtac package-validate package.yaml --format json
```

## Evaluate in dependency order

```bash
dtac package-eval examples/package/order-approval/package.yaml \
  --facts '{"customer_tier":"VIP","blocked":false,"amount":500,"region":"EU"}'
```

The example evaluates in this deterministic order:

```text
risk-classification -> approval-decision -> fulfillment-route
```

Expected terminal output:

```json
{
  "fulfillment-route": {
    "queue": "EU_AUTO"
  }
}
```

The result includes the facts actually passed to every table, matched rule IDs, table outputs, terminal outputs, and the topological order.

### External facts vs dependency bindings

A dependency binding is authoritative for that downstream input. If the caller also supplies an external fact with the same name, the upstream bound value wins. The package result reports such names in `overridden_fact_keys` so the override is visible rather than silent.

External facts not consumed by an unbound table input are reported in `unused_fact_keys`.

### Effective dates

`package-eval --as-of YYYY-MM-DD` passes the same explicit date to every table. The package layer does not read the system clock.

## Dependency graph

Machine-readable JSON:

```bash
dtac package-graph examples/package/order-approval/package.yaml --format json
```

Graphviz DOT:

```bash
dtac package-graph examples/package/order-approval/package.yaml --format dot
```

Mermaid:

```bash
dtac package-graph examples/package/order-approval/package.yaml --format mermaid
```

Edges point from the upstream decision to the downstream decision and include binding labels when values are passed.

## Impact analysis

Ask which downstream decisions can be affected when one table changes:

```bash
dtac package-impact examples/package/order-approval/package.yaml \
  --changed risk-classification
```

Expected downstream impact:

```text
approval-decision
fulfillment-route
```

`--changed` can be repeated for multiple changed tables. Impact is graph-based and transitive; it does not claim that every possible fact set will actually change behavior.

## Compare two package versions

```bash
dtac package-diff baseline/package.yaml candidate/package.yaml --fail-on never
```

The report includes:

- added/removed tables;
- tables whose own decision logic changed according to semantic diff;
- tables whose dependency/binding declaration changed;
- downstream impacted decisions in either the before or after graph;
- an `all_affected` set suitable for regression-test selection.

By default `package-diff` exits `1` on any package change. Use `--fail-on never` when the JSON report is evidence rather than a gate.

## Type compatibility

Bindings are accepted when types are equal, either side is `any`, or an upstream `integer` feeds a downstream `number`. A general `number` does not feed an `integer` input because the output may contain a non-integer value.

## What packages do not do

- They do not make arbitrary table outputs globally visible.
- They do not infer dependencies from matching field names.
- They do not bind lists of COLLECT results into one scalar/object input automatically.
- They do not provide loops or recursive decision execution; cycles are invalid.
- They do not replace target-runtime orchestration. A runtime adapter can consume the validated graph if deployment/execution outside DTAC is required.

See the [runnable order-approval package](../examples/package/order-approval/README.md).
