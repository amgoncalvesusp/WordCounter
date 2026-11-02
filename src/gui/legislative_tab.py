"""Import, review and summarize legislative attention without changing PDF counts."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.core.boolean_search import compile_query
from src.core.exporter import ExcelExportError
from src.core.legislative import CsvMapping, annual_summary, preview_csv, review_proposition
from src.core.research_exporter import export_legislative_analysis
from src.core.term_search import normalize
from src.gui.legislative_worker import ImportSpec, LegislativeWorker


def _column_key(name):
    return "".join(c for c in normalize(name) if c.isalnum())


def _readonly_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    return table


def _fill_table(table, rows):
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            text = "—" if value is None else str(round(value, 6) if isinstance(value, float) else value)
            item = QTableWidgetItem(text)
            item.setToolTip(text)
            table.setItem(i, j, item)


class CsvMappingDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.setWindowTitle(f"Mapear CSV — {Path(path).name}")
        self.resize(850, 650)
        layout = QVBoxLayout(self)
        tip = QLabel("Escolha as colunas usadas. Prefira a data de apresentação ao ano da numeração.")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        form = QFormLayout()
        self.house = QComboBox()
        self.house.addItems(["Câmara", "Senado"])
        self.encoding = QComboBox()
        self.encoding.addItems(["auto", "utf-8-sig", "cp1252"])
        self.delimiter = QComboBox()
        for label, value in [("Detectar", "auto"), ("Ponto e vírgula", ";"),
                             ("Vírgula", ","), ("Tabulação", "\t")]:
            self.delimiter.addItem(label, value)
        self.id_column, self.year_column, self.type_column = QComboBox(), QComboBox(), QComboBox()
        self.year_is_date = QCheckBox("Extrair ano da data (AAAA-MM-DD ou DD/MM/AAAA)")
        for label, widget in [("Casa", self.house), ("Codificação", self.encoding),
                              ("Separador", self.delimiter), ("Identificador único", self.id_column),
                              ("Data ou ano", self.year_column), ("Formato da data", self.year_is_date),
                              ("Tipo de proposição", self.type_column)]:
            form.addRow(label, widget)
        layout.addLayout(form)
        layout.addWidget(QLabel("Campos textuais pesquisados (marque um ou mais):"))
        self.text_columns = QListWidget()
        self.text_columns.setMaximumHeight(135)
        layout.addWidget(self.text_columns)
        self.preview_table = _readonly_table([])
        layout.addWidget(self.preview_table)
        self.error_label = QLabel()
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.year_column.currentTextChanged.connect(
            lambda value: self.year_is_date.setChecked("data" in _column_key(value))
        )
        self.preview = None
        self._refresh()
        self.encoding.currentIndexChanged.connect(self._refresh)
        self.delimiter.currentIndexChanged.connect(self._refresh)

    def _refresh(self):
        try:
            self.preview = preview_csv(
                self.path, self.encoding.currentText(), self.delimiter.currentData()
            )
        except (OSError, ValueError) as exc:
            self.preview = None
            self.error_label.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.error_label.setText(
            f"Amostra: até 5 registros. Codificação: {self.preview['encoding']}. "
            f"Separador: {repr(self.preview['delimiter'])}."
        )
        headers = self.preview["headers"]
        suggestions = [
            (self.id_column, ("id", "codigomateria", "codigo", "identificador", "uri")),
            (self.year_column, ("dataapresentacao", "datapresentacaomateria", "ano", "anomateria")),
            (self.type_column, ("siglatipo", "siglasubtipomateria", "siglatipomateria", "tipo", "sigla")),
        ]
        for combo, candidates in suggestions:
            previous = combo.currentText()
            combo.clear()
            combo.addItems(headers)
            suggested = next((h for c in candidates for h in headers if _column_key(h) == c), headers[0])
            combo.setCurrentText(previous if previous in headers else suggested)
        self.text_columns.clear()
        for header in headers:
            item = QListWidgetItem(header)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            selected = any(part in _column_key(header) for part in ("ementa", "indexa", "keyword", "resumo"))
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
            self.text_columns.addItem(item)
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        _fill_table(self.preview_table, [[row[h] for h in headers] for row in self.preview["rows"]])

    def import_spec(self):
        if self.preview is None:
            raise ValueError(self.error_label.text())
        columns = tuple(self.text_columns.item(i).text() for i in range(self.text_columns.count())
                        if self.text_columns.item(i).checkState() == Qt.CheckState.Checked)
        if not columns:
            raise ValueError("Selecione pelo menos um campo textual.")
        mapping = CsvMapping(
            self.id_column.currentText(), self.year_column.currentText(),
            self.type_column.currentText(), columns, self.house.currentText(), self.year_is_date.isChecked(),
        )
        return ImportSpec(self.path, mapping, self.preview["encoding"], self.preview["delimiter"])

    def _accept(self):
        try:
            self.import_spec()
        except ValueError as exc:
            self.error_label.setText(str(exc))
            return
        self.accept()


class LegislativeTab(QWidget):
    series_requested = pyqtSignal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.specs = ()
        self.results = ()
        self.summary = []
        self.worker = None
        self.parameters = {}
        self._stale = True
        layout = QVBoxLayout(self)
        notice = QLabel(
            "Importe o universo completo do período, incluindo matérias encerradas. "
            "Uma proposição conta uma vez por Casa/ID. Texto ausente fica pendente."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self._build_inputs(layout)
        self._build_results(layout)

    def _build_inputs(self, layout):
        row = QHBoxLayout()
        self.add_button = QPushButton("Adicionar CSV…")
        self.clear_button = QPushButton("Limpar arquivos")
        self.process_button = QPushButton("Processar proposições")
        self.process_button.setObjectName("PrimaryButton")
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        for button in (self.add_button, self.clear_button, self.process_button, self.cancel_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(75)
        layout.addWidget(self.file_list)
        self.rule_input = QPlainTextEdit()
        self.rule_input.setMaximumHeight(80)
        self.rule_input.setPlainText("mudanç* climátic* OR mudanç* d* clima OR aquecimento global")
        self.rule_input.setAccessibleName("Expressão booleana climática")
        layout.addWidget(QLabel("Regra climática — AND, OR, NOT, parênteses, |, * e aspas:"))
        layout.addWidget(self.rule_input)
        self.source_note = QLineEdit()
        self.source_note.setPlaceholderText("Descreva a fonte e o universo: apresentação/recebimento, cobertura histórica…")
        self.source_note.setAccessibleName("Descrição da fonte e do universo")
        layout.addWidget(self.source_note)
        filters = QHBoxLayout()
        self.types_input = QLineEdit("PL, PEC, PLP, MPV, PLS, PLC")
        self.types_input.setToolTip("Tipos exatos separados por vírgula. Vazio inclui todos.")
        self.start_year, self.end_year = QSpinBox(), QSpinBox()
        for spin in (self.start_year, self.end_year):
            spin.setRange(0, 9999)
            spin.setSpecialValueText("Sem limite")
        for label, widget in [("Tipos:", self.types_input), ("De:", self.start_year), ("Até:", self.end_year)]:
            filters.addWidget(QLabel(label))
            filters.addWidget(widget)
        layout.addLayout(filters)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status_label = QLabel("Adicione CSVs e confira o mapeamento antes de processar.")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.add_button.clicked.connect(self.browse_csv)
        self.clear_button.clicked.connect(self.clear_imports)
        self.process_button.clicked.connect(self.start_processing)
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.rule_input.textChanged.connect(self._invalidate)
        self.types_input.textChanged.connect(self._refresh_results)
        self.start_year.valueChanged.connect(self._refresh_results)
        self.end_year.valueChanged.connect(self._refresh_results)

    def _build_results(self, layout):
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Localizar ID ou conteúdo entre todos os registros do recorte")
        search_button = QPushButton("Localizar")
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_button)
        layout.addLayout(search_row)
        self.results_table = _readonly_table(
            ["Casa", "ID", "Ano", "Tipo", "Automático", "Final", "Revisado", "Evidências / texto"]
        )
        self.results_table.setColumnWidth(7, 460)
        self.summary_table = _readonly_table([
            "Casa", "Ano", "Total único", "Climáticas", "Não identificadas", "Pendentes",
            "Atenção (%)", "Mínimo identificado (%)",
        ])
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.results_table)
        splitter.addWidget(self.summary_table)
        splitter.setSizes([250, 130])
        layout.addWidget(splitter, 1)
        reviews = QHBoxLayout()
        self.review_note = QLineEdit()
        self.review_note.setMaxLength(2048)
        self.review_note.setPlaceholderText("Nota da revisão (opcional)")
        self.review_buttons = []
        for label, decision in [("Marcar climático", True), ("Marcar não identificado", False),
                                ("Restaurar automático", None)]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, d=decision: self.review_selected(d))
            reviews.addWidget(button)
            self.review_buttons.append(button)
        reviews.addWidget(self.review_note)
        layout.addLayout(reviews)
        actions = QHBoxLayout()
        self.house_for_pet = QComboBox()
        self.send_button = QPushButton("Enviar Casa para Séries PET")
        self.export_button = QPushButton("Exportar XLSX")
        actions.addWidget(self.house_for_pet)
        actions.addWidget(self.send_button)
        actions.addStretch()
        actions.addWidget(self.export_button)
        layout.addLayout(actions)
        self.send_button.clicked.connect(self.send_to_pet)
        self.export_button.clicked.connect(self.export_results)
        search_button.clicked.connect(self._refresh_results)
        self.search_input.returnPressed.connect(self._refresh_results)
        self._invalidate()

    def browse_csv(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar CSV legislativo", "", "CSV (*.csv *.tsv)")
        for path in paths:
            try:
                dialog = CsvMappingDialog(path, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.add_import(dialog.import_spec())
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Erro ao ler CSV", str(exc))

    def add_import(self, spec):
        self.specs = (*self.specs, spec)
        item = QListWidgetItem(f"{spec.mapping.house} — {Path(spec.path).name}")
        item.setToolTip(f"{spec.path}\n{spec.mapping}")
        self.file_list.addItem(item)
        self._invalidate()

    def clear_imports(self):
        self.specs, self.results, self.summary = (), (), []
        self.parameters = {}
        self.file_list.clear()
        self.results_table.setRowCount(0)
        self.summary_table.setRowCount(0)
        self._invalidate()

    def _invalidate(self):
        self._stale = True
        if hasattr(self, "export_button"):
            self.export_button.setEnabled(False)
            self.send_button.setEnabled(False)
            for button in self.review_buttons:
                button.setEnabled(False)
        if self.results:
            self.status_label.setText("Entradas alteradas. Processe novamente para atualizar os resultados.")

    def is_processing(self):
        return self.worker is not None and self.worker.isRunning()

    def start_processing(self):
        if self.is_processing():
            return
        if not self.specs:
            QMessageBox.warning(self, "Sem arquivos", "Adicione pelo menos um CSV.")
            return
        try:
            compile_query(self.rule_input.toPlainText())
            self._filters()
        except ValueError as exc:
            QMessageBox.warning(self, "Parâmetros inválidos", str(exc))
            return
        self._invalidate()
        self._set_busy(True)
        self.worker = LegislativeWorker(self.specs, self.rule_input.toPlainText(), self)
        self.worker.completed.connect(self.accept_results)
        self.worker.error.connect(self._processing_error)
        self.worker.cancelled.connect(lambda: self.status_label.setText("Processamento cancelado; nenhum lote parcial aplicado."))
        self.worker.progress.connect(self.status_label.setText)
        self.worker.finished.connect(self._processing_finished)
        self.worker.start()

    def cancel_processing(self):
        if self.worker:
            self.worker.requestInterruption()
            self.status_label.setText("Cancelando…")

    def _set_busy(self, busy):
        for widget in (self.add_button, self.clear_button, self.process_button, self.rule_input,
                       self.source_note, self.types_input, self.start_year, self.end_year):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.progress.setVisible(busy)

    def _processing_finished(self):
        worker = self.worker
        self.worker = None
        self._set_busy(False)
        if worker:
            worker.deleteLater()

    def _processing_error(self, message):
        self.status_label.setText("Falha no processamento. Corrija os dados e processe novamente.")
        QMessageBox.critical(self, "Erro no CSV", message)

    def accept_results(self, payload):
        self.results = tuple(payload["results"])
        self.parameters = {k: v for k, v in payload.items() if k != "results"}
        self._stale = False
        self._refresh_results()

    def _filters(self):
        kinds = tuple(dict.fromkeys(p.strip().upper() for p in self.types_input.text().split(",") if p.strip()))
        start, end = self.start_year.value() or None, self.end_year.value() or None
        if start and end and start > end:
            raise ValueError("Ano inicial deve ser menor ou igual ao ano final.")
        return dict(kinds=kinds, start_year=start, end_year=end)

    def _eligible(self, proposition, filters):
        return ((not filters["kinds"] or proposition.kind in filters["kinds"])
                and (not filters["start_year"] or proposition.year >= filters["start_year"])
                and (not filters["end_year"] or proposition.year <= filters["end_year"]))

    @staticmethod
    def _decision(value):
        return "Pendente" if value is None else "Climático" if value else "Não identificado"

    def _refresh_results(self):
        if self._stale:
            return
        try:
            filters = self._filters()
            self.summary = annual_summary(self.results, **filters)
        except ValueError as exc:
            self.status_label.setText(str(exc))
            self.export_button.setEnabled(False)
            self.send_button.setEnabled(False)
            for button in self.review_buttons:
                button.setEnabled(False)
            return
        query = normalize(self.search_input.text().strip())
        eligible = [(i, r) for i, r in enumerate(self.results) if self._eligible(r.proposition, filters)]
        visible = [(i, r) for i, r in eligible if not query or query in normalize(
            r.proposition.identifier + " " + " ".join(text for _, text in r.proposition.texts)
        )]
        self._visible_indices = [i for i, _ in visible[:1000]]
        _fill_table(self.results_table, [self._result_cells(r) for _, r in visible[:1000]])
        keys = ["house", "year", "total", "climatic", "not_identified", "pending", "attention_pct", "identified_pct"]
        _fill_table(self.summary_table, [[row[k] for k in keys] for row in self.summary])
        current_house = self.house_for_pet.currentText()
        self.house_for_pet.clear()
        self.house_for_pet.addItems(sorted({r["house"] for r in self.summary}))
        if current_house:
            self.house_for_pet.setCurrentText(current_house)
        self.export_button.setEnabled(bool(eligible))
        self.send_button.setEnabled(bool(self.summary))
        for button in self.review_buttons:
            button.setEnabled(bool(visible))
        self.status_label.setText(
            f"{len(eligible)} proposições no recorte; {self.parameters.get('duplicates', 0)} duplicatas consolidadas. "
            f"Exibindo {min(len(visible), 1000)} de {len(visible)} resultados da busca. "
            "Resumo e exportação usam todo o recorte. Pendentes impedem percentual definitivo."
        )

    def _result_cells(self, result):
        p = result.proposition
        evidence = " | ".join(f"{e.field}: {e.snippet}" for e in result.evidence)
        if not evidence:
            evidence = " | ".join(f"{field}: {text[:260]}" for field, text in p.texts)
        return [p.house, p.identifier, p.year, p.kind, self._decision(result.automatic),
                self._decision(result.climatic), "Sim" if result.review is not None else "Não", evidence]

    def review_selected(self, decision):
        row = self.results_table.currentRow()
        if self._stale or row < 0:
            return
        index = self._visible_indices[row]
        updated = review_proposition(self.results[index], decision, self.review_note.text())
        self.results = tuple(updated if i == index else r for i, r in enumerate(self.results))
        self._refresh_results()
        self.results_table.selectRow(row)

    def send_to_pet(self):
        if self._stale or not self.send_button.isEnabled():
            return
        house = self.house_for_pet.currentText()
        rows = [r for r in self.summary if r["house"] == house]
        if any(row["attention_pct"] is None for row in rows):
            QMessageBox.warning(self, "Pendências no recorte", "Revise os registros pendentes antes de enviar esta Casa para PET.")
            return
        if rows:
            self.series_requested.emit([(r["year"], r["attention_pct"]) for r in rows],
                                       f"Atenção climática — {house}", "Percentual (%)")

    def export_results(self):
        if self._stale or not self.export_button.isEnabled():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar análise legislativa", "atencao_legislativa.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        filters = self._filters()
        selected = tuple(r for r in self.results if self._eligible(r.proposition, filters))
        parameters = self.analysis_parameters()
        try:
            export_legislative_analysis(selected, self.summary, path, parameters=parameters)
            QMessageBox.information(self, "Exportado", f"Arquivo salvo em:\n{path}")
        except (ExcelExportError, OSError, ValueError) as exc:
            QMessageBox.critical(self, "Erro ao exportar", str(exc))

    def analysis_parameters(self):
        filters = self._filters()
        reviews = [
            {"house": r.proposition.house, "identifier": r.proposition.identifier,
             "decision": r.review, "note": r.note}
            for r in self.results if r.review is not None and self._eligible(r.proposition, filters)
        ]
        return {**self.parameters, "filters": filters, "universe_note": self.source_note.text(),
                "reviews": reviews}
