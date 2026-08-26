# Organization policy packs

DTAC's built-in validator checks whether a decision table is structurally and semantically valid. Organization policy packs answer a different question: **does this valid table satisfy our governance and portability standards?**

A policy pack is a small versioned YAML/JSON file. It never changes evaluation semantics, rewrites rules, or injects defaults. It only produces `POLxxx` findings that can be used locally, in pull requests, or as CI gates.

## Apply a policy

```bash
dtac policy-check examples/policy/governed-routing.yaml \
  --policy policies/enterprise-governance.yaml
```

Apply several packs in a deterministic order:

```bash
dtac policy-check examples/policy/governed-routing.yaml \
  --policy policies/enterprise-governance.yaml \
  --policy policies/sap-change-control.yaml \
  --format json \
  --output policy-report.json
```

Base DTAC validation runs once. Then the policy packs are applied in the exact order supplied on the command line. Error-level validation or policy findings return exit code `1`; warning-only policy findings remain reportable without failing the command. Malformed policy files return exit code `2` through the normal CLI error path.

## Policy format

```yaml
version: 1
id: enterprise-governance
description: Baseline governance for business-critical enterprise decisions.
severity: error
rules:
  required_rule_fields: [owner, ticket, rationale]
  allowed_hit_policies: [unique, first]
  require_input_domains: true
  max_rules: 200
```

The machine-readable contract is defined in [`schema/policy-pack.schema.json`](../schema/policy-pack.schema.json).

Unknown root/rule properties, duplicate list values, unsupported operators/hit policies, and contradictory allowed/forbidden operator declarations fail policy loading explicitly. A pack is never partially applied.

## Supported policy rules

### Required rule provenance

```yaml
required_rule_fields: [owner, source, ticket, rationale]
```

Each listed field must be present on every rule. Missing values produce `POL004` on the exact `rules[i].field` path.

This is useful for change-controlled business logic where executable behavior must remain tied to a responsible owner and approved change/source.

### Allowed hit policies

```yaml
allowed_hit_policies: [unique, first]
```

A table using another native hit policy receives `POL001` at `hit_policy`.

For example, an organization may allow `collect` for classification workloads but prohibit it for approval/routing decisions where one deterministic result is required.

### Allowed and forbidden operators

```yaml
allowed_operators: [eq, in, gt, gte, lt, lte, between, present]
forbidden_operators: [regex]
```

Operator inventory is normalized from the canonical model:

- scalar conditions count as `eq`;
- list conditions count as `in`;
- `"*"` counts as `present`;
- object conditions use their explicit operator names.

An operator outside the allowed set produces `POL006`; an explicitly forbidden operator produces `POL007`. A policy cannot list the same operator as both allowed and forbidden.

This can codify runtime portability constraints—for example, avoiding regex in a target where cross-engine regex equivalence is not acceptable.

### Require finite input domains

```yaml
require_input_domains: true
```

Missing input domains produce `POL003` on `inputs[i].domain`.

Finite domains improve coverage analysis and make exhaustive `dtac compatibility` proofs possible. Not every real-world continuous input should be artificially discretized; enable this only where the declared domain genuinely represents the governed business space.

### Limit rule count

```yaml
max_rules: 200
```

Tables above the limit receive `POL002`. This is a governance threshold, not an engine limitation. It can be used to trigger modularization/review when a decision table becomes too large for practical business review.

### Require complete effective windows

```yaml
require_complete_effective_window: true
```

If a rule declares only `effective_from` or only `effective_to`, it receives `POL005` for the missing boundary. Rules with no effective dates remain valid.

This is useful when temporary/cutover rules must always have an explicit end as well as start boundary.

## Stable diagnostics

| Code | Meaning |
| --- | --- |
| `POL001` | hit policy not allowed |
| `POL002` | rule count exceeds policy maximum |
| `POL003` | required finite input domain is missing |
| `POL004` | required rule provenance field is missing |
| `POL005` | effective window has only one boundary |
| `POL006` | operator is outside the allowed set |
| `POL007` | operator is explicitly forbidden |

Every policy diagnostic contains `severity`, `policy_id`, `path`, and `message`. JSON output also preserves the base `DTxxx` validation findings separately from policy findings.

## Included example packs

The repository includes two starting points rather than claiming universal enterprise policy:

- [`policies/enterprise-governance.yaml`](../policies/enterprise-governance.yaml): owner/ticket/rationale, finite domains, UNIQUE/FIRST, rule-count limit;
- [`policies/sap-change-control.yaml`](../policies/sap-change-control.yaml): owner/source/ticket/rationale, finite domains, UNIQUE/FIRST, no regex, bounded effective windows, larger rule-count limit.

The runnable [`examples/policy/governed-routing.yaml`](../examples/policy/governed-routing.yaml) passes both packs. The values and thresholds are examples; organizations should copy/version packs in their own governance repository rather than treating these defaults as mandatory standards.

## CI pattern

```yaml
- name: Check enterprise decision governance
  run: |
    dtac policy-check decisions/order-routing.yaml \
      --policy governance/enterprise.yaml \
      --policy governance/runtime-portability.yaml \
      --format json \
      --output policy-report.json
```

Keep policy packs version-controlled and review their changes like executable governance. Tightening a policy can make existing tables fail without changing table runtime semantics, so policy changes should have their own rollout/change-management process.

## Relationship to other DTAC controls

- `dtac validate` proves the table is a valid canonical decision definition.
- `dtac policy-check` proves it satisfies organization-specific governance constraints.
- `dtac compatibility` proves executable equivalence/change over a declared finite fact space.
- `dtac diff` explains structural/governance changes.
- scenario packs preserve named regression cases.
- `dtac bundle` packages approved table/evidence/runtime artifacts for release.

Policy packs intentionally remain orthogonal to evaluator semantics: governance can become stricter without silently changing a business decision.
