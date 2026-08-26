from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .model import DecisionTable, Rule, table_from_mapping


DMN_NS = "https://www.omg.org/spec/DMN/20211108/MODEL/"
DMN_VERSION = "1.4"

_DMN_TO_DTAC_HIT_POLICY = {
    "UNIQUE": "unique",
    "FIRST": "first",
}
_DTAC_TO_DMN_HIT_POLICY = {value: key for key, value in _DMN_TO_DTAC_HIT_POLICY.items()}
_DMN_TO_DTAC_TYPE = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "date": "date",
    "Any": "any",
    "any": "any",
}
_DTAC_TO_DMN_TYPE = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "date": "date",
    "any": None,
}
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_RANGE_RE = re.compile(r"^([\[(])\s*(.*?)\s*\.\.\s*(.*?)\s*([\])])$")
_COMPARISON_RE = re.compile(r"^(<=|>=|<|>)\s*(.+)$")
_DATE_RE = re.compile(r'^date\(\s*("(?:[^"\\]|\\.)*")\s*\)$')


class DMNUnsupportedError(ValueError):
    """Raised when DMN or DTAC semantics cannot be represented by the supported subset."""


class _AnyUnaryTest:
    pass


_ANY = _AnyUnaryTest()
_ABSENT = object()


def load_dmn(path: str | Path, *, decision_id: str | None = None) -> DecisionTable:
    source = Path(path)
    try:
        root = ET.fromstring(source.read_text(encoding="utf-8"))
    except ET.ParseError as exc:
        raise ValueError(f"Invalid DMN XML: {exc}") from exc
    return decision_table_from_dmn_element(root, decision_id=decision_id)


def loads_dmn(text: str, *, decision_id: str | None = None) -> DecisionTable:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid DMN XML: {exc}") from exc
    return decision_table_from_dmn_element(root, decision_id=decision_id)


def decision_table_from_dmn_element(root: ET.Element, *, decision_id: str | None = None) -> DecisionTable:
    if root.tag != _q("definitions"):
        namespace, local = _split_tag(root.tag)
        if local == "definitions":
            raise DMNUnsupportedError(
                f"Unsupported DMN namespace {namespace!r}; this adapter accepts DMN 1.4 namespace {DMN_NS!r}"
            )
        raise ValueError("DMN document root must be definitions")

    decisions = list(root.findall(_q("decision")))
    candidates = [item for item in decisions if item.find(_q("decisionTable")) is not None]
    if decision_id is not None:
        candidates = [item for item in candidates if item.get("id") == decision_id]
        if not candidates:
            raise ValueError(f"No decision-table decision with id {decision_id!r} was found")
    elif len(candidates) != 1:
        ids = ", ".join(item.get("id", "<missing-id>") for item in candidates) or "none"
        raise ValueError(
            "DMN import requires exactly one decision-table decision unless --decision is provided; "
            f"found {len(candidates)} ({ids})"
        )

    decision = candidates[0]
    decision_table = decision.find(_q("decisionTable"))
    assert decision_table is not None

    raw_hit_policy = decision_table.get("hitPolicy", "UNIQUE").upper()
    if raw_hit_policy not in _DMN_TO_DTAC_HIT_POLICY:
        raise DMNUnsupportedError(
            f"Unsupported DMN hit policy {raw_hit_policy!r}; supported subset: UNIQUE, FIRST"
        )
    if decision_table.get("aggregation"):
        raise DMNUnsupportedError("DMN hit-policy aggregation is not supported")

    inputs = _import_inputs(decision_table)
    outputs = _import_outputs(decision_table)
    rules = _import_rules(decision_table, inputs, outputs)

    table_id = decision.get("id")
    if not table_id:
        raise ValueError("DMN decision.id is required by this adapter")
    name = decision.get("name") or table_id
    description = _optional_child_text(decision, "description")

    document: dict[str, Any] = {
        "version": 1,
        "id": table_id,
        "name": name,
        "hit_policy": _DMN_TO_DTAC_HIT_POLICY[raw_hit_policy],
        "inputs": inputs,
        "outputs": outputs,
        "rules": rules,
    }
    if description:
        document["description"] = description
    return table_from_mapping(document)


def dumps_dmn(table: DecisionTable, *, model_namespace: str | None = None) -> str:
    _check_exportable(table)
    ET.register_namespace("", DMN_NS)

    namespace = model_namespace or f"urn:dtac:{_xml_id(table.id)}"
    root = ET.Element(
        _q("definitions"),
        {
            "id": f"definitions_{_xml_id(table.id)}",
            "name": table.name,
            "namespace": namespace,
        },
    )
    decision = ET.SubElement(root, _q("decision"), {"id": table.id, "name": table.name})
    if table.description:
        _text_element(decision, "description", table.description)

    decision_table = ET.SubElement(
        decision,
        _q("decisionTable"),
        {
            "id": f"decisionTable_{_xml_id(table.id)}",
            "hitPolicy": _DTAC_TO_DMN_HIT_POLICY[table.hit_policy],
        },
    )

    for index, item in enumerate(table.inputs, start=1):
        input_node = ET.SubElement(
            decision_table,
            _q("input"),
            {"id": f"input_{index}", "label": item.name},
        )
        expression_attributes = {"id": f"inputExpression_{index}"}
        dmn_type = _export_type(item.type, f"input {item.name!r}")
        if dmn_type is not None:
            expression_attributes["typeRef"] = dmn_type
        expression = ET.SubElement(input_node, _q("inputExpression"), expression_attributes)
        _text_element(expression, "text", item.name)
        if item.domain:
            values_node = ET.SubElement(input_node, _q("inputValues"), {"id": f"inputValues_{index}"})
            _text_element(
                values_node,
                "text",
                ", ".join(_format_literal(value, item.type) for value in item.domain),
            )

    for index, item in enumerate(table.outputs, start=1):
        attributes = {"id": f"output_{index}", "name": item.name}
        dmn_type = _export_type(item.type, f"output {item.name!r}")
        if dmn_type is not None:
            attributes["typeRef"] = dmn_type
        ET.SubElement(decision_table, _q("output"), attributes)

    for rule_index, rule in enumerate(table.rules, start=1):
        rule_node = ET.SubElement(decision_table, _q("rule"), {"id": rule.id})
        for input_index, item in enumerate(table.inputs, start=1):
            entry = ET.SubElement(
                rule_node,
                _q("inputEntry"),
                {"id": f"rule_{rule_index}_input_{input_index}"},
            )
            condition = rule.when.get(item.name, _ABSENT)
            _text_element(entry, "text", _format_unary_test(condition, item.type))
        for output_index, item in enumerate(table.outputs, start=1):
            entry = ET.SubElement(
                rule_node,
                _q("outputEntry"),
                {"id": f"rule_{rule_index}_output_{output_index}"},
            )
            if item.name not in rule.then:
                raise DMNUnsupportedError(
                    f"Rule {rule.id!r} does not set output {item.name!r}; DMN export requires every output entry"
                )
            _text_element(entry, "text", _format_literal(rule.then[item.name], item.type))

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"


def dump_dmn(table: DecisionTable, path: str | Path, *, model_namespace: str | None = None) -> None:
    Path(path).write_text(dumps_dmn(table, model_namespace=model_namespace), encoding="utf-8")


def table_to_document(table: DecisionTable) -> dict[str, Any]:
    document: dict[str, Any] = {
        "version": table.version,
        "id": table.id,
        "name": table.name,
        "hit_policy": table.hit_policy,
        "inputs": [],
        "outputs": [],
        "rules": [],
    }
    if table.description:
        document["description"] = table.description
    if table.metadata:
        document["metadata"] = dict(table.metadata)

    for item in table.inputs:
        raw: dict[str, Any] = {"name": item.name, "type": item.type}
        if item.description:
            raw["description"] = item.description
        if item.domain:
            raw["domain"] = list(item.domain)
        document["inputs"].append(raw)

    for item in table.outputs:
        raw = {"name": item.name, "type": item.type}
        if item.description:
            raw["description"] = item.description
        document["outputs"].append(raw)

    for rule in table.rules:
        raw_rule: dict[str, Any] = {
            "id": rule.id,
            "when": dict(rule.when),
            "then": dict(rule.then),
        }
        if rule.description:
            raw_rule["description"] = rule.description
        if rule.priority is not None:
            raw_rule["priority"] = rule.priority
        for field_name in ("owner", "source", "ticket", "rationale", "effective_from", "effective_to"):
            value = getattr(rule, field_name)
            if value is not None:
                raw_rule[field_name] = value
        if rule.metadata:
            raw_rule["metadata"] = dict(rule.metadata)
        document["rules"].append(raw_rule)
    return document


def _import_inputs(decision_table: ET.Element) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, node in enumerate(decision_table.findall(_q("input")), start=1):
        expression = node.find(_q("inputExpression"))
        if expression is None:
            raise DMNUnsupportedError(f"DMN input {index} has no inputExpression")
        name = _required_child_text(expression, "text", f"DMN input {index} expression").strip()
        if not name:
            raise DMNUnsupportedError(f"DMN input {index} expression must be a simple non-empty fact name")
        if name in seen:
            raise ValueError(f"Duplicate DMN input expression {name!r}")
        seen.add(name)
        data_type = _import_type(expression.get("typeRef"), f"input {name!r}")
        raw: dict[str, Any] = {"name": name, "type": data_type}

        input_values = node.find(_q("inputValues"))
        if input_values is not None:
            domain_text = _required_child_text(input_values, "text", f"inputValues for {name!r}")
            parsed = _parse_unary_test(domain_text, data_type)
            if parsed is _ANY or isinstance(parsed, dict):
                raise DMNUnsupportedError(
                    f"inputValues for {name!r} must be a finite scalar list in the supported subset"
                )
            raw["domain"] = list(parsed) if isinstance(parsed, list) else [parsed]
        result.append(raw)

    if not result:
        raise DMNUnsupportedError("DMN decision table must have at least one input")
    return result


def _import_outputs(decision_table: ET.Element) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, node in enumerate(decision_table.findall(_q("output")), start=1):
        name = node.get("name")
        if not name:
            raise DMNUnsupportedError(
                f"DMN output {index} has no name; named outputs are required by this subset"
            )
        if name in seen:
            raise ValueError(f"Duplicate DMN output name {name!r}")
        seen.add(name)
        result.append({"name": name, "type": _import_type(node.get("typeRef"), f"output {name!r}")})
    if not result:
        raise DMNUnsupportedError("DMN decision table must have at least one output")
    return result


def _import_rules(
    decision_table: ET.Element,
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, node in enumerate(decision_table.findall(_q("rule")), start=1):
        input_entries = node.findall(_q("inputEntry"))
        output_entries = node.findall(_q("outputEntry"))
        if len(input_entries) != len(inputs):
            raise DMNUnsupportedError(
                f"DMN rule {node.get('id') or index!r} has {len(input_entries)} input entries; expected {len(inputs)}"
            )
        if len(output_entries) != len(outputs):
            raise DMNUnsupportedError(
                f"DMN rule {node.get('id') or index!r} has {len(output_entries)} output entries; expected {len(outputs)}"
            )

        rule_id = node.get("id") or f"rule-{index}"
        when: dict[str, Any] = {}
        for item, entry in zip(inputs, input_entries):
            text = _required_child_text(entry, "text", f"inputEntry in rule {rule_id!r}")
            parsed = _parse_unary_test(text, item["type"])
            if parsed is not _ANY:
                when[item["name"]] = parsed

        then: dict[str, Any] = {}
        for item, entry in zip(outputs, output_entries):
            text = _required_child_text(entry, "text", f"outputEntry in rule {rule_id!r}")
            then[item["name"]] = _parse_literal(text, item["type"])

        result.append({"id": rule_id, "when": when, "then": then})
    return result


def _check_exportable(table: DecisionTable) -> None:
    if table.version != 1:
        raise DMNUnsupportedError(f"DMN export supports canonical version 1, got {table.version}")
    if table.hit_policy not in _DTAC_TO_DMN_HIT_POLICY:
        raise DMNUnsupportedError(
            f"Hit policy {table.hit_policy!r} is not representable by the supported DMN subset; use unique or first"
        )
    if table.metadata:
        raise DMNUnsupportedError("Table metadata is not exported by the DMN subset; remove it or use a target-specific adapter")

    for item in table.inputs:
        _export_type(item.type, f"input {item.name!r}")
        if item.description:
            raise DMNUnsupportedError(f"Input description for {item.name!r} is not preserved by this DMN subset")
        for value in item.domain:
            _format_literal(value, item.type)
    for item in table.outputs:
        _export_type(item.type, f"output {item.name!r}")
        if item.description:
            raise DMNUnsupportedError(f"Output description for {item.name!r} is not preserved by this DMN subset")

    input_names = set(table.input_names)
    output_names = set(table.output_names)
    for rule in table.rules:
        if rule.priority is not None:
            raise DMNUnsupportedError(
                f"Rule {rule.id!r} has priority metadata; this subset preserves FIRST semantics only through rule order"
            )
        governance = {
            "description": rule.description,
            "owner": rule.owner,
            "source": rule.source,
            "ticket": rule.ticket,
            "rationale": rule.rationale,
            "effective_from": rule.effective_from,
            "effective_to": rule.effective_to,
            "metadata": dict(rule.metadata),
        }
        if any(value not in (None, {}, "") for value in governance.values()):
            raise DMNUnsupportedError(
                f"Rule {rule.id!r} contains governance/effective-date fields that standard DMN export would lose"
            )
        unknown_inputs = set(rule.when) - input_names
        if unknown_inputs:
            raise DMNUnsupportedError(
                f"Rule {rule.id!r} references unknown inputs: {', '.join(sorted(unknown_inputs))}"
            )
        if set(rule.then) != output_names:
            raise DMNUnsupportedError(
                f"Rule {rule.id!r} must set exactly the declared outputs for DMN export"
            )
        for item in table.inputs:
            _format_unary_test(rule.when.get(item.name, _ABSENT), item.type)
        for item in table.outputs:
            _format_literal(rule.then[item.name], item.type)


def _parse_unary_test(text: str, data_type: str) -> Any:
    value = text.strip()
    if value == "-":
        return _ANY
    if not value:
        raise DMNUnsupportedError("Empty DMN inputEntry is not supported; use '-' for an unrestricted input")

    if value.startswith("not(") and value.endswith(")"):
        inner = value[4:-1].strip()
        parts = _split_top_level(inner)
        if not parts:
            raise DMNUnsupportedError("DMN not() unary test must contain at least one literal")
        parsed = [_parse_literal(item, data_type) for item in parts]
        return {"ne": parsed[0]} if len(parsed) == 1 else {"not_in": parsed}

    range_match = _RANGE_RE.fullmatch(value)
    if range_match:
        lower_token, lower_text, upper_text, upper_token = range_match.groups()
        lower = _parse_literal(lower_text, data_type)
        upper = _parse_literal(upper_text, data_type)
        return {
            "gte" if lower_token == "[" else "gt": lower,
            "lte" if upper_token == "]" else "lt": upper,
        }

    comparison = _COMPARISON_RE.fullmatch(value)
    if comparison:
        operator, literal_text = comparison.groups()
        operator_map = {"<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}
        return {operator_map[operator]: _parse_literal(literal_text, data_type)}

    parts = _split_top_level(value)
    if len(parts) > 1:
        return [_parse_literal(item, data_type) for item in parts]
    return _parse_literal(value, data_type)


def _format_unary_test(condition: Any, data_type: str) -> str:
    if condition is _ABSENT:
        return "-"
    if condition == "*":
        raise DMNUnsupportedError(
            "DTAC '*' means any present value, while DMN '-' is unrestricted including null/missing; omit the condition instead"
        )
    if isinstance(condition, list):
        if not condition:
            raise DMNUnsupportedError("Empty membership lists are not supported by DMN export")
        return ", ".join(_format_literal(item, data_type) for item in condition)
    if not isinstance(condition, dict):
        return _format_literal(condition, data_type)

    keys = set(condition)
    if keys == {"eq"}:
        return _format_literal(condition["eq"], data_type)
    if keys == {"in"}:
        values = condition["in"]
        if not isinstance(values, (list, tuple)) or not values:
            raise DMNUnsupportedError("DMN export requires a non-empty list for the in operator")
        return ", ".join(_format_literal(item, data_type) for item in values)
    if keys == {"ne"}:
        return f"not({_format_literal(condition['ne'], data_type)})"
    if keys == {"not_in"}:
        values = condition["not_in"]
        if not isinstance(values, (list, tuple)) or not values:
            raise DMNUnsupportedError("DMN export requires a non-empty list for not_in")
        return "not(" + ", ".join(_format_literal(item, data_type) for item in values) + ")"
    if keys == {"between"}:
        values = condition["between"]
        if not isinstance(values, (list, tuple)) or len(values) != 2:
            raise DMNUnsupportedError("between requires exactly two values")
        return f"[{_format_literal(values[0], data_type)}..{_format_literal(values[1], data_type)}]"
    if len(keys) == 1 and next(iter(keys)) in {"gt", "gte", "lt", "lte"}:
        key = next(iter(keys))
        symbol = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[key]
        return f"{symbol} {_format_literal(condition[key], data_type)}"

    lower_keys = keys & {"gt", "gte"}
    upper_keys = keys & {"lt", "lte"}
    if len(lower_keys) == 1 and len(upper_keys) == 1 and keys == lower_keys | upper_keys:
        lower_key = next(iter(lower_keys))
        upper_key = next(iter(upper_keys))
        left = "(" if lower_key == "gt" else "["
        right = ")" if upper_key == "lt" else "]"
        return (
            f"{left}{_format_literal(condition[lower_key], data_type)}.."
            f"{_format_literal(condition[upper_key], data_type)}{right}"
        )

    unsupported = ", ".join(sorted(keys))
    raise DMNUnsupportedError(
        f"Condition operators [{unsupported}] are not representable by the supported FEEL unary-test subset"
    )


def _parse_literal(text: str, data_type: str) -> Any:
    value = text.strip()
    if not value:
        raise DMNUnsupportedError("Empty FEEL literal is not supported")
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False

    date_match = _DATE_RE.fullmatch(value)
    if date_match:
        parsed = _parse_json_string(date_match.group(1))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parsed):
            raise DMNUnsupportedError(f"Unsupported FEEL date literal {value!r}; expected date(\"YYYY-MM-DD\")")
        return parsed

    if value.startswith('"'):
        return _parse_json_string(value)
    if _NUMBER_RE.fullmatch(value):
        return float(value) if any(marker in value.lower() for marker in (".", "e")) else int(value)

    raise DMNUnsupportedError(
        f"Unsupported FEEL literal/expression {value!r}; supported literals are quoted strings, numbers, booleans, null, and date(\"YYYY-MM-DD\")"
    )


def _format_literal(value: Any, data_type: str) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        if data_type not in {"boolean", "any"}:
            raise DMNUnsupportedError(f"Boolean literal is incompatible with DTAC type {data_type!r}")
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if data_type not in {"number", "any"}:
            raise DMNUnsupportedError(
                f"Numeric literal {value!r} is not exportable for DTAC type {data_type!r}; integer type is intentionally not coerced to DMN number"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise DMNUnsupportedError("NaN and infinity are not supported FEEL literals")
        return repr(value)
    if isinstance(value, str):
        if data_type == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise DMNUnsupportedError(f"Date value {value!r} must use YYYY-MM-DD")
            return f"date({json.dumps(value, ensure_ascii=False)})"
        if data_type not in {"string", "any"}:
            raise DMNUnsupportedError(f"String literal is incompatible with DTAC type {data_type!r}")
        return json.dumps(value, ensure_ascii=False)
    raise DMNUnsupportedError(f"Unsupported literal value type for DMN export: {type(value).__name__}")


def _import_type(type_ref: str | None, context: str) -> str:
    if not type_ref:
        return "any"
    local = _type_local_name(type_ref)
    if local not in _DMN_TO_DTAC_TYPE:
        raise DMNUnsupportedError(
            f"Unsupported DMN typeRef {type_ref!r} on {context}; supported: string, number, boolean, date, Any"
        )
    return _DMN_TO_DTAC_TYPE[local]


def _export_type(data_type: str, context: str) -> str | None:
    if data_type == "integer":
        raise DMNUnsupportedError(
            f"DTAC integer type on {context} is not exported because DMN FEEL has number rather than a distinct integer built-in type"
        )
    if data_type not in _DTAC_TO_DMN_TYPE:
        raise DMNUnsupportedError(
            f"DTAC type {data_type!r} on {context} is not supported by the DMN subset"
        )
    return _DTAC_TO_DMN_TYPE[data_type]


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote = False
    escape = False
    for index, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
            continue
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
            if depth < 0:
                raise DMNUnsupportedError(f"Unbalanced FEEL unary test {text!r}")
        elif char == "," and depth == 0:
            part = text[start:index].strip()
            if not part:
                raise DMNUnsupportedError(f"Empty item in FEEL unary test {text!r}")
            parts.append(part)
            start = index + 1
    if quote or depth != 0:
        raise DMNUnsupportedError(f"Unbalanced FEEL unary test {text!r}")
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_json_string(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DMNUnsupportedError(f"Unsupported FEEL string literal {value!r}") from exc
    if not isinstance(parsed, str):
        raise DMNUnsupportedError(f"Expected FEEL string literal, got {value!r}")
    return parsed


def _required_child_text(node: ET.Element, child_name: str, context: str) -> str:
    child = node.find(_q(child_name))
    if child is None or child.text is None:
        raise DMNUnsupportedError(f"Missing {child_name} text for {context}")
    return child.text


def _optional_child_text(node: ET.Element, child_name: str) -> str | None:
    child = node.find(_q(child_name))
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _text_element(parent: ET.Element, local_name: str, text: str) -> ET.Element:
    child = ET.SubElement(parent, _q(local_name))
    child.text = text
    return child


def _q(local_name: str) -> str:
    return f"{{{DMN_NS}}}{local_name}"


def _split_tag(tag: str) -> tuple[str | None, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return None, tag


def _type_local_name(type_ref: str) -> str:
    if "}" in type_ref:
        return type_ref.rsplit("}", 1)[-1]
    if ":" in type_ref:
        return type_ref.rsplit(":", 1)[-1]
    return type_ref


def _xml_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return cleaned or "decision"
