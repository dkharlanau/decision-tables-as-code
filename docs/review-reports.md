# Business review reports

`dtac render` turns the canonical decision-table model into a deterministic review artifact for people who should not have to read YAML.

## Standalone HTML

```bash
dtac render examples/order-routing.yaml \
  --format html \
  --coverage \
  --output order-routing.html
```

The generated file contains its own CSS and needs no server, JavaScript, CDN, or external asset. It includes:

- table identity, hit policy, rule count, and semantic fingerprint
- metadata
- optional finite-domain coverage metrics
- a horizontally scrollable rule matrix with sticky headers
- stable per-rule anchors and an index for large tables
- validator diagnostics

## Markdown

```bash
dtac render examples/order-routing.yaml \
  --format markdown \
  --coverage \
  --output order-routing.md
```

Markdown is useful for pull-request descriptions, generated docs, Confluence-style copy/paste workflows, or repositories where HTML artifacts are not desired.

## Render semantic changes

Use `--against` to compare the rendered table with a previous version:

```bash
dtac render examples/order-routing-v2.yaml \
  --against examples/order-routing.yaml \
  --format html \
  --output order-routing-change.html
```

The report summarizes added, removed, and changed rules and adds a change-status column to the current rule matrix. Removed rules remain listed in the change summary even though they are absent from the current matrix.

## Semantic fingerprint

Every report includes a SHA-256 fingerprint of the canonical in-memory table model. Formatting differences in the source file do not change this fingerprint; semantic model changes do. This makes a generated review artifact traceable to the decision definition it represents.

Rendering is intentionally separate from validation exit behavior. A report can show validation findings without refusing to render. Use `dtac validate` as the CI merge gate.
