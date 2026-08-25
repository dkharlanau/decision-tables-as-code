# Decision Tables as Code

Version, validate, compare, visualize, and test enterprise decision tables stored in spreadsheets or structured files.

## Problem

Business rules are frequently maintained in Excel and become difficult to validate, compare, test, and migrate.

## Core idea

Store decision tables as structured, versionable files with deterministic validation, diff, and test generation.

## Example

```text
Country | Customer Type | Channel | Result
DE      | B2B           | WEB     | A
DE      | B2C           | WEB     | B
```

## Initial scope

- Excel import
- YAML/JSON model
- duplicate rule detection
- conflicting rule detection
- missing combination detection
- decision table diff
- test generation
- DMN export
- visualization

## Long-term direction

A Git-native format and validation layer for enterprise decision logic.

## Design principles

- versionable
- portable
- machine-readable
- deterministic-first
- visual where useful
- Git-friendly
- vendor-neutral where practical
- interoperable with enterprise tools

## Status

Planning.
