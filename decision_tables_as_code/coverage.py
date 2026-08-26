from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Any

from .engine import matching_rules
from .model import DecisionTable


@dataclass(frozen=True)
class CoverageReport:
    evaluated_combinations: int
    covered_combinations: int
    uncovered: tuple[dict[str, Any], ...]
    ambiguous: tuple[dict[str, Any], ...]

    @property
    def coverage_percent(self) -> float:
        if self.evaluated_combinations == 0:
            return 0.0
        return round(100 * self.covered_combinations / self.evaluated_combinations, 2)


def analyze_coverage(table: DecisionTable, *, max_combinations: int = 10_000) -> CoverageReport:
    missing_domains = [item.name for item in table.inputs if not item.domain]
    if missing_domains:
        raise ValueError("Coverage requires domain values for every input; missing: " + ", ".join(missing_domains))

    total = prod(len(item.domain) for item in table.inputs)
    if total > max_combinations:
        raise ValueError(f"Coverage would evaluate {total} combinations; limit is {max_combinations}")

    uncovered: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    covered = 0

    for values in product(*(item.domain for item in table.inputs)):
        facts = dict(zip(table.input_names, values))
        matches = matching_rules(table, facts)
        if not matches:
            uncovered.append(facts)
        else:
            covered += 1
            if table.hit_policy == "unique" and len(matches) > 1:
                ambiguous.append({"facts": facts, "rules": [rule.id for rule in matches]})

    return CoverageReport(total, covered, tuple(uncovered), tuple(ambiguous))
