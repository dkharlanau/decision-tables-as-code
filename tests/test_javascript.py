from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from decision_tables_as_code.engine import evaluate
from decision_tables_as_code.io import load_table
from decision_tables_as_code.javascript import (
    JavaScriptGenerationError,
    generate_javascript,
    generate_typescript_declaration,
)
from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.scenarios import load_scenarios


ROOT = Path(__file__).parents[1]
NODE = shutil.which("node")


def test_generated_module_is_dependency_free_esm_and_types_are_stable():
    table = load_table(ROOT / "examples" / "order-routing.yaml")
    source = generate_javascript(table)
    declaration = generate_typescript_declaration(table)

    assert "export function evaluate" in source
    assert "export function matchingRules" in source
    assert "from " not in source
    assert "require(" not in source
    assert 'export const tableId = TABLE.id' in source
    assert 'table_id: "order-routing"' in declaration
    assert "asOf?: string | Date" in declaration


@pytest.mark.skipif(NODE is None, reason="Node.js is required for generated-runtime parity")
@pytest.mark.parametrize(
    ("table_path", "scenario_path"),
    [
        ("examples/order-routing.yaml", "examples/order-routing.scenarios.yaml"),
        ("examples/effective-routing.yaml", "examples/effective-routing.scenarios.yaml"),
        ("examples/sap/approval-matrix.yaml", "examples/sap/approval-matrix.scenarios.yaml"),
    ],
)
def test_generated_runtime_matches_native_scenario_packs(tmp_path: Path, table_path: str, scenario_path: str):
    table = load_table(ROOT / table_path)
    scenarios = load_scenarios(ROOT / scenario_path)
    module_path = tmp_path / "decision.mjs"
    module_path.write_text(generate_javascript(table), encoding="utf-8")

    for scenario in scenarios["scenarios"]:
        facts = dict(scenario["facts"])
        as_of = scenario.get("as_of")
        native = evaluate(table, facts, as_of=as_of)
        js = _node_evaluate(module_path, facts, as_of)
        assert js == {
            "table_id": native.table_id,
            "matched_rule_ids": list(native.matched_rule_ids),
            "outputs": native.outputs,
        }, scenario["id"]


@pytest.mark.skipif(NODE is None, reason="Node.js is required for generated-runtime parity")
def test_generated_runtime_matches_all_condition_operators_and_collect(tmp_path: Path):
    table = table_from_mapping({
        "version": 1,
        "id": "operators",
        "hit_policy": "collect",
        "inputs": [
            {"name": "score", "type": "number"},
            {"name": "country", "type": "string"},
            {"name": "code", "type": "string"},
            {"name": "optional", "type": "string"},
        ],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [
            {"id": "eq", "when": {"country": {"eq": "DE"}}, "then": {"result": "eq"}},
            {"id": "ne", "when": {"country": {"ne": "PL"}}, "then": {"result": "ne"}},
            {"id": "in", "when": {"country": {"in": ["DE", "AT"]}}, "then": {"result": "in"}},
            {"id": "not-in", "when": {"country": {"not_in": ["PL", "FR"]}}, "then": {"result": "not-in"}},
            {"id": "gt", "when": {"score": {"gt": 9}}, "then": {"result": "gt"}},
            {"id": "gte", "when": {"score": {"gte": 10}}, "then": {"result": "gte"}},
            {"id": "lt", "when": {"score": {"lt": 11}}, "then": {"result": "lt"}},
            {"id": "lte", "when": {"score": {"lte": 10}}, "then": {"result": "lte"}},
            {"id": "between", "when": {"score": {"between": [5, 15]}}, "then": {"result": "between"}},
            {"id": "exists", "when": {"optional": {"exists": False}}, "then": {"result": "exists"}},
            {"id": "regex", "when": {"code": {"regex": "[A-Z]{2}-[0-9]{3}"}}, "then": {"result": "regex"}},
            {"id": "list", "when": {"country": ["DE", "CH"]}, "then": {"result": "list"}},
            {"id": "wildcard", "when": {"country": "*"}, "then": {"result": "wildcard"}},
        ],
    })
    facts = {"score": 10, "country": "DE", "code": "AB-123"}
    native = evaluate(table, facts)
    module_path = tmp_path / "operators.mjs"
    module_path.write_text(generate_javascript(table), encoding="utf-8")
    js = _node_evaluate(module_path, facts, None)

    assert js["matched_rule_ids"] == list(native.matched_rule_ids)
    assert js["outputs"] == native.outputs


def test_python_specific_regex_is_rejected_explicitly():
    table = table_from_mapping({
        "version": 1,
        "id": "regex-portability",
        "inputs": [{"name": "value", "type": "string"}],
        "outputs": [{"name": "result", "type": "string"}],
        "rules": [{"id": "r", "when": {"value": {"regex": "(?P<name>.+)"}}, "then": {"result": "x"}}],
    })
    with pytest.raises(JavaScriptGenerationError, match="Python-specific regex"):
        generate_javascript(table)


def _node_evaluate(module_path: Path, facts: dict, as_of) -> dict:
    runner = module_path.with_name("runner.mjs")
    runner.write_text(
        "import { evaluate } from './" + module_path.name + "';\n"
        "const facts = JSON.parse(process.argv[2]);\n"
        "const asOf = process.argv[3] === '' ? undefined : process.argv[3];\n"
        "process.stdout.write(JSON.stringify(evaluate(facts, { asOf })));\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [NODE, str(runner), json.dumps(facts, default=str), "" if as_of is None else str(as_of)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
