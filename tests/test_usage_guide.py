"""The embedded guide serves both the main tab and the F1 dialog."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QTextBrowser, QWidget

from src.gui.help_dialog import HelpDialog, create_help_widget


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


def test_usage_widget_can_be_embedded_and_covers_the_complete_workflow(app):
    parent = QWidget()
    browser = create_help_widget(parent)
    assert isinstance(browser, QTextBrowser)
    assert browser.parent() is parent
    text = browser.toPlainText()
    for topic in (
        "PDFs", "Legislativo", "Séries PET", "ementa", "indexação",
        "AND", "OR", "NOT", "PLS", "PLC", "Pendentes",
        "KWIC", "Sentimento", "Flesch", "TTR", "Guiraud",
        "pontos percentuais", "L-curtose", "0,1226", "CURT",
    ):
        assert topic in text, topic
    parent.close()


def test_guide_explains_unavailable_statistics_and_denominator_limits(app):
    browser = create_help_widget()
    text = browser.toPlainText()
    for instruction in (
        "menos de quatro", "base zero", "anos consecutivos",
        "20 mudanças", "não confirma", "matérias atualmente em tramitação",
        "restaurar", "cobertura da taxonomia",
    ):
        assert instruction in text, instruction
    browser.close()


def test_f1_dialog_reuses_the_same_guide(app):
    dialog = HelpDialog()
    embedded = create_help_widget()
    browsers = dialog.findChildren(QTextBrowser)
    assert len(browsers) == 1
    assert browsers[0].toPlainText() == embedded.toPlainText()
    dialog.close()
    embedded.close()
