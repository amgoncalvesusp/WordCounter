"""Native desktop journeys through real workers, review and XLSX exports."""

import csv
import os
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from openpyxl import load_workbook
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from src.gui.legislative_tab import CsvMappingDialog
from src.gui.legislative_worker import LegislativeWorker
from src.gui.main_window import MainWindow

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    if not QFontDatabase.families() and font.is_file():
        # Windows offscreen Qt does not discover system fonts automatically.
        QFontDatabase.addApplicationFont(str(font))
    return instance


def _until(app, condition, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return
        QTest.qWait(5)
    pytest.fail("Desktop journey did not reach the expected state before timeout.")


@pytest.fixture
def window(app, monkeypatch):
    monkeypatch.setattr(MainWindow, "_check_tesseract", lambda self: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    widget = MainWindow()
    widget.resize(1280, 900)
    widget.show()
    app.processEvents()
    yield widget
    if widget.legislative_tab.is_processing():
        widget.legislative_tab.cancel_processing()
        _until(app, lambda: not widget.legislative_tab.is_processing())
    if widget.worker_thread is not None and widget.worker_thread.isRunning():
        widget.cancel_processing()
        _until(app, lambda: not widget.worker_thread.isRunning())
    widget.close()
    app.processEvents()


@pytest.fixture
def legislative_csv(tmp_path):
    path = tmp_path / "universo.csv"
    counts = [1, 2, 4, 3, 6, 4]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["id", "dataApresentacao", "siglaTipo", "ementa", "keywords"])
        for year, climatic in zip(range(2020, 2026), counts):
            for number in range(10):
                writer.writerow([
                    f"{year}-{number:02}", f"{year}-03-01", "PL",
                    "Mudanças climáticas" if number < climatic else "Política de educação",
                    "carbono" if number < climatic else "escolas",
                ])
    return path


def _import_from_button(window, monkeypatch, path):
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([str(path)], ""))
    monkeypatch.setattr(CsvMappingDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.tabs.setCurrentWidget(window.legislative_tab)
    QTest.mouseClick(window.legislative_tab.add_button, Qt.MouseButton.LeftButton)
    assert len(window.legislative_tab.specs) == 1
    assert window.legislative_tab.specs[0].mapping.year_is_date


def _screenshot(window, tmp_path, name):
    directory = Path(os.environ.get("WORDCOUNTER_SCREENSHOT_DIR", str(tmp_path / "screenshots")))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"wordcounter-{name}.png"
    assert window.grab().save(str(path))


def test_legislative_review_to_pet_and_exports(window, app, monkeypatch, legislative_csv, tmp_path):
    tab = window.legislative_tab
    _import_from_button(window, monkeypatch, legislative_csv)
    tab.source_note.setText("Universo sintético completo: dez proposições por ano, Câmara.")
    QTest.mouseClick(tab.process_button, Qt.MouseButton.LeftButton)
    _until(app, lambda: tab.worker is None and bool(tab.results))
    assert len(tab.results) == 60
    assert [row["attention_pct"] for row in tab.summary] == [10, 20, 40, 30, 60, 40]
    assert tab.summary_table.rowCount() == 6

    tab.results_table.selectRow(1)
    tab.review_note.setText("Revisão de conteúdo climático não explícito na ementa.")
    QTest.mouseClick(tab.review_buttons[0], Qt.MouseButton.LeftButton)
    assert tab.results[1].automatic is False
    assert tab.results[1].review is True
    assert tab.summary[0]["attention_pct"] == 20
    _screenshot(window, tmp_path, "legislativo")

    legislation_output = tmp_path / "legislativo.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(legislation_output), ""))
    QTest.mouseClick(tab.export_button, Qt.MouseButton.LeftButton)
    workbook = load_workbook(legislation_output)
    assert workbook["Proposições"].max_row == 61
    assert workbook["Resumo Anual"].cell(2, 7).value == 20
    workbook.close()

    QTest.mouseClick(tab.send_button, Qt.MouseButton.LeftButton)
    pet = window.pet_tab
    assert window.tabs.currentWidget() is pet
    assert pet.analysis["n_levels"] == 6
    assert pet.analysis["n_changes"] == 5
    assert pet.analysis["l_kurtosis"] is not None
    assert pet.import_parameters, "Legislative provenance must follow the derived PET series."
    assert "Câmara" in pet.label_input.text()
    _screenshot(window, tmp_path, "pet")

    pet_output = tmp_path / "pet.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(pet_output), ""))
    QTest.mouseClick(pet.btn_export, Qt.MouseButton.LeftButton)
    workbook = load_workbook(pet_output)
    assert workbook["Série"].max_row == 7
    assert workbook["Mudanças"].max_row == 6
    assert workbook["Parâmetros"].max_row > 4
    workbook.close()

    window.activateWindow()
    QTest.keyClick(window, Qt.Key.Key_F1)
    _until(app, lambda: window.tabs.currentWidget() is window.help_tab)
    assert "L-curtose" in window.help_tab.toPlainText()
    _screenshot(window, tmp_path, "como-usar")


def test_pdf_journey_still_processes_and_exports(window, app, monkeypatch, sample_pdf, tmp_path):
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([sample_pdf], ""))
    QTest.mouseClick(window.btn_add, Qt.MouseButton.LeftButton)
    assert window.pdf_files == [sample_pdf]
    window.ocr_checkbox.setChecked(False)
    window.terms_input.setPlainText("clima")
    QTest.mouseClick(window.btn_process, Qt.MouseButton.LeftButton)
    _until(app, lambda: window.btn_process.isEnabled() and bool(window.results))
    assert window.results_table.rowCount() == 1
    assert window.results[0]["words_analytical"] > 100
    assert window.results[0]["term_results"]["clima"]["analytical"] > 0
    path = tmp_path / "pdf.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    QTest.mouseClick(window.btn_export, Qt.MouseButton.LeftButton)
    workbook = load_workbook(path)
    assert "Contagem de Palavras" in workbook.sheetnames
    assert workbook["Contagem de Palavras"].max_row == 2
    workbook.close()


def test_close_requests_cancellation_without_destroying_active_worker(window, app, monkeypatch, legislative_csv):
    entered = threading.Event()

    def cancellable_source(self, spec):
        entered.set()
        deadline = time.monotonic() + 5
        while not self.isInterruptionRequested() and time.monotonic() < deadline:
            self.msleep(5)
        self._check_cancelled()
        raise AssertionError("Window did not request worker cancellation.")

    monkeypatch.setattr(LegislativeWorker, "_load_source", cancellable_source)
    _import_from_button(window, monkeypatch, legislative_csv)
    QTest.mouseClick(window.legislative_tab.process_button, Qt.MouseButton.LeftButton)
    _until(app, entered.is_set)
    assert window.legislative_tab.is_processing()
    assert window.close() is False
    assert window.isVisible()
    _until(app, lambda: window.legislative_tab.worker is None)
    assert not window.legislative_tab.results
    assert "cancelado" in window.legislative_tab.status_label.text().lower()
    assert window.close() is True
