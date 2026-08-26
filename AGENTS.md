# Agent instructions

Decision Tables as Code evaluates bounded business decisions. The table and supplied facts are authoritative. Never fabricate missing facts or widen the supported expression language.

## Working loop

1. Read `README.md`, the decision table, and `docs/agent-manifest.json`.
2. Validate and lint before evaluation.
3. Confirm the facts file contains the values required for the requested decision.
4. Run the table with the supplied facts.
5. Return the decision together with the explainability trace and matched rule.
6. Report missing/invalid facts explicitly rather than guessing them.

## Guardrails

- Preserve rule order and declared hit policy.
- Respect explicit null handling and defaults.
- Do not add unsupported expressions or hidden procedural logic.
- Keep evaluation deterministic.
- When editing a table, show which cases or outcomes may change.

## Useful commands

```bash
dtac validate <table.yaml>
dtac lint <table.yaml>
dtac run <table.yaml> --facts <facts.json>
dtac explain <table.yaml> --facts <facts.json>
```
