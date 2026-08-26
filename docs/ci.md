# CI integration

A decision table can be treated like source code. The minimum merge gate is deterministic validation:

```bash
dtac validate path/to/table.yaml
```

For tables with finite input domains, add coverage:

```bash
dtac coverage path/to/table.yaml
```

The CLI returns a non-zero exit code for validation errors, semantic diffs that contain changes, and coverage reports with gaps or ambiguity. That makes the commands suitable for GitHub Actions, pre-merge checks, or local pre-commit hooks.

A practical enterprise pattern is:

1. Export or convert the maintained table into canonical YAML.
2. Validate structural and semantic invariants.
3. Run finite-domain coverage where the business domain is enumerated.
4. Review semantic diff in the pull request.
5. Execute generated or hand-authored decision scenarios.
6. Export to the target runtime only after the checks pass.

The repository CI currently validates the example, runs coverage, and executes the Python test suite.
