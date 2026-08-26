# Classified semantic diff

`dtac diff` compares two decision-table versions by meaning rather than by YAML line changes. Its JSON output is versioned so CI systems and agents can consume it without scraping prose.

```bash
dtac diff before.yaml after.yaml --fail-on never --output diff.json
```

The top-level `format_version` is currently `1`. The report contains the raw added, removed, changed-rule, and table-property sets plus a `classifications` list. Each classification has a stable `path`, a classification, and a reason.

## Classifications

- `breaking` — a contract or selection change is provably incompatible, such as removing an output, changing a declared type, or changing the hit policy.
- `potentially_breaking` — executable behavior can change but compatibility depends on the facts and caller, such as adding/removing a rule, changing conditions or outputs, changing effective dates, or adding an output.
- `non_breaking` — a change is structurally additive where the core model can prove that existing callers do not need to change, such as declaring an additional input that is not itself an executable rule change.
- `governance_only` — descriptions, ownership, source, ticket, rationale, or metadata changed without executable rule semantics changing.
- `none` — the two canonical tables are semantically identical for fields tracked by the diff.

The top-level `classification` is the highest-impact classification in the report. Classification is intentionally conservative: `potentially_breaking` means DTAC cannot prove that existing decisions are preserved.

## CI gates

The default preserves the original CLI behavior and exits with code `1` on any semantic change:

```bash
dtac diff main.yaml candidate.yaml
```

For a practical pull-request gate, fail only when executable behavior may change:

```bash
dtac diff main.yaml candidate.yaml --fail-on potentially-breaking
```

For a contract-only hard gate:

```bash
dtac diff main.yaml candidate.yaml --fail-on breaking
```

To collect a report without using the exit code as a gate:

```bash
dtac diff main.yaml candidate.yaml --fail-on never --output semantic-diff.json
```

This classification is a static compatibility signal, not a proof that all runtime facts produce identical outputs. Use scenario packs and coverage analysis alongside it for higher assurance.
