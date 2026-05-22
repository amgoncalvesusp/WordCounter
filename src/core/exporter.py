"""Export results to XLSX."""
from pathlib import Path
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
TERM_HEADER_FILL = PatternFill(start_color="7B5CB8", end_color="7B5CB8", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
ALT_ROW_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

BASE_COLUMNS = [
    ("doc_id", "Nº Doc.", 8),
    ("filename", "Nome do Arquivo", 35),
    ("year", "Ano", 8),
    ("president", "Presidente", 28),
    ("document", "Documento", 32),
    ("total_pages", "Total de Páginas", 12),
    ("pages_with_text", "Páginas c/ Texto", 14),
    ("pages_problematic", "Páginas Problemáticas", 16),
    ("ocr_pages_count", "Páginas c/ OCR", 12),
    ("words_total", "Palavras (PDF Completo)", 18),
    ("words_analytical", "Palavras (Corpus Analítico)", 22),
    ("confidence", "Grau de Confiança", 14),
    ("observations", "Observações", 50),
]


def export_to_xlsx(results: List[Dict], output_path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Contagem de Palavras"

    all_terms = []
    seen = set()
    for r in results:
        for label in r.get("term_results", {}).keys():
            if label not in seen:
                all_terms.append(label)
                seen.add(label)

    columns = list(BASE_COLUMNS)
    for term_label in all_terms:
        columns.append((f"_term_{term_label}_total", f"{term_label}\n(PDF)", 14))
        columns.append((f"_term_{term_label}_analytical", f"{term_label}\n(Corpus)", 14))

    for col_idx, (key, label, width) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        if key.startswith("_term_"):
            cell.fill = TERM_HEADER_FILL
        else:
            cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 40
    ws.freeze_panes = "C2"

    for row_idx, result in enumerate(results, start=2):
        enriched = {"doc_id": row_idx - 1, **result}
        for label, term_data in result.get("term_results", {}).items():
            enriched[f"_term_{label}_total"] = term_data["total"]
            enriched[f"_term_{label}_analytical"] = term_data["analytical"]

        for col_idx, (key, _label, _width) in enumerate(columns, start=1):
            value = enriched.get(key, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = THIN_BORDER
            if row_idx % 2 == 0:
                cell.fill = ALT_ROW_FILL

    ws2 = wb.create_sheet("Páginas Excluídas")
    headers2 = ["Nº Doc.", "Arquivo", "Página", "Motivo da Exclusão", "Palavras na Página"]
    for col_idx, label in enumerate(headers2, start=1):
        cell = ws2.cell(row=1, column=col_idx, value=label)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
    ws2.column_dimensions["A"].width = 8
    ws2.column_dimensions["B"].width = 35
    ws2.column_dimensions["C"].width = 10
    ws2.column_dimensions["D"].width = 40
    ws2.column_dimensions["E"].width = 20
    ws2.row_dimensions[1].height = 28
    ws2.freeze_panes = "A2"

    detail_row = 2
    for doc_idx, result in enumerate(results, start=1):
        for page in result.get("excluded_pages", []):
            ws2.cell(row=detail_row, column=1, value=doc_idx)
            ws2.cell(row=detail_row, column=2, value=result["filename"])
            ws2.cell(row=detail_row, column=3, value=page["page_number"])
            ws2.cell(row=detail_row, column=4, value=page["exclusion_reason"])
            ws2.cell(row=detail_row, column=5, value=page["word_count"])
            for col in range(1, 6):
                ws2.cell(row=detail_row, column=col).border = THIN_BORDER
                if detail_row % 2 == 0:
                    ws2.cell(row=detail_row, column=col).fill = ALT_ROW_FILL
            detail_row += 1

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
