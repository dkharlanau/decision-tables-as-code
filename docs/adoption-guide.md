# Adoption guide

Do not start by rewriting every enterprise rule. Start with one table where review pain already exists: an Excel matrix, migration derivation, approval threshold, interface filter, classification rule, or cutover decision.

## Stage 1 — capture the current rule set

If the source is a spreadsheet, use an explicit import mapping rather than column-name guessing:

```bash
dtac import rules.xlsx --config rules.import.yaml --output rules.yaml
```

If the source is configuration or a proprietary rule system, extract or transcribe only the representable decision-table layer. Preserve the original source reference in `source`, `ticket`, `rationale`, and metadata.

Exit criterion: the canonical table can be reviewed against the current source and the team agrees it represents the same intended rule set.

## Stage 2 — validate before changing behavior

```bash
dtac validate rules.yaml
```

Use validation first to expose duplicate IDs, unknown fields, exact conflicts, proven UNIQUE overlaps, FIRST-policy shadowing, and malformed conditions/effective dates.

Do not automatically "fix" findings when the current production behavior is unclear. A conflict discovered during migration is evidence to resolve with the functional owner.

Exit criterion: errors are resolved or explicitly understood and documented.

## Stage 3 — turn examples into executable regressions

Create a scenario pack from:

- business examples from workshops;
- production incidents;
- known exceptions;
- threshold boundaries;
- cutover before/after cases;
- values that previously caused ambiguity.

```bash
dtac test rules.yaml rules.scenarios.yaml
```

For effective-dated logic, put `as_of` directly in the scenario so cutover behavior is reproducible.

Exit criterion: important business cases run without manual interpretation.

## Stage 4 — add coverage where domains are finite

Declare input domains when enumeration is meaningful, then run:

```bash
dtac coverage rules.yaml
```

Coverage is especially useful for small categorical matrices. Do not fake finite domains for genuinely open numeric/text spaces just to obtain a percentage.

Exit criterion: gaps and ambiguity are either eliminated or explicitly accepted.

## Stage 5 — move changes into pull requests

Compare the approved baseline with the candidate:

```bash
dtac diff baseline.yaml candidate.yaml --fail-on potentially-breaking
```

A practical pull request contains:

- the canonical table change;
- scenario changes when expected behavior changes;
- semantic diff output;
- validation/coverage evidence;
- rendered review artifact;
- ticket/source/rationale metadata.

Exit criterion: reviewers can see the business change without reconstructing it from spreadsheet cells or a line diff.

## Stage 6 — connect the target runtime

Only after the Git-side workflow is useful should the team automate deployment.

A target adapter should first implement a representability check. It must reject unsupported semantics rather than approximate them silently. Keep credentials, system-specific object IDs, transports, and environment configuration outside the portable table.

For SAP-oriented work, see [SAP / BRFplus interoperability](sap-brfplus.md).

## Stage 7 — reconcile after deployment

For high-control environments, re-extract the deployed rule or validate target behavior against the approved scenarios. This distinguishes "the pull request was approved" from "the intended decision logic actually reached the runtime."

## Minimal CI baseline

A first useful gate does not need a platform:

```yaml
- run: dtac validate rules.yaml
- run: dtac test rules.yaml rules.scenarios.yaml
- run: dtac diff baseline.yaml rules.yaml --fail-on potentially-breaking
```

Add coverage and review artifacts when they add evidence rather than ceremony.

## What to measure

Adoption is useful when it reduces rule-change uncertainty. Practical measures include:

- time to explain what changed in a rule set;
- number of rule conflicts found before deployment;
- percentage of production defects represented as regression scenarios;
- number of changes with traceable owner/source/ticket/rationale;
- time required for a functional reviewer to approve a change;
- rule-set drift found between approved source and target runtime.
