# Generated runtime adapters

Decision Tables as Code can turn a reviewed canonical table into an autonomous runtime artifact. This closes the gap between Git governance and application execution: the same rules that were validated, tested, diffed, and approved are compiled into code instead of being reimplemented manually.

## Python runtime export

Install DTAC, then generate a standalone Python module:

```bash
dtac-python-export examples/order-routing.yaml --output build/order_routing.py
```

The generated module has no DTAC or PyYAML runtime dependency. It embeds the normalized decision table and exposes:

```python
from build.order_routing import evaluate

result = evaluate({
    "country": "DE",
    "customer_type": "B2B",
    "order_value": 6000,
})
```

The result contains `table_id`, `matched_rule_ids`, and `outputs`.

## Semantic contract

The generated Python runtime preserves the native DTAC execution semantics for:

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
      v
application artifact
```

A useful CI pattern is to generate the runtime artifact from the exact reviewed commit or release tag and package it together with the semantic-diff report and scenario results.

## Boundary

Runtime export is code generation, not generic deployment. DTAC does not install the generated module into an application, configure application-specific integration, or claim semantic equivalence with proprietary rule platforms. Each adapter must have explicit parity tests against the native DTAC evaluator.

Python is the first generated runtime target. JavaScript/TypeScript and stronger release-bundle provenance remain roadmap items.
