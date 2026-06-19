"""Main application window."""

from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.styles import STYLE
from src.gui.workers import ProcessingWorker
from src.gui.help_dialog import HelpDialog
from src.core.analysis import build_column_specs, build_default_analyzers
from src.core.exporter import export_to_xlsx
from src.core.ocr_engine import configure_tesseract
from src.core.term_search import parse_terms


class DropZone(QFrame):
    def __init__(self, on_files_dropped):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.on_files_dropped = on_files_dropped
        layout = QVBoxLayout(self)
        self.label = QLabel('Arraste PDFs aqui ou clique em "Adicionar Arquivos"')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #a6adc8; font-size: 11pt; padding: 14px;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [u.toLocalFile() for u in urls]
            has_pdf = any(p.lower().endswith(".pdf") for p in paths)
            has_dir = any(Path(p).is_dir() for p in paths)
            if has_pdf or has_dir:
                self.setProperty("active", "true")
                self.style().unpolish(self)
                self.style().polish(self)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        paths = []
        for u in event.mimeData().urls():
            local = u.toLocalFile()
            p = Path(local)
            if p.is_dir():
                paths.extend(str(x) for x in p.glob("*.pdf"))
                paths.extend(str(x) for x in p.glob("*.PDF"))
            elif local.lower().endswith(".pdf"):
                paths.append(local)
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if paths:
            self.on_files_dropped(paths)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Contador de Palavras — Mensagens Presidenciais")
        self.resize(1280, 860)
        self.setStyleSheet(STYLE)

        self.pdf_files: List[str] = []
        self.results: List[dict] = []
        self.worker_thread = None
        self.worker = None
        self._term_labels: List[str] = []

        self._build_ui()
        self._build_menu()
        self._check_tesseract()

    def _build_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #181825; color: #cdd6f4; border-bottom: 1px solid #313244; padding: 4px; }
            QMenuBar::item { padding: 6px 12px; }
            QMenuBar::item:selected { background-color: #313244; color: #cba6f7; }
            QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; padding: 4px; }
            QMenu::item { padding: 6px 24px; }
            QMenu::item:selected { background-color: #313244; color: #cba6f7; }
        """)
        file_menu = menubar.addMenu("&Arquivo")
        act_add = QAction("Adicionar PDFs...", self)
        act_add.setShortcut("Ctrl+O")
        act_add.triggered.connect(self.browse_files)
        file_menu.addAction(act_add)

        act_export = QAction("Exportar XLSX...", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self.export_results)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_exit = QAction("Sair", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        help_menu = menubar.addMenu("Aj&uda")
        act_help = QAction("Como usar", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(self.show_help)
        help_menu.addAction(act_help)

        act_about = QAction("Sobre", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("Contador de Palavras")
        title.setObjectName("Title")
        title_row.addWidget(title)
        title_row.addStretch()
        self.btn_help = QPushButton("❓  Como usar")
        self.btn_help.clicked.connect(self.show_help)
        title_row.addWidget(self.btn_help)
        main_layout.addLayout(title_row)

        subtitle = QLabel(
            "Análise padronizada de PDFs — Mensagens Presidenciais ao Congresso Nacional"
        )
        subtitle.setObjectName("Subtitle")
        main_layout.addWidget(subtitle)

        self.drop_zone = DropZone(self.add_files)
        main_layout.addWidget(self.drop_zone)

        file_row = QHBoxLayout()
        self.btn_add = QPushButton("➕  Adicionar Arquivos")
        self.btn_clear = QPushButton("🗑  Limpar Lista")
        self.btn_clear.setObjectName("DangerButton")
        self.ocr_checkbox = QCheckBox("Aplicar OCR em páginas escaneadas (Tesseract)")
        self.ocr_checkbox.setChecked(True)
        self.sentiment_checkbox = QCheckBox("Análise de sentimento (LeIA / VADER-PT)")
        self.sentiment_checkbox.setChecked(True)
        self.sentiment_checkbox.setToolTip(
            "Escore de valência por sentença (Hutto & Gilbert, 2014; LeIA). "
            "Gera classe, composto médio e detalhamento por sentença para análise "
            "de conteúdo e núcleos de significação."
        )
        self.president_checkbox = QCheckBox("Detectar presidente")
        self.president_checkbox.setChecked(True)
        self.president_checkbox.setToolTip(
            "Identifica o chefe de Estado a partir do conteúdo (lista em "
            "data/presidents.json). Desative para corpora genéricos."
        )
        self.textmetrics_checkbox = QCheckBox("Métricas textuais")
        self.textmetrics_checkbox.setChecked(True)
        self.textmetrics_checkbox.setToolTip(
            "Legibilidade (Flesch-PT), diversidade lexical (TTR/Guiraud) e "
            "frequência de palavras-chave. Exportadas no XLSX (incl. aba "
            "'Frequência de Palavras') para análise de conteúdo."
        )
        self.climate_policy_checkbox = QCheckBox("Perfil de política climática")
        self.climate_policy_checkbox.setChecked(True)
        self.climate_policy_checkbox.setToolTip(
            "Classifica o que o documento reporta como política climática, "
            "por setor e instrumento, e exporta evidências e lacunas no XLSX."
        )
        self.kwic_checkbox = QCheckBox("Concordância (KWIC)")
        self.kwic_checkbox.setChecked(True)
        self.kwic_checkbox.setToolTip(
            "Para cada termo de busca, registra o contexto ao redor de cada "
            "ocorrência (aba 'Concordância (KWIC)' no XLSX). Requer termos de "
            "busca. Unidade de contexto para análise de conteúdo."
        )
        file_row.addWidget(self.btn_add)
        file_row.addWidget(self.btn_clear)
        file_row.addStretch()
        file_row.addWidget(self.president_checkbox)
        file_row.addWidget(self.textmetrics_checkbox)
        file_row.addWidget(self.climate_policy_checkbox)
        file_row.addWidget(self.kwic_checkbox)
        file_row.addWidget(self.sentiment_checkbox)
        file_row.addWidget(self.ocr_checkbox)
        main_layout.addLayout(file_row)

        self.btn_add.clicked.connect(self.browse_files)
        self.btn_clear.clicked.connect(self.clear_files)

        # Splitter: files list + search terms
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("QSplitter::handle { background: #313244; }")

        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        list_header = QLabel("Arquivos selecionados")
        list_header.setObjectName("SectionHeader")
        left_layout.addWidget(list_header)
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(140)
        left_layout.addWidget(self.file_list)
        splitter.addWidget(left_box)

        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        search_row = QHBoxLayout()
        search_header = QLabel("Termos de busca (opcional)")
        search_header.setObjectName("SectionHeader")
        search_row.addWidget(search_header)
        search_row.addStretch()
        btn_help_search = QPushButton("?")
        btn_help_search.setFixedSize(28, 28)
        btn_help_search.setToolTip("Como usar a busca de termos")
        btn_help_search.clicked.connect(self.show_help)
        search_row.addWidget(btn_help_search)
        right_layout.addLayout(search_row)

        self.terms_input = QPlainTextEdit()
        self.terms_input.setPlaceholderText(
            "Um termo por linha. Exemplos:\n\n"
            "clima\n"
            "desmatamento\n"
            '"efeito estufa"           (aspas = busca exata)\n'
            '"mudança do clima"\n'
            "# linhas começando com # são ignoradas"
        )
        self.terms_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
                font-family: "Consolas", "Cascadia Code", monospace;
                font-size: 10pt;
            }
            QPlainTextEdit:focus { border-color: #cba6f7; }
        """)
        right_layout.addWidget(self.terms_input)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, stretch=2)

        action_row = QHBoxLayout()
        self.btn_process = QPushButton("▶  Processar PDFs")
        self.btn_process.setObjectName("PrimaryButton")
        self.btn_process.clicked.connect(self.start_processing)
        self.btn_cancel = QPushButton("✖  Cancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)
        self.btn_export = QPushButton("⬇  Exportar XLSX")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_results)
        action_row.addWidget(self.btn_process)
        action_row.addWidget(self.btn_cancel)
        action_row.addStretch()
        action_row.addWidget(self.btn_export)
        main_layout.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        result_header = QLabel("Resultados")
        result_header.setObjectName("SectionHeader")
        main_layout.addWidget(result_header)
        self.results_table = QTableWidget(0, 8)
        self._rebuild_results_table([])
        self.results_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.results_table, stretch=2)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto. Pressione F1 para ajuda.")

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def show_about(self):
        QMessageBox.about(
            self,
            "Sobre — Contador de Palavras",
            "<h3>Contador de Palavras</h3>"
            "<p>Análise padronizada de PDFs para pesquisa acadêmica.</p>"
            "<p>Versão 1.3 — análise textual e perfil de política climática.</p>"
            "<hr>"
            "<p><b>Autoria</b></p>"
            "<ul style='margin-left:8px;'>"
            "<li>Natalia Vieira de Carvalho</li>"
            "<li>Alessandra Nascimento dos Santos</li>"
            "<li>Helena Carvalho de Lorenzo</li>"
            "<li>Adriano Marques Gonçalves</li>"
            "</ul>"
            "<p><i>Programa de Pós-graduação em Desenvolvimento Territorial "
            "e Meio Ambiente — UNIARA</i></p>",
        )

    def _check_tesseract(self):
        if configure_tesseract():
            self.status_bar.showMessage(
                "Tesseract detectado — OCR disponível. F1 para ajuda."
            )
        else:
            self.ocr_checkbox.setChecked(False)
            self.ocr_checkbox.setEnabled(False)
            self.status_bar.showMessage(
                "Tesseract não encontrado — OCR desabilitado. F1 para ajuda."
            )

    def browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar PDFs", "", "PDF Files (*.pdf)"
        )
        if paths:
            self.add_files(paths)

    def add_files(self, paths: List[str]):
        added = 0
        for p in paths:
            if p not in self.pdf_files and p.lower().endswith(".pdf"):
                self.pdf_files.append(p)
                item = QListWidgetItem(f"📄  {Path(p).name}")
                item.setToolTip(p)
                self.file_list.addItem(item)
                added += 1
        self.status_bar.showMessage(
            f"{added} arquivo(s) adicionado(s). Total: {len(self.pdf_files)}"
        )

    def clear_files(self):
        self.pdf_files.clear()
        self.file_list.clear()
        self.results.clear()
        self.results_table.setRowCount(0)
        self.btn_export.setEnabled(False)
        self.status_bar.showMessage("Lista limpa.")

    def start_processing(self):
        if not self.pdf_files:
            QMessageBox.warning(
                self, "Nenhum arquivo", "Adicione PDFs antes de processar."
            )
            return

        search_terms = parse_terms(self.terms_input.toPlainText())
        self._search_terms = search_terms
        self._enable_sentiment = self.sentiment_checkbox.isChecked()
        self._enable_president = self.president_checkbox.isChecked()
        self._enable_textmetrics = self.textmetrics_checkbox.isChecked()
        self._enable_kwic = self.kwic_checkbox.isChecked()
        self._enable_climate_policy = self.climate_policy_checkbox.isChecked()
        self._rebuild_results_table(search_terms)

        self.results.clear()
        self.btn_process.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_add.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(self.pdf_files) * 100)
        self.progress.setValue(0)

        self.worker_thread = QThread()
        self.worker = ProcessingWorker(
            self.pdf_files.copy(),
            enable_ocr=self.ocr_checkbox.isChecked(),
            search_terms=search_terms,
            enable_sentiment=self._enable_sentiment,
            enable_president=self._enable_president,
            enable_textmetrics=self._enable_textmetrics,
            enable_kwic=self._enable_kwic,
            enable_climate_policy=self._enable_climate_policy,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.file_started.connect(self.on_file_started)
        self.worker.file_progress.connect(self.on_file_progress)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.all_finished.connect(self.on_all_finished)
        self.worker.error.connect(self.on_error)
        self.worker_thread.start()

    def _rebuild_results_table(self, search_terms):
        self._president_on = getattr(self, "_enable_president", True)
        base_headers = ["#", "Arquivo", "Ano"]
        base_widths = [40, 280, 70]
        if self._president_on:
            base_headers.append("Presidente")
            base_widths.append(200)
        base_headers += ["Páginas", "Palavras (PDF)", "Palavras (Corpus)", "Confiança"]
        base_widths += [80, 130, 150, 90]

        self._sentiment_on = getattr(self, "_enable_sentiment", False)
        if self._sentiment_on:
            base_headers += ["Sentimento", "Comp. médio"]
            base_widths += [110, 100]
        self._sentiment_cols = 2 if self._sentiment_on else 0

        self._climate_policy_on = getattr(self, "_enable_climate_policy", False)
        if self._climate_policy_on:
            base_headers += ["Clima", "Cobertura (%)"]
            base_widths += [110, 110]
        self._climate_policy_cols = 2 if self._climate_policy_on else 0

        self._term_labels = []
        for term, exact in search_terms:
            label = f'"{term}"' if exact else term
            self._term_labels.append(label)
            base_headers.append(f"{label}\n(Corpus)")

        self.results_table.setColumnCount(len(base_headers))
        self.results_table.setHorizontalHeaderLabels(base_headers)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.results_table.setRowCount(0)
        widths = base_widths + [110] * len(self._term_labels)
        for i, w in enumerate(widths):
            self.results_table.setColumnWidth(i, w)

    def cancel_processing(self):
        if self.worker:
            self.worker.cancel()
        self.status_bar.showMessage("Cancelando...")

    def on_file_started(self, idx: int, filename: str):
        self.status_bar.showMessage(
            f"Processando {Path(filename).name} ({idx + 1}/{len(self.pdf_files)})..."
        )

    def on_file_progress(self, file_idx: int, current: int, total: int):
        per_file = (current / total) * 100 if total else 100
        overall = file_idx * 100 + per_file
        self.progress.setValue(int(overall))

    def on_file_finished(self, idx: int, result: dict):
        self.results.append(result)
        self._add_result_row(idx + 1, result)

    def on_all_finished(self, results: List[dict]):
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.btn_process.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_add.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.btn_export.setEnabled(len(results) > 0)
        self.progress.setVisible(False)
        self.status_bar.showMessage(
            f"Concluído. {len(results)} arquivo(s) processado(s)."
        )

    def on_error(self, idx: int, path: str, error_msg: str):
        QMessageBox.critical(
            self, "Erro no processamento", f"{Path(path).name}:\n\n{error_msg}"
        )

    def _add_result_row(self, doc_id: int, result: dict):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        words_total_str = f"{result['words_total']:,}".replace(",", ".")
        words_corpus_str = f"{result['words_analytical']:,}".replace(",", ".")
        cells = [str(doc_id), result["filename"], result["year"]]
        if getattr(self, "_president_on", True):
            cells.append(result["president"])
        cells += [
            str(result["total_pages"]),
            words_total_str,
            words_corpus_str,
            result["confidence"],
        ]
        conf_col = len(cells) - 1
        for col, value in enumerate(cells):
            item = QTableWidgetItem(value)
            if col == conf_col:
                if value == "Alto":
                    item.setForeground(Qt.GlobalColor.green)
                elif value == "Médio":
                    item.setForeground(Qt.GlobalColor.yellow)
                else:
                    item.setForeground(Qt.GlobalColor.red)
            self.results_table.setItem(row, col, item)

        next_col = len(cells)
        if getattr(self, "_sentiment_cols", 0):
            classe = result.get("sent_classe", "")
            item_cls = QTableWidgetItem(classe)
            item_cls.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if classe == "Positivo":
                item_cls.setForeground(Qt.GlobalColor.green)
            elif classe == "Negativo":
                item_cls.setForeground(Qt.GlobalColor.red)
            self.results_table.setItem(row, next_col, item_cls)

            comp = QTableWidgetItem(str(result.get("sent_compound_medio", "")))
            comp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, next_col + 1, comp)
            next_col += self._sentiment_cols

        if getattr(self, "_climate_policy_cols", 0):
            intensity = str(result.get("clim_intensidade", ""))
            item_intensity = QTableWidgetItem(intensity)
            item_intensity.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if intensity == "Alta":
                item_intensity.setForeground(Qt.GlobalColor.green)
            elif intensity == "Media":
                item_intensity.setForeground(Qt.GlobalColor.yellow)
            elif intensity == "Baixa":
                item_intensity.setForeground(Qt.GlobalColor.cyan)
            self.results_table.setItem(row, next_col, item_intensity)

            coverage = QTableWidgetItem(str(result.get("clim_cobertura_pct", "")))
            coverage.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, next_col + 1, coverage)
            next_col += self._climate_policy_cols

        term_results = result.get("term_results", {})
        for i, label in enumerate(self._term_labels):
            count = term_results.get(label, {}).get("analytical", 0)
            item = QTableWidgetItem(str(count))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, next_col + i, item)

    def export_results(self):
        if not self.results:
            QMessageBox.information(
                self, "Sem resultados", "Processe ao menos um PDF antes de exportar."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar resultados", "contagem_palavras.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            analyzers = build_default_analyzers(
                getattr(self, "_search_terms", []),
                detect_president=getattr(self, "_enable_president", True),
                detect_sentiment=getattr(self, "_enable_sentiment", True),
                detect_textmetrics=getattr(self, "_enable_textmetrics", True),
                detect_kwic=getattr(self, "_enable_kwic", True),
                detect_climate_policy=getattr(
                    self, "_enable_climate_policy", True
                ),
            )
            column_specs = build_column_specs(analyzers)
            export_to_xlsx(self.results, path, column_specs)
            QMessageBox.information(self, "Exportado", f"Arquivo salvo em:\n{path}")
            self.status_bar.showMessage(f"Exportado: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao exportar", str(e))
