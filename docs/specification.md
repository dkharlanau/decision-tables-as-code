# Decision Table Format v1

Decision Tables as Code uses a deliberately small YAML/JSON model. The goal is not to replace a full rules platform. The goal is to make enterprise rules reviewable, testable, diffable, and automatable in Git.

## Document structure

```yaml
version: 1
id: freight-routing
name: Freight routing
hit_policy: unique
inputs:
  - name: country
    type: string
    domain: [DE, PL]
outputs:
  - name: route
    type: string
rules:
  - id: de
    when:
      country: DE
    then:
      route: central
```

`version` is the format version. `id` is the stable machine identity of the table. `hit_policy` controls what happens when multiple rules match. `inputs` and `outputs` define the contract. `rules` contain conditions and results. Optional `metadata` may contain ownership, source-system, process, ticket, or other provenance.

## Hit policies

- `unique`: zero or one rule may match. More than one match is a runtime error and is surfaced by finite-domain coverage analysis where possible.
- `first`: the first matching rule is selected. Rules with an integer `priority` are evaluated before rules without one; lower numbers have higher priority.
- `collect`: every matching rule contributes one output object.

## Conditions

A scalar is equality. A list is membership. `"*"` is a wildcard for any present value.

Operator objects use AND semantics:

```yaml
amount: {gte: 1000, lt: 5000}
country: {in: [DE, AT, CH]}
customer_id: {regex: "C[0-9]+"}
blocked: {ne: true}
optional_field: {exists: false}
```

Supported operators: `eq`, `ne`, `in`, `not_in`, `gt`, `gte`, `lt`, `lte`, `between`, `exists`, and `regex`.

## Domains and coverage

An input may define a finite `domain`. If every input has a domain, `dtac coverage` evaluates the Cartesian product and reports uncovered combinations and ambiguity under the `unique` policy.

Domains are intentionally explicit. The tool does not infer business completeness from observed rules because that would turn a deterministic check into a guess.

## Stable rule identity

Every rule should have a stable `id`. Semantic diff uses the ID to distinguish a modified rule from a deleted-and-recreated rule. This makes pull requests substantially easier to review than raw spreadsheet diffs.
