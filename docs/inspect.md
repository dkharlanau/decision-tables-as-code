# Machine-readable inspection

`dtac inspect` emits a stable JSON summary of a decision table for CI jobs, catalog builders, documentation generators, and AI agents.

```bash
dtac inspect examples/order-routing.yaml
```

The payload contains:

- `format_version`: version of the inspect JSON contract.
- `table`: table identity, hit policy, description, and metadata.
- `contract`: typed input and output definitions.
- `rules`: rule count, IDs, priority/governance/effective-date counts, and used condition operators.
- `diagnostics`: validation findings plus counts by severity.

The command does not evaluate business facts and does not read the system clock. It is intended to let external tools understand the shape and health of a table without parsing repository prose or reimplementing the table model.

Write the result to a file with:

```bash
dtac inspect examples/order-routing.yaml --output inspect.json
```

Consumers should branch on `format_version` before depending on fields. Additive fields may appear within a format version, while breaking contract changes require a new version.
