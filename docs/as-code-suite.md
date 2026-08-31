# Decision Tables as Code in the as-code suite

Decision Tables as Code owns bounded business decisions: declared facts, ordered rules, outputs, scenarios, explainability, semantic change, and release evidence. It does not own the surrounding process, interface transport, field transformation, or source-to-target assurance.

## A practical process reference

Process as Code supports generic, sandboxed artifact references. A process can therefore point to a reviewed decision table without copying the rules into the process model:

```yaml
artifacts:
  - id: approval_strategy
    kind: decision-tables-as-code
    relation: decides-with
    uri: github://dkharlanau/decision-tables-as-code/examples/sap/approval-matrix.yaml?ref=<immutable-revision>#sap-approval-matrix
```

The fragment is the stable decision-table `id`. Use an immutable tag or commit for governed handoffs. `process-code resolve` can prove that the referenced object is reachable; it does not validate DTAC semantics or execute the decision. Validate and test the table with DTAC:

```bash
dtac validate examples/sap/approval-matrix.yaml
dtac test examples/sap/approval-matrix.yaml \
  examples/sap/approval-matrix.scenarios.yaml
```

This separation is intentional: the process owns where a decision occurs, while the table owns how supplied facts produce an outcome.

## Related projects

- [Process as Code](https://github.com/dkharlanau/process-as-code) can reference a table from a process step through its generic artifact model. It does not embed or execute DTAC rules.
- [Interface as Code](https://github.com/dkharlanau/interface-as-code) owns delivery, retry, monitoring, and reconciliation expectations around integrations. A routing table may support an interface, but there is no automatic interface binding today.
- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code) owns source-to-target field transformation intent. Use a decision table only when the logic is genuinely a bounded decision, not as a substitute mapping format.
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code) proves source/target outcomes from explicit controls. It does not consume DTAC tables or treat a decision result as reconciliation evidence by itself.

## Handoff rule

Carry stable IDs, immutable revisions, and release hashes across repository boundaries. Do not copy rules into process transitions, mapping expressions, or reconciliation tolerances merely to make a diagram look integrated. There is currently no runtime adapter that executes a DTAC table from another suite contract.
