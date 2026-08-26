from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .validate import Diagnostic


SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
TOOL_NAME = "Decision Tables as Code"
TOOL_URI = "https://github.com/dkharlanau/decision-tables-as-code"


_DIAGNOSTIC_TITLES = {
    "DT001": "Unsupported format version",
    "DT002": "Unsupported hit policy",
    "DT003": "Missing input contract",
    "DT004": "Missing output contract",
    "DT005": "No rules defined",
    "DT010": "Duplicate contract name",
    "DT011": "Unsupported data type",
    "DT020": "Duplicate rule identifier",
    "DT021": "Unknown input reference",
    "DT022": "Unknown output reference",
    "DT023": "Missing rule output",
    "DT030": "Duplicate rule",
    "DT031": "Conflicting exact rules",
    "DT032": "Proven UNIQUE overlap",
    "DT033": "Shadowed FIRST rule",
    "DT040": "Invalid condition",
}


def diagnostics_to_sarif(diagnostics: Iterable[Diagnostic], source_path: str | Path) -> dict:
    findings = tuple(diagnostics)
    source_uri = _source_uri(source_path)
    codes = sorted({item.code for item in findings})
    rules = [_sarif_rule(code) for code in codes]
    results = [_sarif_result(item, source_uri) for item in findings]
    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "informationUri": TOOL_URI,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def sarif_json(diagnostics: Iterable[Diagnostic], source_path: str | Path) -> str:
    return json.dumps(diagnostics_to_sarif(diagnostics, source_path), indent=2, ensure_ascii=False) + "\n"


def diagnostics_to_github_annotations(diagnostics: Iterable[Diagnostic], source_path: str | Path) -> str:
    source = _annotation_escape_property(str(source_path).replace("\\", "/"))
    lines: list[str] = []
    for item in diagnostics:
        command = "error" if item.severity == "error" else "warning" if item.severity == "warning" else "notice"
        title = _annotation_escape_property(f"{item.code} {_DIAGNOSTIC_TITLES.get(item.code, 'Decision table finding')}")
        message = _annotation_escape_message(f"{item.path}: {item.message}")
        lines.append(f"::{command} file={source},title={title}::{message}")
    return "\n".join(lines) + ("\n" if lines else "")


def _sarif_rule(code: str) -> dict:
    title = _DIAGNOSTIC_TITLES.get(code, "Decision table finding")
    return {
        "id": code,
        "name": code,
        "shortDescription": {"text": title},
        "helpUri": f"{TOOL_URI}/blob/main/docs/diagnostics.md#{code.lower()}",
    }


def _sarif_result(item: Diagnostic, source_uri: str) -> dict:
    level = "error" if item.severity == "error" else "warning" if item.severity == "warning" else "note"
    return {
        "ruleId": item.code,
        "level": level,
        "message": {"text": item.message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": source_uri}
                },
                "logicalLocations": [
                    {"name": item.path, "kind": "decisionTablePath"}
                ],
            }
        ],
        "properties": {
            "decisionTablePath": item.path,
            "severity": item.severity,
        },
    }


def _source_uri(source_path: str | Path) -> str:
    return str(source_path).replace("\\", "/")


def _annotation_escape_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _annotation_escape_property(value: str) -> str:
    return (
        _annotation_escape_message(value)
        .replace(":", "%3A")
        .replace(",", "%2C")
    )
