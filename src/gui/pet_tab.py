"""Temporal series editor and descriptive PET statistics."""

import csv
import hashlib
import io
import math
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from src.core.exporter import ExcelExportError
from src.core.legislative import preview_csv
from src.core.pet_statistics import analyze_series
from src.core.research_exporter import export_pet_analysis

MAX_SERIES_BYTES = 10 * 1024 * 1024
MAX_SERIES_ROWS = 10000


def _point(year, value, row):
    try:
        parsed_year = int(year.strip())
        parsed_value = float(value.strip().replace(",", "."))
        if not math.isfinite(parsed_value):
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Linha {row}: informe ano inteiro e valor numérico finito.") from exc
    return parsed_year, parsed_value


def parse_series_text(text):
    """Parse explicit year;value or year-tab-value rows without guessing a header."""
    if len(text) > MAX_SERIES_BYTES:
        raise ValueError("Série muito grande. Limite: 10 MB.")
    points = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        cells = line.split(";") if ";" in line else line.split("\t")
        if len(cells) != 2:
            raise ValueError(f"Linha {number}: use ano;valor, por exemplo 2020;1,5.")
        points.append(_point(*cells, number))
        if len(points) > MAX_SERIES_ROWS:
            raise ValueError("Série muito grande. Limite: 10.000 linhas.")
    if not points:
        raise ValueError("Informe ao menos um par ano;valor.")
    return points


def _fill_table(table, rows):
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            text = "Não disponível" if value is None else str(value)
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, column, item)
    table.resizeColumnsToContents()


def _source_bytes(path):
    source = Path(path)
    before = source.stat()
    if before.st_size > MAX_SERIES_BYTES:
        raise ValueError("CSV de série muito grande. Limite: 10 MB.")
    content = source.read_bytes()
    after = source.stat()
    def fingerprint(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns
    if fingerprint(before) != fingerprint(after):
        raise ValueError("CSV alterado durante a leitura. Importe o arquivo novamente.")
    if len(content) > MAX_SERIES_BYTES:
        raise ValueError("CSV de série muito grande. Limite: 10 MB.")
    return content


class SeriesCsvDialog(QDialog):
    """Select explicit CSV columns before importing a short annual series."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        if Path(path).stat().st_size > MAX_SERIES_BYTES:
            raise ValueError("CSV de série muito grande. Limite: 10 MB.")
        self.setWindowTitle("Importar série CSV")
        self.resize(760, 430)
        layout = QVBoxLayout(self)
        filename = QLabel(Path(path).name)
        filename.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(filename)
        form = QFormLayout()
        self.encoding_combo = QComboBox()
        for label, value in [("Automática", "auto"), ("UTF-8", "utf-8-sig"), ("Windows-1252", "cp1252")]:
            self.encoding_combo.addItem(label, value)
        self.delimiter_combo = QComboBox()
        for label, value in [("Automático", "auto"), ("Ponto e vírgula (;)", ";"), ("Vírgula (,)", ","), ("Tabulação", "\t")]:
            self.delimiter_combo.addItem(label, value)
        self.year_combo, self.value_combo = QComboBox(), QComboBox()
        form.addRow("Codificação", self.encoding_combo)
        form.addRow("Separador", self.delimiter_combo)
        form.addRow("Coluna do ano", self.year_combo)
        form.addRow("Coluna do valor", self.value_combo)
        layout.addLayout(form)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.preview_table)
        self.preview_error = QLabel()
        self.preview_error.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_error.setWordWrap(True)
        layout.addWidget(self.preview_error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.preview = None
        self._change_format()
        self.encoding_combo.currentIndexChanged.connect(self._change_format)
        self.delimiter_combo.currentIndexChanged.connect(self._change_format)

    def _refresh_preview(self):
        self.preview = preview_csv(self.path, encoding=self.encoding_combo.currentData(),
                                   delimiter=self.delimiter_combo.currentData())
        headers = self.preview["headers"]
        previous_year, previous_value = self.year_combo.currentText(), self.value_combo.currentText()
        for combo in (self.year_combo, self.value_combo):
            combo.clear()
            combo.addItems(headers)
        year = next((h for h in headers if h.lower() in {"ano", "year"}), headers[0])
        value = next((h for h in headers if h.lower() in {"valor", "value", "atencao", "atenção", "attention_pct"}), headers[min(1, len(headers) - 1)])
        self.year_combo.setCurrentText(previous_year if previous_year in headers else year)
        self.value_combo.setCurrentText(previous_value if previous_value in headers else value)
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        _fill_table(self.preview_table, [[row.get(h, "") for h in headers] for row in self.preview["rows"]])
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _change_format(self):
        try:
            self._refresh_preview()
            self.preview_error.clear()
        except (OSError, UnicodeError, ValueError, csv.Error) as exc:
            self.preview = None
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.preview_error.setText(f"Confira codificação e separador. {exc}")

    def read_points(self):
        if self.preview is None:
            raise ValueError(self.preview_error.text())
        year_column, value_column = self.year_combo.currentText(), self.value_combo.currentText()
        if year_column == value_column:
            raise ValueError("Selecione colunas diferentes para ano e valor.")
        parameters = {"source_file": self.path, "year_column": year_column,
                      "value_column": value_column, "encoding": self.preview["encoding"],
                      "delimiter": self.preview["delimiter"]}
        content = _source_bytes(self.path)
        parameters["source_sha256"] = hashlib.sha256(content).hexdigest()
        with io.StringIO(content.decode(parameters["encoding"]), newline="") as source:
            reader = csv.DictReader(source, delimiter=parameters["delimiter"], strict=True)
            if reader.fieldnames != self.preview["headers"]:
                raise ValueError("Cabeçalho CSV mudou desde a prévia. Importe o arquivo novamente.")
            points = []
            for row_number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Linha {row_number}: quantidade de campos diferente do cabeçalho.")
                points.append(_point(row[year_column], row[value_column], row_number))
                if len(points) > MAX_SERIES_ROWS:
                    raise ValueError("Série muito grande. Limite: 10.000 linhas.")
        if not points:
            raise ValueError("CSV não contém valores da série.")
        return points, parameters


class PetTab(QWidget):
    """Import or enter annual attention levels, inspect changes and export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis = None
        self.import_parameters = {}
        layout = QVBoxLayout(self)
        intro = QLabel("Informe níveis anuais de uma mesma medida. Escolha diferença ou variação relativa e confira as transições antes de interpretar as estatísticas.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.label_input = QLineEdit("Série de atenção")
        self.units_combo = QComboBox()
        self.units_combo.addItems(["Percentual (%)", "Contagem", "Outra unidade"])
        self.method_combo = QComboBox()
        self.method_combo.addItem("Diferença anual (pontos percentuais para séries em %)", "difference")
        self.method_combo.addItem("Variação relativa anual (%)", "relative")
        form.addRow("Nome da série", self.label_input)
        form.addRow("Unidade dos níveis", self.units_combo)
        form.addRow("Medida de mudança", self.method_combo)
        layout.addLayout(form)
        self.series_input = QPlainTextEdit()
        self.series_input.setPlaceholderText("Um ano;valor por linha, sem cabeçalho.\n2020;1,5\n2021;2,0\n2022;2,4")
        self.series_input.setMaximumHeight(145)
        self.series_input.setAccessibleName("Série anual: ano e valor separados por ponto e vírgula")
        layout.addWidget(self.series_input)
        controls = QHBoxLayout()
        self.btn_import = QPushButton("Importar série CSV…")
        self.btn_calculate = QPushButton("Calcular mudanças e estatísticas")
        self.btn_calculate.setObjectName("PrimaryButton")
        self.btn_export = QPushButton("Exportar XLSX")
        self.btn_export.setEnabled(False)
        for button in (self.btn_import, self.btn_calculate, self.btn_export):
            controls.addWidget(button)
        layout.addLayout(controls)
        self.change_unit = QLabel()
        layout.addWidget(self.change_unit)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.levels_table = self._table(["Ano", "Nível"])
        self.changes_table = self._table(["Ano anterior", "Ano", "Mudança"])
        splitter.addWidget(self.levels_table)
        splitter.addWidget(self.changes_table)
        layout.addWidget(splitter, 1)
        self.statistics = QLabel("Calcule a série para ver as estatísticas.")
        self.statistics.setTextFormat(Qt.TextFormat.PlainText)
        self.statistics.setWordWrap(True)
        self.warnings = QLabel()
        self.warnings.setTextFormat(Qt.TextFormat.PlainText)
        self.warnings.setWordWrap(True)
        self.warnings.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        warnings_area = QScrollArea()
        warnings_area.setWidgetResizable(True)
        warnings_area.setMaximumHeight(130)
        warnings_area.setWidget(self.warnings)
        layout.addWidget(self.statistics)
        layout.addWidget(warnings_area)
        self.btn_import.clicked.connect(self.import_csv)
        self.btn_calculate.clicked.connect(self.calculate)
        self.btn_export.clicked.connect(self.export_results)
        self.series_input.textChanged.connect(self._edited_series)
        self.label_input.textChanged.connect(self._invalidate)
        self.units_combo.currentIndexChanged.connect(self._invalidate)
        self.method_combo.currentIndexChanged.connect(self._invalidate)
        self._invalidate()

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        return table

    def _edited_series(self):
        self.import_parameters = {}
        self._invalidate()

    def _invalidate(self):
        self.analysis = None
        self.btn_export.setEnabled(False)
        self.levels_table.setRowCount(0)
        self.changes_table.setRowCount(0)
        self.statistics.setText("Entrada alterada. Calcule para atualizar os resultados.")
        self.warnings.clear()
        if self.method_combo.currentData() == "relative":
            description = "Variação relativa (%) = 100 × (nível atual − anterior) / anterior."
        elif self.units_combo.currentText() == "Percentual (%)":
            description = "Pontos percentuais = percentual atual − percentual anterior."
        else:
            description = "Diferença na unidade dos níveis = nível atual − anterior."
        self.change_unit.setText(description)

    def set_series(self, points, label="", unit="Percentual (%)"):
        self.series_input.setPlainText("\n".join(f"{year};{value}" for year, value in points))
        if label:
            self.label_input.setText(label)
        if unit in [self.units_combo.itemText(i) for i in range(self.units_combo.count())]:
            self.units_combo.setCurrentText(unit)
        else:
            self.units_combo.setCurrentText("Outra unidade")
        self.calculate()

    def calculate(self):
        self._invalidate()
        try:
            points = parse_series_text(self.series_input.toPlainText())
            if self.units_combo.currentText() == "Percentual (%)" and any(value > 100 for _, value in points):
                raise ValueError("Níveis percentuais de atenção devem estar entre 0 e 100. Confira a unidade selecionada.")
            analysis = analyze_series(points, method=self.method_combo.currentData())
        except (ValueError, OverflowError) as exc:
            QMessageBox.warning(self, "Série inválida", str(exc))
            return
        self.analysis = analysis
        _fill_table(self.levels_table, [[row["year"], row["value"]] for row in analysis["levels"]])
        _fill_table(self.changes_table, [[row["previous_year"], row["year"], row["change"]] for row in analysis["changes"]])
        measures = [("Curtose (excesso corrigido; normal = 0)", "excess_kurtosis"),
                    ("Curtose (excesso + 3; normal = 3)", "pearson_kurtosis"),
                    ("L-curtose (normal ≈ 0,1226)", "l_kurtosis")]
        text = [f"Níveis anuais: {analysis['n_levels']} | Mudanças anuais válidas: {analysis['n_changes']}"]
        for label, key in measures:
            value = analysis[key]
            text.append(f"{label}: {'Não disponível' if value is None else format(value, '.6g')}")
        self.statistics.setText("\n".join(text))
        warnings = list(analysis["warnings"])
        warnings.append("Medidas descritivas: valores elevados não confirmam a PET nem explicam a causa das mudanças.")
        self.warnings.setText("\n".join(warnings))
        self.btn_export.setEnabled(True)

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar série anual", "", "CSV (*.csv);;Todos os arquivos (*)")
        if not path:
            return
        try:
            dialog = SeriesCsvDialog(path, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            points, parameters = dialog.read_points()
            self.set_series(points, Path(path).stem, self.units_combo.currentText())
            self.import_parameters = parameters
        except (OSError, UnicodeError, ValueError, csv.Error) as exc:
            QMessageBox.warning(self, "Não foi possível importar a série", str(exc))

    def export_results(self):
        if self.analysis is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar análise PET", "analise_pet.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".xlsx"
        try:
            export_pet_analysis(self.analysis, path, label=self.label_input.text(),
                                unit=self.units_combo.currentText(), parameters=self.import_parameters)
        except (OSError, ExcelExportError) as exc:
            QMessageBox.warning(self, "Não foi possível exportar", str(exc))
            return
        QMessageBox.information(self, "Exportação concluída", f"Análise salva em:\n{path}")
