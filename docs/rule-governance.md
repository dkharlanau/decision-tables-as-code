# Rule provenance and effective dates

Decision logic is easier to review when a rule explains what it does, where it came from, who owns it, and when it may apply.

Decision Tables as Code supports optional governance fields directly on each rule:

```yaml
- id: de-routing-2027
  owner: Order Management
  source: EU routing workbook / sheet 4
  ticket: CHG-1042
  rationale: New fulfillment model starts in 2027
  effective_from: 2027-01-01
  metadata:
    control: SOX-12
    system: S4
  when:
    country: DE
  then:
    route: eu-new
```

Supported fields are `owner`, `source`, `ticket`, `rationale`, `effective_from`, `effective_to`, and free-form `metadata`. Effective dates are inclusive and use `YYYY-MM-DD`.

## Deterministic time handling

The core engine never reads the system clock. If a table contains an effective-dated rule, evaluation must provide an explicit date:

```bash
dtac eval examples/effective-routing.yaml \
  --facts '{"country":"DE"}' \
  --as-of 2027-01-01
```

Missing effective-date bounds are open-ended. This allows CI, regression testing, and historical replay to produce the same result whenever the same table, facts, and evaluation date are supplied.

## Validation

`dtac validate` reports `DT024` for invalid ISO dates and `DT025` when `effective_from` is later than `effective_to`. Conflict and overlap checks ignore rules whose effective windows cannot overlap.

## Semantic diff

Governance fields participate in semantic diff. Changes to ownership, source, ticket, rationale, effective dates, or rule metadata are reported even when conditions and outputs stay unchanged.

Typical source references include SAP BRFplus objects, customizing tables, transport/change numbers, Confluence specifications, Jira tickets, Excel workbooks, interface mapping documents, policy IDs, and migration work packages.
