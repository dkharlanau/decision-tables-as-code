# Decision explanation traces

`dtac explain` shows why each candidate rule matched or was rejected for a concrete fact set.

```bash
dtac explain examples/order-routing.yaml \
  --facts '{"country":"DE","customer_type":"B2B","order_value":6000}'
```

The JSON output is designed for debugging, CI evidence, support tooling, and AI agents. It contains:

- the supplied facts and explicit `as_of` date;
- every rule in evaluation order;
- whether the rule was effective for the requested date;
- every condition, the observed fact value, presence flag, and match result;
- whether all conditions matched;
- whether the rule was selected by the table hit policy;
- the final decision result or evaluation error.

For effective-dated tables, provide `--as-of YYYY-MM-DD`. The explanation path does not use the system clock.

Write the trace to a file with:

```bash
dtac explain table.yaml --facts @facts.json --as-of 2027-01-01 --output explain.json
```

The top-level `format_version` identifies the machine-readable explanation contract. Consumers should use it before depending on fields.
