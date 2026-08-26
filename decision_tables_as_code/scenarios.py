from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from .engine import evaluate
from .model import DecisionTable


@dataclass(frozen=True)
class ScenarioResult:
    id: str
    passed: bool
    message: str
    facts: Mapping[str, Any]
    expected: Mapping[str, Any]
    actual: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioReport:
    total: int
    passed: int
    failed: int
    results: tuple[ScenarioResult, ...]

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "results": [item.to_dict() for item in self.results],
        }


def load_scenarios(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        raw = json.loads(text)
    elif source.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    else:
        raise ValueError("Scenario file must be YAML or JSON")
    if not isinstance(raw, Mapping):
        raise ValueError("Scenario file must contain an object at the root")
    return raw


def run_scenarios(table: DecisionTable, document: Mapping[str, Any]) -> ScenarioReport:
    version = document.get("version", 1)
    if version != 1:
        raise ValueError(f"Unsupported scenario format version {version!r}")

    declared_table = document.get("table")
    if declared_table is not None and declared_table != table.id:
        raise ValueError(f"Scenario file targets table {declared_table!r}, not {table.id!r}")

    raw_scenarios = document.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ValueError("scenarios must be a non-empty array")

    results: list[ScenarioResult] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_scenarios, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError(f"scenarios[{index - 1}] must be an object")
        scenario_id = raw.get("id", f"scenario-{index}")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError(f"scenarios[{index - 1}].id must be a non-empty string")
        if scenario_id in seen_ids:
            raise ValueError(f"Duplicate scenario id {scenario_id!r}")
        seen_ids.add(scenario_id)

        facts = raw.get("facts")
        expected = raw.get("expect")
        as_of = _normalize_as_of(raw.get("as_of"), scenario_id)
        if not isinstance(facts, Mapping):
            raise ValueError(f"Scenario {scenario_id!r}: facts must be an object")
        if not isinstance(expected, Mapping):
            raise ValueError(f"Scenario {scenario_id!r}: expect must be an object")

        results.append(_run_one(table, scenario_id, dict(facts), dict(expected), as_of=as_of))

    passed = sum(item.passed for item in results)
    return ScenarioReport(len(results), passed, len(results) - passed, tuple(results))


def _run_one(
    table: DecisionTable,
    scenario_id: str,
    facts: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    as_of: str | None = None,
) -> ScenarioResult:
    expected_error = expected.get("error")
    if expected_error is not None and not isinstance(expected_error, str):
        raise ValueError(f"Scenario {scenario_id!r}: expect.error must be a string")

    try:
        result = evaluate(table, facts, as_of=as_of)
    except Exception as exc:  # scenario runner compares deterministic engine failures
        actual = {"error": str(exc), "error_type": type(exc).__name__}
        if as_of is not None:
            actual["as_of"] = as_of
        if expected_error is not None and expected_error in str(exc):
            return ScenarioResult(scenario_id, True, "expected error observed", facts, expected, actual)
        if expected_error is not None:
            return ScenarioResult(
                scenario_id,
                False,
                f"expected error containing {expected_error!r}, got {str(exc)!r}",
                facts,
                expected,
                actual,
            )
        return ScenarioResult(scenario_id, False, f"unexpected error: {exc}", facts, expected, actual)

    actual = {
        "outputs": result.outputs,
        "matched_rules": list(result.matched_rule_ids),
    }
    if as_of is not None:
        actual["as_of"] = as_of
    if expected_error is not None:
        return ScenarioResult(
            scenario_id,
            False,
            f"expected error containing {expected_error!r}, but evaluation succeeded",
            facts,
            expected,
            actual,
        )

    mismatches: list[str] = []
    if "outputs" in expected and expected["outputs"] != result.outputs:
        mismatches.append(f"outputs expected {expected['outputs']!r}, got {result.outputs!r}")
    if "matched_rules" in expected:
        raw_rules = expected["matched_rules"]
        if not isinstance(raw_rules, list) or not all(isinstance(item, str) for item in raw_rules):
            raise ValueError(f"Scenario {scenario_id!r}: expect.matched_rules must be an array of strings")
        if tuple(raw_rules) != result.matched_rule_ids:
            mismatches.append(
                f"matched_rules expected {raw_rules!r}, got {list(result.matched_rule_ids)!r}"
            )
    if "outputs" not in expected and "matched_rules" not in expected:
        raise ValueError(
            f"Scenario {scenario_id!r}: expect must contain outputs, matched_rules, or error"
        )

    if mismatches:
        return ScenarioResult(scenario_id, False, "; ".join(mismatches), facts, expected, actual)
    return ScenarioResult(scenario_id, True, "passed", facts, expected, actual)


def _normalize_as_of(value: Any, scenario_id: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise ValueError(f"Scenario {scenario_id!r}: as_of must be an ISO date string")
