# DMN 1.4 interoperability subset

Decision Tables as Code supports a deliberately small DMN 1.4 import/export subset. The purpose is Git interoperability for ordinary decision tables, not to become a full DMN or FEEL engine.

The adapter accepts the DMN 1.4 model namespace:

```text
https://www.omg.org/spec/DMN/20211108/MODEL/
```

DMN 1.4 is an OMG specification. The normative specification and machine-readable files are published at https://www.omg.org/spec/DMN/1.4.

## CLI

Import one DMN decision table into canonical YAML:

```bash
dtac dmn-import examples/dmn/routing-unique.dmn \
  --output /tmp/routing.yaml
```

If a document contains multiple decisions with decision tables, select one explicitly:

```bash
dtac dmn-import model.dmn --decision decision-id --output decision.yaml
```

Export a representable canonical table:

```bash
dtac dmn-export table.yaml --output table.dmn
```

Provide a model namespace when the generated DMN must use a project-specific namespace:

```bash
dtac dmn-export table.yaml \
  --model-namespace urn:example:decisions \
  --output table.dmn
```

## Supported decision-table subset

| DMN construct | Support | Canonical mapping |
| --- | --- | --- |
| DMN 1.4 `definitions` model namespace | yes | document boundary |
| One decision-table decision | yes | one `DecisionTable` |
| Multiple decision-table decisions | selectable | use `--decision` |
| `UNIQUE` hit policy | yes | `unique` |
| `FIRST` hit policy | yes | `first`; physical rule order is preserved |
| `COLLECT`, `ANY`, `PRIORITY`, output/rule-order hit policies | no | explicit unsupported error |
| Input `inputExpression/text` | simple literal fact name | input name |
| Named outputs | yes | output name |
| Rule IDs | yes | preserved |
| `string` | yes | `string` |
| `number` | yes | `number` |
| `boolean` | yes | `boolean` |
| `date` | yes | `date` with `date("YYYY-MM-DD")` literals |
| missing/`Any` type | yes | `any` |
| DTAC `integer` export | no | rejected rather than silently coerced to FEEL `number` |
| finite scalar `inputValues` | yes | canonical input `domain` |
| compound/multiple named outputs | yes | every rule must set every declared output |

## Supported FEEL unary tests

Input entries support only constructs that DTAC can preserve deterministically:

| FEEL input entry | Canonical representation |
| --- | --- |
| `-` | no condition for that input |
| `"DE"` | equality |
| `"DE", "PL"` | membership |
| `< 1000`, `<= 1000`, `> 1000`, `>= 1000` | numeric/date comparison operator |
| `[0..100]`, `(0..100]`, `[0..100)`, `(0..100)` | lower/upper bounds with matching inclusivity |
| `not("DE")` | `ne` |
| `not("DE", "PL")` | `not_in` |
| numbers, booleans, `null`, quoted strings | scalar literals |
| `date("2027-01-01")` | date literal |

Arbitrary FEEL functions, expressions, contexts, invocations, custom functions, list expressions beyond the unary-test subset, and target-specific extensions are rejected with an actionable error.

## Why `-` is not DTAC `*`

DTAC `"*"` means **any present value**. A DMN `-` unary test is unrestricted. Those semantics are not identical when missing/null values matter, so `dmn-export` rejects canonical `"*"` instead of silently translating it to `-`.

An omitted canonical condition is exported as DMN `-`.

## Round-trip guarantee

For tables inside the supported subset, the repository tests a semantic round trip:

```text
DMN 1.4 -> canonical DTAC -> DMN 1.4 -> canonical DTAC
```

The first and final canonical tables must have no semantic diff. The CI fixtures cover both UNIQUE and FIRST, including FIRST rule-order behavior.

## Intentionally rejected on standard export

Canonical DTAC contains governance features that standard DMN export in this narrow adapter does not preserve:

- table metadata;
- input/output descriptions;
- rule descriptions;
- rule owner/source/ticket/rationale;
- rule effective dates;
- rule metadata;
- explicit canonical rule priority.

If any of these are present, export fails rather than dropping evidence. A target-specific adapter may choose a safe way to preserve them using annotations, sidecar metadata, extensions, or runtime-specific objects.

## Not a full DMN engine

DTAC does not execute arbitrary FEEL or Decision Requirements Diagrams, BKMs, invocation expressions, relations, contexts, decision services, custom functions, or vendor extensions. It imports/exports the supported decision-table seam so teams can apply Git review, scenarios, validation, semantic diff, and business-rule governance around a portable subset.

That strict boundary is intentional: interoperability should fail visibly when meaning cannot be preserved.
