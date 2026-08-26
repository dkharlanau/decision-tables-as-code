# Rule overlap and shadow analysis

`dtac validate` includes deterministic relationship checks between rules.

## UNIQUE overlap — DT032

Under `hit_policy: unique`, two rules must never match the same facts. The validator reports `DT032` when it can prove that two non-identical rule conditions overlap.

Examples it can prove:

```yaml
# scalar vs membership
- when: {country: DE}
- when: {country: [DE, AT]}
```

```yaml
# numeric range overlap
- when: {amount: {gte: 100, lt: 200}}
- when: {amount: {between: [150, 300]}}
```

Exact duplicate conditions are handled separately by `DT030`/`DT031`.

## FIRST shadowing — DT033

Under `hit_policy: first`, rule order is semantically significant. A later rule is reported as `DT033` when its full match set is provably contained by a rule evaluated earlier.

```yaml
hit_policy: first
rules:
  - id: fallback
    priority: 10
    when: {country: "*"}
    then: {route: fallback}
  - id: germany
    priority: 20
    when: {country: DE}
    then: {route: germany}
```

`germany` can never be selected because `fallback` always wins first for every fact set that would match it.

## Conservative by design

The analyzer currently proves relationships for:

- scalar equality
- membership lists and `in`
- wildcards and absent dimensions
- `eq`
- numeric `gt`, `gte`, `lt`, `lte`, and `between`
- compatible combinations of the above
- simple `exists` presence constraints

It does not guess relationships involving regex, `ne`, or `not_in`. Those relationships are treated as unknown unless another input dimension already proves the rules disjoint. This avoids false-positive merge failures.

Finite-domain `dtac coverage` remains the stronger exhaustive check when every input domain can be enumerated. Relationship analysis is useful when domains are not fully declared or numeric ranges are too large to enumerate.
