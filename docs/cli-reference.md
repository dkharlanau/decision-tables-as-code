# CLI reference

This file is generated from the actual `argparse` command definitions. Do not edit command signatures here by hand.

Regenerate it with:

```bash
python scripts/generate_cli_reference.py
```

Use `--check` in CI to fail when the checked-in reference is stale.

## `dtac coverage`

```text
dtac coverage <table> [--max-combinations <max-combinations>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--max-combinations` `<max-combinations>` | no | `10000` | — | — |

## `dtac diff`

```text
dtac diff <before> <after> [--output <output>] [--fail-on <fail-on>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `before` | yes | — | — | — |
| `after` | yes | — | — | — |
| `--output` `<output>` | no | — | — | Write JSON semantic diff to a file instead of stdout |
| `--fail-on` `<fail-on>` | no | `any` | `any`, `potentially-breaking`, `breaking`, `never` | Exit 1 for the selected change threshold; default preserves legacy behavior and fails on any change |

## `dtac dmn-export`

```text
dtac dmn-export <table> [--model-namespace <model-namespace>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--model-namespace` `<model-namespace>` | no | — | — | DMN definitions namespace; defaults to a deterministic urn:dtac namespace |
| `--output` `<output>` | no | — | — | Write DMN XML to a file instead of stdout |

## `dtac dmn-import`

```text
dtac dmn-import <source> [--decision <decision>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `source` | yes | — | — | — |
| `--decision` `<decision>` | no | — | — | Decision id when the DMN document contains multiple decision tables |
| `--output` `<output>` | no | — | — | Write canonical YAML to a file instead of stdout |

## `dtac eval`

```text
dtac eval <table> --facts <facts> [--as-of <as-of>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--facts` `<facts>` | yes | — | — | JSON object or @path/to/facts.json |
| `--as-of` `<as-of>` | no | — | — | Explicit YYYY-MM-DD date used for effective-dated rules |

## `dtac explain`

```text
dtac explain <table> --facts <facts> [--as-of <as-of>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--facts` `<facts>` | yes | — | — | JSON object or @path/to/facts.json |
| `--as-of` `<as-of>` | no | — | — | Explicit YYYY-MM-DD date used for effective-dated rules |
| `--output` `<output>` | no | — | — | Write JSON explanation to a file instead of stdout |

## `dtac import`

```text
dtac import <source> --config <config> [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `source` | yes | — | — | — |
| `--config` `<config>` | yes | — | — | — |
| `--output` `<output>` | no | — | — | — |

## `dtac inspect`

```text
dtac inspect <table> [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--output` `<output>` | no | — | — | Write JSON inspection output to a file instead of stdout |

## `dtac package-diff`

```text
dtac package-diff <before> <after> [--output <output>] [--fail-on <fail-on>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `before` | yes | — | — | — |
| `after` | yes | — | — | — |
| `--output` `<output>` | no | — | — | Write package diff JSON to a file instead of stdout |
| `--fail-on` `<fail-on>` | no | `any` | `any`, `never` | — |

## `dtac package-eval`

```text
dtac package-eval <manifest> --facts <facts> [--as-of <as-of>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `manifest` | yes | — | — | — |
| `--facts` `<facts>` | yes | — | — | JSON object or @path/to/facts.json |
| `--as-of` `<as-of>` | no | — | — | Explicit YYYY-MM-DD date passed to effective-dated tables |
| `--output` `<output>` | no | — | — | Write package result JSON to a file instead of stdout |

## `dtac package-graph`

```text
dtac package-graph <manifest> [--format <output-format>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `manifest` | yes | — | — | — |
| `--format` `<output-format>` | no | `json` | `json`, `dot`, `mermaid` | — |
| `--output` `<output>` | no | — | — | Write graph output to a file instead of stdout |

## `dtac package-impact`

```text
dtac package-impact <manifest> --changed <changed> [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `manifest` | yes | — | — | — |
| `--changed` `<changed>` | yes | — | — | Changed table id; repeat for multiple tables |
| `--output` `<output>` | no | — | — | Write impact JSON to a file instead of stdout |

## `dtac package-validate`

```text
dtac package-validate <manifest> [--format <output-format>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `manifest` | yes | — | — | — |
| `--format` `<output-format>` | no | `text` | `text`, `json` | — |
| `--output` `<output>` | no | — | — | Write validation output to a file instead of stdout |

## `dtac render`

```text
dtac render <table> [--format <format>] [--output <output>] [--coverage] [--against <against>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--format` `<format>` | no | `markdown` | `markdown`, `html` | — |
| `--output` `<output>` | no | — | — | — |
| `--coverage` | no | false | — | — |
| `--against` `<against>` | no | — | — | Previous table version for semantic change highlighting |

## `dtac test`

```text
dtac test <table> <scenarios> [--json]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `scenarios` | yes | — | — | — |
| `--json` | no | false | — | — |

## `dtac validate`

```text
dtac validate <table> [--format <output-format>] [--output <output>]
```

| Argument | Required | Default | Choices | Help |
| --- | --- | --- | --- | --- |
| `table` | yes | — | — | — |
| `--format` `<output-format>` | no | `text` | `text`, `json`, `sarif`, `github` | — |
| `--output` `<output>` | no | — | — | Write validation output to a file instead of stdout |
