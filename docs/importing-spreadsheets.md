# Importing Excel and CSV decision tables

The importer deliberately separates the business workbook from the mapping configuration. Column names and types are never guessed.

## 1. Keep the source table simple

```csv
Rule ID,Priority,Country,Order Value,Route
DE-HIGH,10,DE,>=5000,enterprise
DE-LOW,20,DE,<5000,standard
PL,30,PL,,shared-service
```

Blank condition cells are wildcards by default. Set `blank_condition: error` in the config if blanks should be rejected.

## 2. Map source columns explicitly

```yaml
table:
  id: order-routing
  hit_policy: unique
blank_condition: wildcard
columns:
  rule_id: Rule ID
  priority: Priority
  inputs:
    country:
      column: Country
      type: string
      domain: [DE, PL]
    order_value:
      column: Order Value
      type: integer
      domain: [500, 5000]
  outputs:
    route:
      column: Route
      type: string
```

## 3. Convert and validate

```bash
dtac import rules.csv --config rules.import.yaml --output rules.yaml
dtac validate rules.yaml
```

XLSX uses the same mapping format. Install the optional dependency with `pip install -e '.[excel]'` or `pip install 'decision-tables-as-code[excel]'` after packaging.

## Condition syntax in cells

- blank: wildcard when `blank_condition: wildcard`
- `DE`: equality
- `in(DE,AT,CH)`: membership
- `not_in(DE,AT)`: exclusion
- `>=5000`, `<5000`, `=DE`, `!=DE`: comparisons
- `between(100,500)`: inclusive range
- `regex(^C[0-9]+$)`: full-match regular expression for string inputs
- `exists(false)`: missing-field condition

Types come from the import mapping. This prevents common spreadsheet surprises such as country code `NO` being silently interpreted as a boolean or leading-zero identifiers becoming numbers.

## Deliberate limitation: formulas

The XLSX importer rejects formula cells rather than evaluating them differently from Excel. Convert formula results to values before import. This keeps the Git representation deterministic and auditable.
