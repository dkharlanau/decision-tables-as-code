# SAP / BRFplus interoperability

Decision Tables as Code is not a replacement for SAP BRFplus and does not claim to implement SAP's runtime, repository, transport, authorization, or API model. It provides a portable, Git-native layer for rule definition, review, testing, provenance, and change analysis before target-specific deployment.

## Conceptual mapping

The useful conceptual correspondence is:

| DTAC concept | BRFplus-oriented target concept | Adapter responsibility |
| --- | --- | --- |
| Decision table | Decision-table expression used by a BRFplus solution | Resolve/create the target application/function/expression structure required by the customer implementation |
| Input definition | Input/context value used by the target rule | Map DTAC types and names to target data objects or function context |
| Output definition | Result/context value | Map result types and names to target objects |
| Rule | Decision-table row | Translate conditions and result values into target row syntax |
| Condition operators | Target condition/cell expression | Implement only operators that have equivalent target semantics; fail explicitly otherwise |
| Hit policy | Target table result-selection behavior | Verify target semantics instead of assuming a one-to-one mapping |
| Rule ID | Stable Git identity | Preserve as description/metadata/sidecar when the target does not provide an equivalent stable row identifier |
| Owner/source/ticket/rationale | Governance metadata | Store in target metadata where possible or keep in the Git-side manifest/review artifact |
| Effective dates | Time-bounded rule applicability | Either map to native target capabilities or compile them into explicit context conditions; never silently drop them |

This is a design mapping, not a promise that every DTAC table can be deployed unchanged to every BRFplus implementation.

## Recommended adapter boundary

A target adapter should have two explicit sides.

### Import side

Convert an external source into canonical DTAC without losing meaning:

```text
SAP/BRFplus or spreadsheet export
        |
        v
customer-specific extractor
        |
        v
canonical DTAC table
        |
        +--> validate
        +--> scenarios
        +--> coverage
        +--> semantic diff
        +--> business review
```

The extractor is responsible for identifying unsupported target constructs. It should fail rather than approximate FEEL-like expressions, formulas, custom functions, nested BRFplus expressions, dynamic data-object lookups, or other semantics that DTAC does not model.

### Export side

Take an approved canonical table and build a target-specific deployment artifact:

```text
approved DTAC table
        |
        v
target adapter
        |
        +--> type mapping
        +--> condition translation
        +--> result translation
        +--> object/package/application resolution
        +--> authorization / credentials
        +--> transport or deployment mechanism
        v
SAP target
```

Repository code should keep credentials, SAP object IDs, package names, transport requests, and environment-specific endpoints outside the portable table itself.

## Representability gate

Before an adapter writes anything to SAP it should answer four questions deterministically:

1. Are all DTAC input/output types representable in the target model?
2. Does every condition operator have equivalent target semantics?
3. Can the table's hit-policy semantics be preserved?
4. Can provenance/effective dates be preserved or explicitly compiled without changing behavior?

If any answer is unknown, the adapter should return an actionable unsupported-semantics error rather than deploy an approximation.

## Transport strategy

The recommended lifecycle is not "Git replaces SAP transport management." Git governs the portable business-rule source and evidence; the target adapter then participates in the customer's normal SAP delivery controls.

A typical enterprise flow is:

1. Pull request changes the canonical table.
2. DTAC validation, scenarios, coverage, and semantic diff run in CI.
3. Functional/business reviewers approve the rendered rule matrix.
4. A controlled adapter or manual implementation creates/updates target BRFplus objects.
5. SAP-native transport/change-management processes move the target artifact across systems.
6. A post-deployment extract or regression run can reconcile the target rule set back to the approved Git version.

That last reconciliation step is intentionally outside the first adapter example but is a strong future integration point with the related Reconciliation as Code project.

## What this repository deliberately does not claim

- full BRFplus import/export compatibility
- a generic remote SAP deployment API
- automatic creation of packages, applications, functions, or transports
- equivalence for custom BRFplus expressions or application exits
- legal/tax correctness of the sample rules
- runtime equivalence unless a target adapter explicitly proves support for the constructs used by a table

## Runnable examples

See the [SAP example gallery](../examples/sap/README.md) for customer derivation, tax classification, replication filtering/loop prevention, and approval-matrix scenarios.
