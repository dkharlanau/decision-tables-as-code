from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .model import DecisionTable, table_from_mapping


def load_document(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    suffix = source.suffix.lower()
    if suffix == ".json":
        raw = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    else:
        raise ValueError(f"Unsupported file type {suffix!r}; use YAML or JSON")
    if not isinstance(raw, Mapping):
        raise ValueError("Decision table document must contain an object at the root")
    return raw


def load_table(path: str | Path) -> DecisionTable:
    return table_from_mapping(load_document(path))
