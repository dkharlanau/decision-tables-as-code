# GitHub Actions and Code Scanning

Decision Tables as Code can surface findings in GitHub in two complementary ways.

## Native workflow annotations

Use `--format github` inside a GitHub Actions step:

```yaml
- name: Validate decision table
  run: dtac validate rules/order-routing.yaml --format github
```

Errors are emitted as GitHub `::error` workflow commands and warnings as `::warning`. The annotation identifies the source file and includes the deterministic decision-table path such as `rules[4].when.country` in the message.

The command still uses normal validator exit codes: validation errors return non-zero and can fail the merge gate.

## SARIF / GitHub Code Scanning

Generate SARIF 2.1.0:

```bash
dtac validate rules/order-routing.yaml \
  --format sarif \
  --output dtac.sarif
```

A GitHub Actions workflow can upload it with the official CodeQL action:

```yaml
permissions:
  contents: read
  security-events: write

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - run: python -m pip install .
  - name: Generate decision-table SARIF
    run: |
      dtac validate rules/order-routing.yaml --format sarif --output dtac.sarif || true
  - name: Upload decision-table SARIF
    uses: github/codeql-action/upload-sarif@v3
    with:
      sarif_file: dtac.sarif
  - name: Enforce decision-table validation
    run: dtac validate rules/order-routing.yaml
```

The first validation is allowed to continue so the SARIF file is uploaded even when findings exist. The final validation step preserves the merge gate.

## Why SARIF and native annotations both exist

Native annotations are the lightest integration and require no code-scanning setup. SARIF is better when findings should remain queryable in GitHub's code-scanning UI, participate in security/quality reporting, or be consumed by another SARIF-aware platform.

Current SARIF contains the exact source file and logical decision-table path. It deliberately omits physical line and column coordinates until the loader has a reliable source map.
