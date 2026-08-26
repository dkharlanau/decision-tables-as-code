from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .io import load_table
from .runtime import generate_python
from .validate import has_errors, validate_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dtac-python-export",
        description="Generate a dependency-free Python runtime from a DTAC decision table",
    )
    parser.add_argument("table", help="Canonical YAML/JSON decision table")
    parser.add_argument("--output", "-o", required=True, help="Generated .py module path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        table = load_table(args.table)
        diagnostics = validate_table(table)
        if has_errors(diagnostics):
            for item in diagnostics:
                print(
                    f"{item.severity.upper():7} {item.code} {item.path}: {item.message}",
                    file=sys.stderr,
                )
            return 1
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(generate_python(table), encoding="utf-8")
        print(f"Wrote {output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
