from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_local_markdown_links_resolve():
    documents = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
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
        "examples/order-routing.scenarios.yaml",
        "examples/order-routing.csv",
        "examples/order-routing.import.yaml",
        "examples/effective-routing.yaml",
        "examples/effective-routing.scenarios.yaml",
        "examples/dmn/routing-unique.dmn",
        "examples/dmn/approval-first.dmn",
        "examples/package/order-approval/package.yaml",
        "examples/package/order-approval/risk-classification.yaml",
        "examples/package/order-approval/approval-decision.yaml",
        "examples/package/order-approval/fulfillment-route.yaml",
        "examples/package/order-approval/README.md",
        "schema/decision-package.schema.json",
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
