from pathlib import Path

import pytest

from decision_tables_as_code.coverage import analyze_coverage
from decision_tables_as_code.importer import SpreadsheetImportError, import_spreadsheet, load_import_config, parse_condition_cell
from decision_tables_as_code.model import table_from_mapping
from decision_tables_as_code.validate import has_errors, validate_table


ROOT = Path(__file__).parents[1]


def test_csv_import_produces_valid_table_with_full_coverage():
    document = import_spreadsheet(
        ROOT / "examples" / "order-routing.csv",
        load_import_config(ROOT / "examples" / "order-routing.import.yaml"),
    )
    table = table_from_mapping(document)
    assert not has_errors(validate_table(table))
    assert analyze_coverage(table).coverage_percent == 100.0
    assert table.rules[0].when["order_value"] == {"gte": 5000}


def test_condition_expression_parser_is_typed_and_explicit():
    assert parse_condition_cell("in(DE,AT)", "string") == ["DE", "AT"]
    assert parse_condition_cell("between(100,500)", "integer") == {"between": [100, 500]}
    assert parse_condition_cell("exists(false)", "string") == {"exists": False}


def test_blank_condition_can_be_rejected():
    with pytest.raises(SpreadsheetImportError, match="Blank condition"):
        parse_condition_cell("", "string", blank_condition="error")


def test_xlsx_import_when_openpyxl_is_available(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Rules"
    sheet.append(["Rule ID", "Country", "Result"])
    sheet.append(["DE", "DE", "A"])
    source = tmp_path / "rules.xlsx"
    workbook.save(source)

    document = import_spreadsheet(source, {
        "table": {"id": "xlsx"},
        "sheet": "Rules",
        "columns": {
            "rule_id": "Rule ID",
            "inputs": {"country": {"column": "Country", "type": "string"}},
            "outputs": {"result": {"column": "Result", "type": "string"}},
        },
    })
    assert document["rules"][0]["then"]["result"] == "A"
