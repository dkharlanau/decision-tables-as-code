# Generated runtime adapters

Decision Tables as Code can turn a reviewed canonical table into an autonomous runtime artifact. This closes the gap between Git governance and application execution: the same rules that were validated, tested, diffed, and approved are compiled into code instead of being reimplemented manually.

## Python runtime export

Generate a standalone Python module:

```bash
dtac-python-export examples/order-routing.yaml --output build/order_routing.py
```

The generated module has no DTAC or PyYAML runtime dependency and exposes `evaluate(facts, as_of=None)`.

```python
from build.order_routing import evaluate

result = evaluate({
    "country": "DE",
    "customer_type": "B2B",
    "order_value": 6000,
})
```

## JavaScript runtime export

Generate a dependency-free ES module:

```bash
dtac-js-export examples/order-routing.yaml --output build/order-routing.mjs
```

Use it directly from Node.js or another ES-module runtime:

```javascript
import { evaluate } from "./build/order-routing.mjs";

const result = evaluate({
  country: "DE",
  customer_type: "B2B",
  order_value: 6000,
});
```

For effective-dated tables, pass an explicit date:

```javascript
const result = evaluate({ country: "DE" }, { as_of: "2027-01-01" });
```

Both generated runtimes return `table_id`, `matched_rule_ids`, and `outputs`.

## Semantic contract

Generated runtimes preserve the native DTAC execution semantics for:

- `unique`, `first`, and `collect` hit policies
- scalar equality and list membership
- wildcard presence checks
- `eq`, `ne`, `in`, `not_in`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, and `regex`
- explicit rule priority ordering
- effective-date windows with an explicit `as_of` value

Generation fails before writing output when validation contains errors. Runtime generation is therefore intended to follow the same validation/scenario/semantic-diff gates used for normal DTAC review.

## Recommended release flow

```text
Excel/CSV/DMN/YAML
      |
      v
canonical decision table
      |
      +--> validate
      +--> test scenarios
      +--> semantic diff
      +--> business review
      |
      v
runtime export
      |
      +--> Python module
      +--> JavaScript ES module
      |
      v
application artifact
```

A useful CI pattern is to generate runtime artifacts from the exact reviewed commit or release tag and package them together with the semantic-diff report and scenario results.

## Boundary

Runtime export is code generation, not generic deployment. DTAC does not install generated modules into applications, configure application-specific integration, or claim semantic equivalence with proprietary rule platforms. Each adapter must have explicit parity tests against the native DTAC evaluator.

Stronger release-bundle provenance, multi-table compilation, and target-specific compatibility proofs remain roadmap work.
