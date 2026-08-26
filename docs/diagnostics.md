# Diagnostic reference

Decision Tables as Code uses stable diagnostic codes so CI policies, SARIF consumers, and future organization-specific policy packs do not have to parse human-readable messages.

## Structural diagnostics

### DT001 — Unsupported format version
The document uses a format version that this release cannot interpret safely.

### DT002 — Unsupported hit policy
The table requests a hit policy outside the supported `unique`, `first`, and `collect` set.

### DT003 — Missing input contract
The table has no declared inputs.

### DT004 — Missing output contract
The table has no declared outputs.

### DT005 — No rules defined
The table is structurally valid but contains no rules. Severity: warning.

### DT010 — Duplicate contract name
An input or output name is declared more than once.

### DT011 — Unsupported data type
An input or output uses a type outside the supported v1 type set.

## Rule diagnostics

### DT020 — Duplicate rule identifier
Stable rule IDs must be unique inside a table.

### DT021 — Unknown input reference
A rule condition references an input that is not declared in the input contract.

### DT022 — Unknown output reference
A rule writes an output that is not declared in the output contract.

### DT023 — Missing rule output
A rule does not assign one of the declared outputs. Severity: warning.

### DT030 — Duplicate rule
A rule repeats the same conditions and outputs as another rule. Under `unique`, this is an error because both rules would match; under other hit policies it is a warning.

### DT031 — Conflicting exact rules
Two rules have identical conditions but different outputs.

### DT032 — Proven UNIQUE overlap
Two non-identical rules under `unique` are provably able to match the same facts. The analyzer is conservative and reports this only when overlap can be established deterministically.

### DT033 — Shadowed FIRST rule
A later `first` rule is provably contained by an earlier rule and can therefore never be selected. Severity: warning.

### DT040 — Invalid condition
A condition has an unsupported operator or invalid operator shape.

## Source locations

Current diagnostics carry a deterministic logical path such as `rules[3].when.country`. SARIF output also identifies the source file. Physical line/column coordinates are intentionally omitted until the loader has a reliable source map; the tool does not invent approximate locations.
