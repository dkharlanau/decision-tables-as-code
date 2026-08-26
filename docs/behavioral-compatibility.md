# Behavioral compatibility proofs

`dtac diff` answers a structural question: what rule, contract, governance, or table properties changed, and how risky does that change look statically?

`dtac compatibility` answers a different question: **for every fact combination in the declared finite input space, does the candidate behave exactly like the baseline?**

When the answer can be proven exhaustively, DTAC returns `provable: true` and either `equivalent: true` or concrete witness cases showing where behavior changed. When the finite proof cannot be made, DTAC returns `provable: false` with blocking reasons instead of guessing.

## Find concrete changed business cases

```bash
dtac compatibility \
  examples/order-routing.yaml \
  examples/order-routing-v2.yaml \
  --output compatibility.json
```

For the repository example the declared domains define eight fact combinations. Seven behave identically. One witness identifies the exact changed business case:

```json
{
  "facts": {
    "country": "DE",
    "customer_type": "B2B",
    "order_value": 5000
  },
  "change_kinds": ["outputs_changed"],
  "before": {
    "status": "ok",
    "matched_rule_ids": ["de-b2b-high"],
    "outputs": {
      "route": "enterprise-desk",
      "approval": "senior"
    }
  },
  "after": {
    "status": "ok",
    "matched_rule_ids": ["de-b2b-high"],
    "outputs": {
      "route": "enterprise-desk",
      "approval": "director"
    }
  }
}
```

That turns a generic statement such as “rule changed” into a reviewable business fact set.

## What is compared

For every exhaustively generated fact set DTAC compares:

- successful result vs deterministic evaluation error;
- whether any rule matched;
- the exact ordered `matched_rule_ids`;
- the exact output object/list/null result;
- deterministic error type and message when both versions error.

Changing only a rule ID therefore counts as behavioral change even if the outputs are identical. Stable rule identity is part of the public decision result contract and is used by scenarios, explain traces, audit evidence, and downstream automation.

## The fact space is the union of both domains

For each input, DTAC takes the ordered union of the baseline and candidate declared domain values.

That matters when a candidate removes a domain value. If the baseline declared `country: [DE, PL]` and the candidate declares only `[DE]`, `PL` is still evaluated. A candidate cannot appear compatible merely by deleting the business case from its own declared domain.

Boolean `true` and integer `1` remain distinct domain values despite Python's internal boolean/integer relationship.

## Proof preconditions

An exact compatibility proof requires:

- both tables to pass DTAC validation;
- the same input names;
- the same declared type for each input;
- a non-empty finite domain for every input in both versions;
- an explicit `--as-of` when either table contains effective-dated rules;
- the union fact space to remain within `--max-combinations`.

If any requirement is missing the report uses:

```json
{
  "provable": false,
  "equivalent": null,
  "changed": null,
  "blocking_reasons": [
    {
      "code": "missing_finite_domain",
      "message": "..."
    }
  ]
}
```

Common blocker codes are `invalid_before_table`, `invalid_after_table`, `input_contract_mismatch`, `input_type_mismatch`, `missing_finite_domain`, `as_of_required`, and `combination_limit`.

This distinction is deliberate: **“not proven different” is not the same as “proven equivalent.”**

## Effective-dated comparison

Compatibility never reads today's date. If effective-dated rules exist, pass the comparison date explicitly:

```bash
dtac compatibility \
  baseline.yaml candidate.yaml \
  --as-of 2027-01-01
```

Run separate proofs for meaningful effective dates when a release spans multiple rule windows. For example, compare before cutover, on cutover day, and after cutover.

## CI gate

Reporting mode exits `0` and writes the evidence regardless of whether behavior changed:

```bash
dtac compatibility before.yaml after.yaml --output compatibility.json
```

Use `--fail-on-change` as a gate:

```bash
dtac compatibility before.yaml after.yaml \
  --fail-on-change \
  --output compatibility.json
```

Exit codes:

- `0`: exhaustive proof completed and behavior is equivalent;
- `1`: exhaustive proof completed and at least one behavior change exists;
- `2`: proof could not be established, or another CLI/input error occurred.

A CI workflow should treat both `1` and `2` as requiring attention. Exit `2` must never be interpreted as compatibility.

## Witness limits

All combinations are still evaluated even when `--max-witnesses` is small. Only the number of detailed examples stored in the JSON report is capped.

```bash
dtac compatibility before.yaml after.yaml \
  --max-witnesses 20
```

`changed_combinations` and `category_counts` remain exact. `witnesses_truncated: true` means additional changed fact sets exist beyond the detailed witness array.

## Combination safety limit

The default maximum is 10,000 fact combinations:

```bash
dtac compatibility before.yaml after.yaml \
  --max-combinations 50000
```

The limit prevents an accidental Cartesian explosion. Exceeding it makes the proof explicitly unprovable rather than switching to sampling.

For large or continuous spaces, use scenario packs for high-value business examples and semantic diff for structural review; narrow or discretize domains only when those values genuinely represent the business proof space.

## Compatibility proof vs semantic diff

Use both in enterprise change review:

1. `dtac diff` explains structural and governance changes, including changes outside executable behavior such as owner/source/ticket metadata;
2. `dtac compatibility` proves observed executable behavior over the declared finite domain and gives witness facts;
3. scenario packs preserve named regression examples that matter even when they are not part of a finite exhaustive domain;
4. a release bundle can preserve the approved table, scenarios, semantic diff, review artifact, runtimes, and checksums.

A structural change can be behaviorally equivalent. Conversely, a small-looking rule edit can have many behavioral witnesses. The two reports answer complementary questions.
