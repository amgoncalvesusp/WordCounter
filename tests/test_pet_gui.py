"""Practical desktop journeys for temporal PET analysis."""

import os
import hashlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.gui.pet_tab import PetTab, SeriesCsvDialog, parse_series_text


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def tab(app):
    widget = PetTab()
    yield widget
    widget.close()


def test_parse_manual_series_accepts_decimal_comma_and_tabs():
    assert parse_series_text("2020;1,5\n\n2021\t2.5") == [(2020, 1.5), (2021, 2.5)]


@pytest.mark.parametrize("text", ["", "2020", "ano;valor", "2020;NaN", "2020;inf"])
def test_parse_manual_series_reports_invalid_rows(text):
    with pytest.raises(ValueError):
        parse_series_text(text)


def test_set_series_calculates_changes_and_statistics(tab):
    tab.set_series([(2020, 0), (2021, 1), (2022, 3), (2023, 6), (2024, 10), (2025, 15)], "Câmara")
    assert tab.analysis["n_changes"] == 5
    assert tab.analysis["excess_kurtosis"] == pytest.approx(-1.2)
    assert tab.levels_table.rowCount() == 6
    assert tab.changes_table.rowCount() == 5
    assert tab.label_input.text() == "Câmara"
    assert tab.btn_export.isEnabled()
    assert "Pontos percentuais" in tab.change_unit.text()
    assert not tab.levels_table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable


def test_input_or_method_edit_invalidates_export(tab):
    tab.set_series([(2020, 1), (2021, 2)])
    tab.series_input.setPlainText("2020;4\n2021;6")
    assert tab.analysis is None
    assert not tab.btn_export.isEnabled()
    tab.calculate()
    assert tab.analysis is not None
    tab.method_combo.setCurrentIndex(1)
    assert tab.analysis is None
    assert "Variação relativa" in tab.change_unit.text()


def test_relative_zero_and_gap_remain_unavailable(tab):
    tab.set_series([(2020, 0), (2021, 1), (2023, 4)])
    tab.method_combo.setCurrentIndex(1)
    tab.calculate()
    assert tab.analysis["n_changes"] == 0
    assert all(row["change"] is None for row in tab.analysis["changes"])
    assert tab.analysis["warnings"]
    assert "Não disponível" in tab.statistics.text()


def test_invalid_data_keeps_export_disabled_and_reports_error(tab, monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    tab.series_input.setPlainText("2020;1\n2020;2")
    tab.calculate()
    assert messages
    assert tab.analysis is None
    assert not tab.btn_export.isEnabled()


def test_csv_mapping_preserves_selected_columns_decimal_comma_and_parameters(app, tmp_path):
    path = tmp_path / "serie.csv"
    path.write_text("ano;atenção;ignorar\n2020;1,5;9\n2021;2,5;10\n", encoding="utf-8-sig")
    dialog = SeriesCsvDialog(str(path))
    dialog.year_combo.setCurrentText("ano")
    dialog.value_combo.setCurrentText("atenção")
    points, parameters = dialog.read_points()
    assert points == [(2020, 1.5), (2021, 2.5)]
    assert parameters["year_column"] == "ano"
    assert parameters["value_column"] == "atenção"
    assert parameters["source_file"] == str(path)
    dialog.close()


def test_csv_mapping_rejects_malformed_rows(app, tmp_path):
    path = tmp_path / "serie.csv"
    path.write_text("ano;valor\n2020;1;extra\n", encoding="utf-8")
    dialog = SeriesCsvDialog(str(path))
    with pytest.raises(ValueError):
        dialog.read_points()
    dialog.close()


def test_export_uses_current_labels_units_and_import_parameters(tab, tmp_path, monkeypatch):
    from src.gui import pet_tab

    calls = []
    path = str(tmp_path / "pet.xlsx")
    monkeypatch.setattr(pet_tab.QFileDialog, "getSaveFileName", lambda *args: (path, ""))
    monkeypatch.setattr(pet_tab, "export_pet_analysis", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    tab.set_series([(2020, 1), (2021, 3)], "Mensagens", "Contagem")
    tab.export_results()
    assert calls[0][0][1] == path
    assert calls[0][1]["label"] == "Mensagens"
    assert calls[0][1]["unit"] == "Contagem"
    assert "parameters" in calls[0][1]


def test_import_calculate_export_round_trip(tab, tmp_path, monkeypatch):
    from openpyxl import load_workbook
    from src.gui import pet_tab

    source = tmp_path / "mensagens.csv"
    source.write_text("ano;valor\n2020;1,5\n2021;2,5\n", encoding="utf-8-sig")
    destination = tmp_path / "pet.xlsx"
    monkeypatch.setattr(pet_tab.QFileDialog, "getOpenFileName", lambda *args: (str(source), ""))
    monkeypatch.setattr(pet_tab.SeriesCsvDialog, "exec", lambda self: pet_tab.QDialog.DialogCode.Accepted)
    monkeypatch.setattr(pet_tab.QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    tab.import_csv()
    assert tab.analysis["changes"][0]["change"] == 1
    assert tab.import_parameters["source_file"] == str(source)
    tab.export_results()
    workbook = load_workbook(destination)
    assert workbook["Série"].cell(2, 2).value == 1.5
    assert workbook["Mudanças"].cell(2, 5).value == 1
    parameters = {row[0]: row[2] for row in workbook["Parâmetros"].iter_rows(min_row=2, values_only=True)}
    assert parameters["source_file"] == str(source)
    assert parameters["Unidade"] == "Percentual (%)"
    workbook.close()


def test_csv_changed_after_preview_is_rejected(app, tmp_path):
    source = tmp_path / "serie.csv"
    source.write_text("ano;valor\n2020;1\n", encoding="utf-8")
    dialog = SeriesCsvDialog(str(source))
    source.write_text("year;value\n2020;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Cabeçalho"):
        dialog.read_points()
    dialog.close()


def test_percentage_levels_above_100_are_rejected_but_counts_allowed(tab, monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    tab.series_input.setPlainText("2020;100\n2021;100,1")
    tab.calculate()
    assert tab.analysis is None
    assert not tab.btn_export.isEnabled()
    assert "100" in messages[-1]
    tab.units_combo.setCurrentText("Contagem")
    tab.calculate()
    assert tab.analysis["n_changes"] == 1


def test_export_adds_missing_xlsx_extension(tab, tmp_path, monkeypatch):
    from src.gui import pet_tab

    calls = []
    destination = str(tmp_path / "analise")
    monkeypatch.setattr(pet_tab.QFileDialog, "getSaveFileName", lambda *args: (destination, ""))
    monkeypatch.setattr(pet_tab, "export_pet_analysis", lambda *args, **kwargs: calls.append(args[1]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    tab.set_series([(2020, 1), (2021, 2)])
    tab.export_results()
    assert calls == [destination + ".xlsx"]


def test_csv_provenance_hash_matches_exact_source_bytes(app, tmp_path):
    source = tmp_path / "serie.csv"
    content = "ano;valor\n2020;1,5\n2021;2,5\n".encode("utf-8-sig")
    source.write_bytes(content)
    dialog = SeriesCsvDialog(str(source))
    points, parameters = dialog.read_points()
    assert points == [(2020, 1.5), (2021, 2.5)]
    assert parameters["source_sha256"] == hashlib.sha256(content).hexdigest()
    dialog.close()


def test_csv_modified_during_read_is_rejected(app, tmp_path, monkeypatch):
    from pathlib import Path

    source = tmp_path / "serie.csv"
    source.write_text("ano;valor\n2020;1\n", encoding="utf-8")
    dialog = SeriesCsvDialog(str(source))
    original = Path.read_bytes

    def changed(path):
        content = original(path)
        path.write_text("ano;valor\n2020;1000\n", encoding="utf-8")
        return content

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="alterado"):
        dialog.read_points()
    dialog.close()


def test_many_gap_warnings_fit_in_scrollable_area(tab, app):
    tab.set_series([(1800 + 2 * index, index) for index in range(80)])
    tab.resize(1000, 850)
    tab.show()
    app.processEvents()
    assert len(tab.analysis["warnings"]) >= 79
    assert tab.minimumSizeHint().height() < 900
    assert tab.warnings.parentWidget().parentWidget().height() <= 130
