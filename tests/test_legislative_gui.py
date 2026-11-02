"""Desktop journeys for CSV classification, review and the main tabs."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.core.legislative import CsvMapping
from src.gui.legislative_tab import CsvMappingDialog, LegislativeTab
from src.gui.legislative_worker import ImportSpec, LegislativeWorker


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def import_spec(tmp_path):
    path = tmp_path / "propostas.csv"
    path.write_text(
        'id;dataApresentacao;siglaTipo;ementa;keywords\n'
        '001;2020-01-01;PL;Mudanças climáticas;carbono\n'
        '001;2020-01-01;PL;Mudanças climáticas;carbono\n'
        '002;2020-01-02;PL;Educação;escolas\n'
        '003;2021-01-01;PL;;\n', encoding="utf-8-sig",
    )
    mapping = CsvMapping("id", "dataApresentacao", "siglaTipo",
                         ("ementa", "keywords"), "Câmara", True)
    return ImportSpec(str(path), mapping, "utf-8-sig", ";")


def test_mapping_suggests_actual_camara_columns(qt_app, import_spec):
    dialog = CsvMappingDialog(import_spec.path)
    spec = dialog.import_spec()
    assert spec.mapping.id_column == "id"
    assert spec.mapping.year_column == "dataApresentacao"
    assert spec.mapping.year_is_date
    assert set(spec.mapping.text_columns) == {"ementa", "keywords"}
    dialog.close()


def test_worker_classifies_deduplicates_and_records_provenance(qt_app, import_spec):
    worker = LegislativeWorker((import_spec,), "mudanç* climátic*")
    completed, errors = [], []
    worker.completed.connect(completed.append)
    worker.error.connect(errors.append)
    worker.run()
    assert not errors
    payload = completed[0]
    assert len(payload["results"]) == 3
    assert payload["duplicates"] == 1
    assert len(payload["sources"][0]["sha256"]) == 64


def test_review_recalculates_index_and_keeps_automatic(qt_app, import_spec, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *a: None)
    tab = LegislativeTab()
    tab.add_import(import_spec)
    worker = LegislativeWorker((import_spec,), "mudanç* climátic*")
    worker.completed.connect(tab.accept_results)
    worker.run()
    assert tab.summary[0]["attention_pct"] == 50
    assert tab.summary[1]["attention_pct"] is None
    tab.results_table.selectRow(1)
    tab.review_selected(True)
    assert tab.results[1].automatic is False
    assert tab.results[1].climatic is True
    assert tab.summary[0]["attention_pct"] == 100
    tab.review_selected(None)
    assert tab.summary[0]["attention_pct"] == 50
    tab.rule_input.setPlainText("carbono")
    assert not tab.export_button.isEnabled()
    tab.close()


def test_send_to_pet_preserves_house_and_refuses_pending(qt_app, import_spec, monkeypatch):
    notices = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: notices.append(a))
    tab = LegislativeTab()
    tab.add_import(import_spec)
    worker = LegislativeWorker((import_spec,), "climátic*")
    worker.completed.connect(tab.accept_results)
    worker.run()
    sent = []
    tab.series_requested.connect(lambda *a: sent.append(a))
    tab.send_to_pet()
    assert notices and not sent
    tab.end_year.setValue(2020)
    tab.send_to_pet()
    assert sent[0][0] == [(2020, 50.0)]
    assert "Câmara" in sent[0][1]
    tab.close()


def test_main_has_workflow_and_usage_tabs(qt_app, monkeypatch):
    from src.gui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "_check_tesseract", lambda self: None)
    window = MainWindow()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        "PDFs", "Legislativo", "Séries PET", "Como usar"
    ]
    window.show_help()
    assert window.tabs.currentWidget() is window.help_tab
    window.close()


def test_export_shortcut_ignores_invalid_filters(qt_app, import_spec, monkeypatch):
    from src.gui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "_check_tesseract", lambda self: None)
    window = MainWindow()
    tab = window.legislative_tab
    tab.add_import(import_spec)
    worker = LegislativeWorker((import_spec,), "climátic*")
    worker.completed.connect(tab.accept_results)
    worker.run()
    window.tabs.setCurrentWidget(tab)
    tab.start_year.setValue(2022)
    tab.end_year.setValue(2020)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: pytest.fail("Invalid filters opened save dialog"))
    window.export_current()
    window.close()


def test_legislative_transfer_preserves_rule_source_and_reviews(qt_app, import_spec, monkeypatch):
    from src.gui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "_check_tesseract", lambda self: None)
    window = MainWindow()
    tab = window.legislative_tab
    tab.add_import(import_spec)
    worker = LegislativeWorker((import_spec,), "climátic*")
    worker.completed.connect(tab.accept_results)
    worker.run()
    tab.end_year.setValue(2020)
    tab.results_table.selectRow(1)
    tab.review_selected(True)
    tab.send_to_pet()
    metadata = window.pet_tab.import_parameters
    assert metadata["origin"] == "Legislativo"
    assert metadata["expression"] == "climátic*"
    assert metadata["sources"][0]["sha256"]
    assert metadata["filters"]["end_year"] == 2020
    assert metadata["reviews"][0]["identifier"] == "002"
    window.close()


def test_pdf_counts_transfer_with_explicit_measure_and_year_validation(qt_app, monkeypatch):
    from src.gui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "_check_tesseract", lambda self: None)
    notices = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: notices.append(a))
    window = MainWindow()
    window.results = [
        {"filename": "2020.pdf", "year": "2020", "words_analytical": 100,
         "words_total": 200, "term_results": {"clima": {"analytical": 3}}},
        {"filename": "2021.pdf", "year": "2021", "words_analytical": 120,
         "words_total": 250, "term_results": {"clima": {"analytical": 6}}},
    ]
    window._term_labels = ["clima"]
    window._update_pdf_pet_measures()
    window.pdf_pet_metric.setCurrentIndex(2)
    window.send_pdf_to_pet()
    assert window.pet_tab.analysis["levels"] == [{"year": 2020, "value": 3.0}, {"year": 2021, "value": 6.0}]
    assert window.pet_tab.units_combo.currentText() == "Contagem"
    assert window.pet_tab.import_parameters["origin"] == "PDFs"
    window.results = [{**r, "year": "2020"} for r in window.results]
    window.send_pdf_to_pet()
    assert notices
    window.close()
