# Architecture

Decision Tables as Code separates portable business-rule governance from the system that ultimately executes the rule.

## Product boundary

DTAC owns the Git-side representation and evidence around a decision table:

- canonical table contract
- deterministic validation and evaluation
- executable business scenarios
- finite-domain coverage analysis
- semantic diff and compatibility classification
- provenance and effective dates
- machine-readable inspect/explain output
- business-readable Markdown/HTML review artifacts

DTAC does not pretend that every runtime has the same semantics. Deployment, runtime-specific expressions, credentials, transport mechanisms, and proprietary object models belong behind target-specific adapters.

## Components

```text
                       +-------------------+
source files ---------->       loader       |
CSV / XLSX / YAML / JSON+----------+--------+
                                  |
                                  v
                         +--------+---------+
                         | canonical model  |
                         +--------+---------+
                                  |
          +-----------------------+-----------------------+
          |            |           |          |           |
          v            v           v          v           v
      validator     evaluator   coverage    diff      inspect/explain
          |            |           |          |           |
          +------------+-----------+----------+-----------+
                                  |
                      +-----------+-----------+
                      |                       |
                      v                       v
                scenario runner        review renderer
                      |                       |
                      +-----------+-----------+
                                  |
                                  v
                         approved Git state
                                  |
                                  v
                         target-specific adapter
```

## Canonical model as the seam

The canonical model is deliberately smaller than DMN, BRFplus, or a custom rules engine. A smaller seam provides three advantages:

1. Review and testing can happen without access to the target runtime.
2. Changes can be compared deterministically in a pull request.
3. Adapters must state what they can and cannot preserve instead of silently approximating unsupported semantics.

The cost is intentional: constructs outside the supported model must be rejected or handled in a target-specific extension rather than hidden behind a false compatibility claim.

## Determinism

The same committed table should produce the same result from the same explicit inputs. Therefore:

- rule ordering is deterministic;
- effective-dated rules use an explicit `as_of` value;
- the engine never reads the current date implicitly;
- reports have a semantic fingerprint;
- machine-readable outputs have format versions;
- semantic diff classifications are conservative when compatibility cannot be proven.

## CI boundary

A typical pull request can use four gates at different levels:

```text
syntax / structure  -> dtac validate
known regressions   -> dtac test
finite completeness -> dtac coverage
change risk         -> dtac diff --fail-on ...
```

`dtac render` creates the human review artifact; `dtac inspect` and `dtac explain` expose the same rule set to automation and agents.

## Enterprise deployment boundary

An adapter should be explicit about representability before deployment:

- input/output type mapping;
- condition-operator mapping;
- hit-policy semantics;
- provenance/effective-date preservation;
- target object IDs and environment configuration;
- credentials and authorization;
- transport/deployment controls.

See [SAP / BRFplus interoperability](sap-brfplus.md) for a concrete example of this boundary.

## Related repositories

The architecture is designed to compose with adjacent Git-native enterprise patterns:

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code) — governed mappings and value transformations.
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph) — relationships between transformations.
- [Interface as Code](https://github.com/dkharlanau/interface-as-code) — interface contracts and routing/configuration evidence.
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code) — prove source/target consistency after change or migration.
- [Process as Code](https://github.com/dkharlanau/process-as-code) — executable process knowledge.
- [Enterprise Change Graph](https://github.com/dkharlanau/enterprise-change-graph) — connect enterprise change objects and impact.
