"""Unit tests for the XLSX exporter (schema-driven)."""

import openpyxl
import pytest

from src.core.analysis import build_column_specs, build_default_analyzers
from src.core.exporter import export_to_xlsx

pytestmark = pytest.mark.unit


def _result(**overrides):
    base = {
        "filename": "doc.pdf",
        "year": "2020",
        "president": "Jair Bolsonaro",
        "document": "Mensagem ao Congresso Nacional",
        "total_pages": 3,
        "pages_with_text": 3,
        "pages_problematic": 0,
        "ocr_pages_count": 0,
        "words_total": 100,
        "words_analytical": 80,
        "confidence": "Alto",
        "observations": "ok",
        "excluded_pages": [],
    }
    base.update(overrides)
    return base


def test_export_creates_main_and_excluded_sheets(tmp_path):
    out = tmp_path / "r.xlsx"
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    export_to_xlsx([_result()], str(out), specs)
    wb = openpyxl.load_workbook(out)
    assert "Contagem de Palavras" in wb.sheetnames
    assert "Páginas Excluídas" in wb.sheetnames


def test_export_writes_values_in_schema_order(tmp_path):
    out = tmp_path / "r.xlsx"
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    export_to_xlsx([_result()], str(out), specs)
    ws = openpyxl.load_workbook(out)["Contagem de Palavras"]
    header = [c.value for c in ws[1]]
    row = [c.value for c in ws[2]]
    assert header[0] == "Nº Doc."
    assert row[0] == 1  # doc_id auto-assigned
    assert "Jair Bolsonaro" in row


def test_export_infers_schema_without_specs(tmp_path):
    out = tmp_path / "r.xlsx"
    result = _result(
        term_results={
            "clima": {"total": 5, "analytical": 4, "exact": False, "term": "clima"}
        },
        _term_clima_total=5,
        _term_clima_analytical=4,
    )
    export_to_xlsx([result], str(out))  # no column_specs -> inferred
    ws = openpyxl.load_workbook(out)["Contagem de Palavras"]
    header = [c.value for c in ws[1]]
    assert any(h and "clima" in h for h in header)


def test_excluded_pages_written_to_second_sheet(tmp_path):
    out = tmp_path / "r.xlsx"
    result = _result(
        excluded_pages=[
            {"page_number": 1, "exclusion_reason": "provável capa", "word_count": 12}
        ]
    )
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    export_to_xlsx([result], str(out), specs)
    ws = openpyxl.load_workbook(out)["Páginas Excluídas"]
    assert ws.cell(row=2, column=3).value == 1  # page number
    assert ws.cell(row=2, column=4).value == "provável capa"


def test_keyword_sheet_when_present(tmp_path):
    out = tmp_path / "r.xlsx"
    result = _result(lex_ttr=0.5, keyword_freq=[("desenvolvimento", 12), ("clima", 7)])
    export_to_xlsx([result], str(out))  # inferred schema detects text metrics
    wb = openpyxl.load_workbook(out)
    assert "Frequência de Palavras" in wb.sheetnames
    ws = wb["Frequência de Palavras"]
    assert ws.cell(row=2, column=3).value == "desenvolvimento"
    assert ws.cell(row=2, column=4).value == 12


def test_kwic_sheet_when_present(tmp_path):
    out = tmp_path / "r.xlsx"
    result = _result(
        kwic=[
            {
                "page": 2,
                "term": "clima",
                "left": "o",
                "keyword": "clima",
                "right": "mudou",
            }
        ]
    )
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    export_to_xlsx([result], str(out), specs)
    wb = openpyxl.load_workbook(out)
    assert "Concordância (KWIC)" in wb.sheetnames
    ws = wb["Concordância (KWIC)"]
    assert ws.cell(row=2, column=4).value == "clima"  # termo
    assert ws.cell(row=2, column=6).value == "clima"  # ocorrência


def test_sentiment_sheet_only_when_present(tmp_path):
    out = tmp_path / "r.xlsx"
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    export_to_xlsx([_result()], str(out), specs)
    assert "Sentimento (Sentenças)" not in openpyxl.load_workbook(out).sheetnames

    out2 = tmp_path / "r2.xlsx"
    result = _result(
        sent_n_sentencas=1,
        sentiment_sentences=[
            {"page": 1, "text": "Foi bom.", "compound": 0.4, "classe": "Positivo"}
        ],
    )
    export_to_xlsx([result], str(out2))
    assert "Sentimento (Sentenças)" in openpyxl.load_workbook(out2).sheetnames
