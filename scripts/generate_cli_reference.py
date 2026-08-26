from __future__ import annotations

import argparse
import sys
from pathlib import Path

from decision_tables_as_code.cli import build_parser


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "cli-reference.md"


def generate_reference() -> str:
    parser = build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    lines = [
        "# CLI reference",
        "",
        "This file is generated from the actual `argparse` command definitions. Do not edit command signatures here by hand.",
        "",
        "Regenerate it with:",
        "",
        "```bash",
        "python scripts/generate_cli_reference.py",
        "```",
        "",
        "Use `--check` in CI to fail when the checked-in reference is stale.",
        "",
    ]

    for command in sorted(subparsers.choices):
        command_parser = subparsers.choices[command]
        actions = [
            action
            for action in command_parser._actions
            if action.dest != "help" and action.help is not argparse.SUPPRESS
        ]
        lines.extend([
            f"## `dtac {command}`",
            "",
            "```text",
            _usage(command, actions),
            "```",
            "",
            "| Argument | Required | Default | Choices | Help |",
            "| --- | --- | --- | --- | --- |",
        ])
        for action in actions:
            lines.append(
                "| "
                + " | ".join([
                    _escape(_argument_label(action)),
                    "yes" if _is_required(action) else "no",
                    _escape(_format_default(action)),
                    _escape(_format_choices(action)),
                    _escape(action.help or "—"),
                ])
                + " |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _usage(command: str, actions: list[argparse.Action]) -> str:
    tokens = ["dtac", command]
    for action in actions:
        if action.option_strings:
            option = action.option_strings[0]
            if action.nargs == 0:
                token = option
            else:
                token = f"{option} <{action.dest.replace('_', '-')}>"
            if not action.required:
                token = f"[{token}]"
        else:
            token = f"<{action.dest}>"
            if action.nargs in ("?", "*"):
                token = f"[{token}]"
        tokens.append(token)
    return " ".join(tokens)


def _argument_label(action: argparse.Action) -> str:
    if action.option_strings:
        label = ", ".join(f"`{item}`" for item in action.option_strings)
        if action.nargs != 0:
            label += f" `<{action.dest.replace('_', '-')}>`"
        return label
    return f"`{action.dest}`"


def _is_required(action: argparse.Action) -> bool:
    if action.option_strings:
        return bool(action.required)
    return action.nargs not in ("?", "*")


def _format_default(action: argparse.Action) -> str:
    if action.default is argparse.SUPPRESS or action.default is None:
        return "—"
    if isinstance(action.default, bool):
        return "true" if action.default else "false"
    return f"`{action.default}`"


def _format_choices(action: argparse.Action) -> str:
    if action.choices is None:
        return "—"
    return ", ".join(f"`{item}`" for item in action.choices)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check = args == ["--check"]
    if args and not check:
        raise SystemExit("usage: generate_cli_reference.py [--check]")

    generated = generate_reference()
    if check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            print("docs/cli-reference.md is stale; run python scripts/generate_cli_reference.py", file=sys.stderr)
            return 1
        return 0

    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
