"""Round-trip and failure checks for the research workbooks."""

from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from src.core.exporter import ExcelExportError
from src.core.research_exporter import (
    export_legislative_analysis,
    export_pet_analysis,
)

pytestmark = pytest.mark.unit


def legislative_result(text="Mudanças climáticas", note="Revisado"):
    proposition = SimpleNamespace(
        identifier="=001", house="Câmara", year=2020, kind="PL",
        texts=(("ementa", text),), source_file="origem.csv",
    )
    return SimpleNamespace(
        proposition=proposition, automatic=True, review=False, climatic=False,
        note=note, evidence=(SimpleNamespace(
            field="ementa", term="climátic*", snippet="Mudanças climáticas"
        ),),
    )


def summary_row():
    return {
        "house": "Câmara", "year": 2020, "total": 1, "climatic": 0,
        "not_identified": 1, "pending": 0, "attention_pct": 0.0,
        "identified_pct": 0.0,
    }


def pet_analysis():
    return {
        "method": "difference", "levels": [{"year": 2020, "value": 1.5}],
        "changes": [{"year": 2022, "previous_year": 2020,
                     "previous_value": 1.5, "value": 2.0, "change": None}],
        "n_levels": 1, "n_changes": 0, "pearson_kurtosis": None,
        "excess_kurtosis": None, "l_kurtosis": None,
        "warnings": ["Lacuna anual: mudança não calculada."],
    }


def test_legislative_round_trip_preserves_audit_and_safe_text(tmp_path):
    path = tmp_path / "analise.xlsx"
    export_legislative_analysis(
        [legislative_result("=HYPERLINK(\"a\")\x00 clima")], [summary_row()],
        path, {"regra": "climátic*", "mapeamento": {"texto": ["ementa"]}},
    )
    wb = load_workbook(path)
    assert wb.sheetnames == [
        "Proposições", "Textos", "Evidências", "Resumo Anual", "Parâmetros"
    ]
    assert wb["Proposições"]["A2"].value == "Câmara"
    assert wb["Proposições"]["B2"].value == "=001"
    assert wb["Proposições"]["B2"].data_type == "s"
    assert wb["Proposições"]["E2"].value == "Sim"
    assert wb["Proposições"]["F2"].value == "Não"
    assert wb["Proposições"]["G2"].value == "Não"
    assert wb["Textos"]["E2"].value == '=HYPERLINK("a")  clima'
    assert wb["Textos"]["E2"].data_type == "s"
    assert wb["Evidências"]["D2"].value == "climátic*"
    assert wb["Resumo Anual"]["G2"].value == 0
    assert wb["Parâmetros"]["C2"].value == "climátic*"
    assert wb["Proposições"].freeze_panes == "A2"
    wb.close()


def test_full_text_and_long_parameters_split_without_loss(tmp_path):
    text = "ação " * 15000
    parameter = "=regra " * 10000
    path = tmp_path / "completo.xlsx"
    export_legislative_analysis(
        [legislative_result(text)], [summary_row()], path, {"regra": parameter}
    )
    wb = load_workbook(path)
    chunks = list(wb["Textos"].values)[1:]
    assert "".join(row[4] for row in chunks) == text
    assert [row[3] for row in chunks] == list(range(1, len(chunks) + 1))
    parameter_chunks = list(wb["Parâmetros"].values)[1:]
    assert "".join(row[2] for row in parameter_chunks) == parameter
    assert all(len(row[4]) <= 32767 for row in chunks)
    assert wb["Parâmetros"]["C2"].data_type == "s"
    wb.close()


def test_pet_round_trip_keeps_missing_transitions_and_method(tmp_path):
    path = tmp_path / "pet.xlsx"
    export_pet_analysis(pet_analysis(), path, "Mensagens", "Percentual (%)")
    wb = load_workbook(path)
    assert wb.sheetnames == ["Série", "Mudanças", "Estatísticas", "Parâmetros"]
    assert wb["Série"]["B2"].value == 1.5
    assert wb["Mudanças"]["E2"].value is None
    assert wb["Mudanças"]["F2"].value == "Anos não consecutivos"
    statistics = dict((row[0], row[1]) for row in list(wb["Estatísticas"].values)[1:])
    assert statistics["Mudanças válidas"] == 0
    assert statistics["Método de mudança"] == "Diferença absoluta"
    assert statistics["Referência normal — Pearson"] == 3
    assert statistics["Referência normal — excesso"] == 0
    assert statistics["Referência normal — L-curtose"] == pytest.approx(0.1226)
    assert "Lacuna" in statistics["Aviso 1"]
    parameters = dict((row[0], row[2]) for row in list(wb["Parâmetros"].values)[1:])
    assert parameters["Série"] == "Mensagens"
    assert parameters["Unidade"] == "Percentual (%)"
    wb.close()


def test_export_rejects_unrepresentable_nontext_field_without_overwriting(tmp_path):
    path = tmp_path / "original.xlsx"
    path.write_bytes(b"original preservado")
    with pytest.raises(ExcelExportError, match="32767"):
        export_legislative_analysis(
            [legislative_result(note="x" * 32768)], [summary_row()], path
        )
    assert path.read_bytes() == b"original preservado"


def test_failed_save_keeps_old_workbook_and_removes_temporary(tmp_path, monkeypatch):
    from src.core import research_exporter

    path = tmp_path / "original.xlsx"
    path.write_bytes(b"original preservado")

    def fail_save(self, filename):
        raise PermissionError("arquivo ocupado")

    monkeypatch.setattr(research_exporter.Workbook, "save", fail_save)
    with pytest.raises(ExcelExportError, match="ocupado"):
        export_pet_analysis(pet_analysis(), path)
    assert path.read_bytes() == b"original preservado"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["original.xlsx"]


def test_failed_replace_keeps_destination_and_cleans_temporary(tmp_path, monkeypatch):
    from src.core import research_exporter

    path = tmp_path / "original.xlsx"
    path.write_bytes(b"original preservado")

    def fail_replace(source, destination):
        raise PermissionError("destino aberto no Excel")

    monkeypatch.setattr(research_exporter.os, "replace", fail_replace)
    with pytest.raises(ExcelExportError, match="aberto no Excel"):
        export_pet_analysis(pet_analysis(), path)
    assert path.read_bytes() == b"original preservado"
    assert [item.name for item in tmp_path.iterdir()] == ["original.xlsx"]


def test_excel_error_literal_is_preserved_as_text(tmp_path):
    path = tmp_path / "literal.xlsx"
    export_legislative_analysis(
        [legislative_result("#N/A")], [summary_row()], path
    )
    wb = load_workbook(path)
    assert wb["Textos"]["E2"].data_type == "s"
    wb.close()


def test_row_limit_is_checked_before_unsupported_row_is_written(tmp_path, monkeypatch):
    from src.core import research_exporter

    monkeypatch.setattr(research_exporter, "MAX_ROWS", 2)
    analysis = {**pet_analysis(), "levels": [
        {"year": 2020, "value": 1}, {"year": 2021, "value": 2}
    ]}
    with pytest.raises(ExcelExportError, match="linhas"):
        export_pet_analysis(analysis, tmp_path / "limite.xlsx")


def test_empty_legislative_workbook_still_has_headers(tmp_path):
    path = tmp_path / "vazio.xlsx"
    export_legislative_analysis([], [], path)
    wb = load_workbook(path)
    assert wb["Proposições"].max_row == 1
    assert wb["Resumo Anual"].max_row == 1
    wb.close()


def test_pet_export_explains_zero_baseline_and_nonfinite_exclusion(tmp_path):
    analysis = {**pet_analysis(), "method": "relative", "changes": [
        {"previous_year": 2020, "year": 2021, "previous_value": 0,
         "value": 1, "change": None},
        {"previous_year": 2021, "year": 2022, "previous_value": 1,
         "value": 2, "change": None},
        {"previous_year": 2022, "year": 2023, "previous_value": 2,
         "value": 3, "change": 50},
    ]}
    path = tmp_path / "motivos.xlsx"
    export_pet_analysis(analysis, path)
    wb = load_workbook(path)
    assert wb["Mudanças"]["F2"].value == "Base anterior zero"
    assert wb["Mudanças"]["F3"].value == "Variação não finita"
    assert wb["Mudanças"]["F4"].value is None
    wb.close()


@pytest.mark.integration
def test_csv_classification_summary_pet_and_workbook_pipeline(tmp_path):
    from src.core.legislative import (
        CsvMapping, annual_summary, classify_propositions, load_propositions,
    )
    from src.core.pet_statistics import analyze_series

    source = tmp_path / "origem.csv"
    source.write_text(
        "id;ano;tipo;ementa\n1;2020;PL;mudança do clima\n"
        "1;2020;PL;mudança do clima\n2;2020;PL;educação\n"
        "3;2021;PL;clima\n", encoding="utf-8",
    )
    loaded = load_propositions(source, CsvMapping(
        "id", "ano", "tipo", ("ementa",), "Câmara"
    ))
    classified = classify_propositions(loaded.propositions, "clima")
    summary = annual_summary(classified)
    assert loaded.duplicate_count == 1
    analysis = analyze_series([(row["year"], row["attention_pct"]) for row in summary])
    path = tmp_path / "legislativo.xlsx"
    export_legislative_analysis(classified, summary, path, {"regra": "clima"})
    wb = load_workbook(path)
    assert wb["Resumo Anual"]["G2"].value == 50
    assert wb["Resumo Anual"]["G3"].value == 100
    wb.close()
    path = tmp_path / "pet.xlsx"
    export_pet_analysis(analysis, path, "Câmara", "Percentual (%)")
    wb = load_workbook(path)
    assert wb["Mudanças"]["E2"].value == 50
    wb.close()
