# Interface filtering and routing rules as code

Cross-system interfaces often contain business rules hidden in middleware filters, ABAP exits, replication configuration, or operational spreadsheets: send this object to S/4, skip that status, use middleware for another target, and never send an object back to the system it originated from.

DTAC can make the deterministic filtering/routing layer visible before it is implemented in the integration runtime.

## Runnable example

`examples/sap/interface-replication-filter.yaml` is a fictional MDG/ERP/S4/AFS routing example with an explicit loop-prevention rule.

```bash
dtac validate examples/sap/interface-replication-filter.yaml

dtac test examples/sap/interface-replication-filter.yaml \
  examples/sap/interface-replication-filter.scenarios.yaml
```

Expected result: all 4 scenarios pass, including inactive-record suppression and the MDG-origin loop guard.

## Why this matters

Interface filters are risky because a successful technical message does not prove the business selection rule was correct. An explicit decision table lets a team review:

- origin-system logic;
- target-system routing;
- active/inactive suppression;
- exception paths;
- loop-prevention rules;
- changes to selection criteria.

## Incident-to-regression loop

When an interface incident reveals a missing filter or wrong route, add the concrete case to the scenario pack before changing the rule. That turns an operational incident into a permanent regression test.

Use `dtac explain` for a concrete fact set when the question is “why was this message sent or skipped?”

```bash
dtac explain examples/sap/interface-replication-filter.yaml \
  --facts '{"origin_system":"MDG","target_system":"MDG","change_type":"ADDRESS","active":true}'
```

The runtime may still be CPI, PI/PO, ABAP, BRFplus, or custom code. DTAC governs the portable decision logic, not the transport technology.
