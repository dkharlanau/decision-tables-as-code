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

## Adoption layer

- [x] Excel/CSV importer with explicit column mapping
- [x] scenario file format and `dtac test`
- [x] Markdown/HTML rendering for business review
- [x] SARIF and GitHub annotations for validator findings
- [x] richer overlap/shadow analysis for numeric and enum conditions
- [x] rule provenance (`source`, ticket, owner, effective dates)
- [x] problem-first documentation landing page
- [x] runnable enterprise use-case gallery
- [x] architecture and staged adoption guides
- [x] generated CLI reference with stale-doc CI check
- [x] documentation link/example integrity tests

## Interoperability

- [x] strict DMN 1.4 import/export subset with round-trip fixtures
- [x] BRFplus-oriented adapter boundary and runnable SAP examples
- [ ] generated runtime adapters for Python/JavaScript
- [x] machine-readable semantic change report

## Scale and governance

- [x] multi-table packages with explicit dependencies and output bindings
- [x] decision dependency graph with JSON/DOT/Mermaid output
- [x] deterministic topological package execution
- [x] transitive impact analysis and package semantic/dependency diff
- [ ] policy packs for organization-specific checks
- [ ] approval metadata and signed release bundles
- [ ] deeper backward-compatibility proofs between table versions
- [x] agent-facing inspect/explain interface
- [x] classified semantic-diff gates for CI

## Product test

A feature belongs here if it makes a real enterprise rule set easier to migrate, review, verify, operate, or reuse without requiring access to the target platform.
