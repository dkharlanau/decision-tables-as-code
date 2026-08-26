# Roadmap

The product goal is a practical Git-native layer for enterprise decision logic: easy to adopt from spreadsheets, deterministic enough for CI, understandable to business reviewers, and interoperable with common rule runtimes.

## Shipped in the first MVP

- [x] canonical YAML/JSON model
- [x] stable rule IDs and typed input/output contracts
- [x] deterministic evaluator
- [x] `unique`, `first`, and `collect` hit policies
- [x] validation diagnostics with stable codes
- [x] duplicate and exact-conflict detection
- [x] finite-domain coverage and ambiguity analysis
- [x] semantic rule diff
- [x] JSON Schema
- [x] CLI and GitHub Actions
- [x] examples and automated tests

## Next — adoption layer

- [ ] Excel/CSV importer with explicit column mapping
- [ ] scenario file format and `dtac test`
- [ ] Markdown/HTML rendering for business review
- [ ] SARIF or GitHub annotations for validator findings
- [ ] richer overlap/shadow analysis for numeric and enum conditions
- [ ] rule provenance (`source`, ticket, owner, effective dates)

## Next — interoperability

- [ ] DMN 1.4 import/export subset
- [ ] BRFplus-oriented adapter examples
- [ ] generated runtime adapters for Python/JavaScript
- [ ] machine-readable semantic change report

## Next — scale and governance

- [ ] multi-table packages and dependencies
- [ ] decision dependency graph
- [ ] policy packs for organization-specific checks
- [ ] approval metadata and signed release bundles
- [ ] backward-compatibility checks between table versions
- [ ] agent-facing inspect/explain interface

## Product test

A feature belongs here if it makes a real enterprise rule set easier to migrate, review, verify, operate, or reuse without requiring access to the target platform.
