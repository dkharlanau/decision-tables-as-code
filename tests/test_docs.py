from __future__ import annotations

import json
import re
from pathlib import Path

from decision_tables_as_code.cli import build_parser


ROOT = Path(__file__).parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
AUTHOR_FOOTER = """## About the author

Created and maintained by **Dzmitryi Kharlanau**, an SAP consultant and system analyst working across enterprise architecture, data, integration, operations, and practical AI.

- [Website and knowledge base](https://dkharlanau.github.io/)
- [LinkedIn](https://www.linkedin.com/in/dkharlanau/)"""


def test_local_markdown_links_resolve():
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("README.md")),
    ]
    broken: list[str] = []

    for document in documents:
        text = document.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{document.relative_to(ROOT)} -> {raw_target}")

    assert not broken, "Broken local documentation links:\n" + "\n".join(broken)


def test_use_case_gallery_points_to_runnable_examples():
    required = [
        "examples/order-routing.yaml",
        "examples/order-routing-v2.yaml",
        "examples/order-routing.scenarios.yaml",
        "examples/order-routing.csv",
        "examples/order-routing.import.yaml",
        "examples/effective-routing.yaml",
        "examples/effective-routing.scenarios.yaml",
        "docs/behavioral-compatibility.md",
        "docs/policy-packs.md",
        "policies/enterprise-governance.yaml",
        "policies/sap-change-control.yaml",
        "examples/policy/governed-routing.yaml",
        "schema/policy-pack.schema.json",
        "examples/dmn/routing-unique.dmn",
        "examples/dmn/approval-first.dmn",
        "examples/package/order-approval/package.yaml",
        "examples/package/order-approval/risk-classification.yaml",
        "examples/package/order-approval/approval-decision.yaml",
        "examples/package/order-approval/fulfillment-route.yaml",
        "examples/package/order-approval/README.md",
        "schema/decision-package.schema.json",
        "schema/release-manifest.schema.json",
        "docs/release-bundles.md",
        "examples/sap/approval-matrix.yaml",
        "examples/sap/approval-matrix.scenarios.yaml",
        "examples/sap/customer-account-group-derivation.yaml",
        "examples/sap/customer-account-group-derivation.scenarios.yaml",
        "examples/sap/interface-replication-filter.yaml",
        "examples/sap/interface-replication-filter.scenarios.yaml",
        "examples/sap/tax-classification.yaml",
        "examples/sap/tax-classification.scenarios.yaml",
    ]

    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, "Missing use-case examples: " + ", ".join(missing)


def test_agent_entrypoints_use_supported_cli_commands():
    manifest = json.loads((ROOT / "docs" / "agent-manifest.json").read_text(encoding="utf-8"))
    parser = build_parser()
    command_action = next(action for action in parser._actions if action.dest == "command")
    supported = set(command_action.choices)

    advertised = {
        entry["command"].split()[1]
        for entry in manifest["entrypoints"]
        if entry.get("type") == "cli"
    }

    assert advertised <= supported


def test_public_agent_guidance_does_not_advertise_retired_commands():
    public_guidance = "\n".join(
        [
            (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "product.html").read_text(encoding="utf-8"),
        ]
    )

    for command in ("dtac lint ", "dtac run ", "dtac doc "):
        assert command not in public_guidance


def test_readme_ends_with_exact_author_footer_and_suite_guide():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").rstrip()
    assert readme.endswith(AUTHOR_FOOTER)
    assert readme.count("## About the author") == 1
    assert "docs/as-code-suite.md" in readme
    for repository in ("mapping-as-code", "interface-as-code", "process-as-code", "reconciliation-as-code"):
        assert f"https://github.com/dkharlanau/{repository}" in readme


def test_agent_manifest_navigates_the_core_suite():
    manifest = json.loads((ROOT / "docs" / "agent-manifest.json").read_text(encoding="utf-8"))
    assert {item["product"] for item in manifest["related"]} == {
        "mapping-as-code", "interface-as-code", "process-as-code", "reconciliation-as-code"
    }
