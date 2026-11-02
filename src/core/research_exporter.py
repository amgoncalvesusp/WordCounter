"""Auditable legislative and PET workbooks with atomic replacement."""

import json
import os
import tempfile
from contextlib import contextmanager
from itertools import chain
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from .exporter import ALT_ROW_FILL, HEADER_FILL, HEADER_FONT, ExcelExportError, _write_cell

MAX_ROWS = 1_048_576
MAX_CELL_CHARS = 32_767


@contextmanager
def _workbook(path):
    workbook = Workbook()
    workbook.remove(workbook.active)
    temporary = None
    try:
        yield workbook
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(
            prefix=".wordcounter-", suffix=".xlsx", dir=destination.parent
        )
        temporary = Path(filename)
        os.close(descriptor)
        workbook.save(temporary)
        os.replace(temporary, destination)
    except (OSError, ValueError) as exc:
        raise ExcelExportError(f"Não foi possível salvar a planilha: {exc}") from exc
    finally:
        workbook.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _sheet(workbook, name, headers, rows):
    sheet = workbook.create_sheet(name)
    sheet.freeze_panes = "A2"
    for row_number, values in enumerate(chain((headers,), rows), 1):
        if row_number > MAX_ROWS:
            raise ExcelExportError(
                f"A aba '{name}' excede o limite de {MAX_ROWS} linhas do Excel."
            )
        for column, value in enumerate(values, 1):
            if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
                raise ExcelExportError(
                    f"Aba '{name}', linha {row_number}: texto excede 32767 caracteres."
                )
            cell = _write_cell(sheet, row_number, column, value)
            if isinstance(value, str):
                cell.data_type = "s"
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if row_number == 1:
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
                sheet.column_dimensions[get_column_letter(column)].width = 24
            elif row_number % 2 == 0:
                cell.fill = ALT_ROW_FILL
    sheet.auto_filter.ref = sheet.dimensions
    sheet.row_dimensions[1].height = 32
    return sheet


def _parts(text):
    return (
        text[start:start + MAX_CELL_CHARS]
        for start in range(0, max(1, len(text)), MAX_CELL_CHARS)
    )


def _parameter_rows(parameters):
    for key, value in parameters.items():
        text = value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, default=str, allow_nan=False
        )
        for part, chunk in enumerate(_parts(text), 1):
            yield str(key), part, chunk


def _decision(value):
    return "Pendente" if value is None else "Sim" if value else "Não"


def _proposition_rows(results):
    for result in results:
        item = result.proposition
        yield (
            item.house, item.identifier, item.year, item.kind,
            _decision(result.automatic),
            "Automático" if result.review is None else _decision(result.review),
            _decision(result.climatic), result.note, item.source_file,
        )


def _text_rows(results):
    for result in results:
        item = result.proposition
        for field, text in item.texts:
            for part, chunk in enumerate(_parts(text), 1):
                yield item.house, item.identifier, field, part, chunk


def _evidence_rows(results):
    for result in results:
        for evidence in result.evidence:
            yield (
                result.proposition.house, result.proposition.identifier,
                evidence.field, evidence.term, evidence.snippet,
            )


def export_legislative_analysis(results, summary, path, parameters=None):
    """Export decisions, original texts, evidence and the selected annual universe."""
    results = tuple(results)
    summary = tuple(summary)
    with _workbook(path) as workbook:
        _sheet(workbook, "Proposições", (
            "Casa", "Identificador", "Ano", "Tipo", "Automático: climático?",
            "Revisão: climático?", "Final: climático?", "Nota de revisão", "Arquivo(s)",
        ), _proposition_rows(results))
        _sheet(workbook, "Textos", (
            "Casa", "Identificador", "Campo", "Parte", "Texto original",
        ), _text_rows(results))
        _sheet(workbook, "Evidências", (
            "Casa", "Identificador", "Campo", "Termo", "Trecho",
        ), _evidence_rows(results))
        keys = (
            "house", "year", "total", "climatic", "not_identified", "pending",
            "attention_pct", "identified_pct",
        )
        _sheet(workbook, "Resumo Anual", (
            "Casa", "Ano", "Total único", "Climáticas identificadas",
            "Não identificadas", "Pendentes", "Atenção (%)",
            "Mínimo identificado (%)",
        ), (tuple(row.get(key) for key in keys) for row in summary))
        _sheet(workbook, "Parâmetros", ("Parâmetro", "Parte", "Valor"),
               _parameter_rows(parameters or {}))


def _statistic_rows(analysis):
    method = {
        "difference": "Diferença absoluta",
        "relative": "Variação relativa (%)",
    }.get(analysis["method"], analysis["method"])
    yield "Método de mudança", method
    yield "Níveis anuais", analysis["n_levels"]
    yield "Mudanças válidas", analysis["n_changes"]
    yield "Curtose de Pearson (excesso corrigido + 3)", analysis["pearson_kurtosis"]
    yield "Excesso de curtose amostral corrigido (Excel CURT)", analysis["excess_kurtosis"]
    yield "L-curtose amostral (l4/l2)", analysis["l_kurtosis"]
    yield "Referência normal — Pearson", 3
    yield "Referência normal — excesso", 0
    yield "Referência normal — L-curtose", 0.1226
    yield "Zeros e lacunas", "Sem pseudocontagem; transições inválidas ficam vazias."
    yield "Interpretação", "Medidas descritivas; não confirmam a PET isoladamente."
    for number, warning in enumerate(analysis["warnings"], 1):
        yield f"Aviso {number}", warning


def _change_rows(analysis):
    for point in analysis["changes"]:
        reason = ""
        if point["change"] is None:
            if point["year"] != point["previous_year"] + 1:
                reason = "Anos não consecutivos"
            elif analysis["method"] == "relative" and point["previous_value"] == 0:
                reason = "Base anterior zero"
            else:
                reason = "Variação não finita"
        yield (
            point["previous_year"], point["year"], point["previous_value"],
            point["value"], point["change"], reason,
        )


def export_pet_analysis(analysis, path, label="", unit="", parameters=None):
    """Export the original series and each annual transition, including exclusions."""
    metadata = {**(parameters or {}), "Série": label, "Unidade": unit,
                "Método": analysis["method"]}
    with _workbook(path) as workbook:
        _sheet(workbook, "Série", ("Ano", "Valor"), (
            (point["year"], point["value"]) for point in analysis["levels"]
        ))
        _sheet(workbook, "Mudanças", (
            "Ano anterior", "Ano", "Valor anterior", "Valor", "Mudança", "Exclusão",
        ), _change_rows(analysis))
        _sheet(workbook, "Estatísticas", ("Medida", "Valor"), _statistic_rows(analysis))
        _sheet(workbook, "Parâmetros", ("Parâmetro", "Parte", "Valor"),
               _parameter_rows(metadata))
