"""QThread workers for non-blocking PDF processing."""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Tuple

from src.core.pdf_processor import PDFProcessor


class ProcessingWorker(QObject):
    file_started = pyqtSignal(int, str)
    file_progress = pyqtSignal(int, int, int)
    file_finished = pyqtSignal(int, dict)
    all_finished = pyqtSignal(list)
    error = pyqtSignal(int, str, str)

    def __init__(
        self,
        pdf_paths: List[str],
        enable_ocr: bool = True,
        search_terms: List[Tuple[str, bool]] = None,
        enable_sentiment: bool = True,
        enable_president: bool = True,
        enable_textmetrics: bool = True,
        enable_kwic: bool = True,
        enable_climate_policy: bool = True,
    ):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.enable_ocr = enable_ocr
        self.search_terms = search_terms or []
        self.enable_sentiment = enable_sentiment
        self.enable_president = enable_president
        self.enable_textmetrics = enable_textmetrics
        self.enable_kwic = enable_kwic
        self.enable_climate_policy = enable_climate_policy
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        results = []
        processor = PDFProcessor(
            enable_ocr=self.enable_ocr,
            search_terms=self.search_terms,
            detect_sentiment=self.enable_sentiment,
            detect_president=self.enable_president,
            detect_textmetrics=self.enable_textmetrics,
            detect_kwic=self.enable_kwic,
            detect_climate_policy=self.enable_climate_policy,
        )

        for idx, path in enumerate(self.pdf_paths):
            if self._cancelled:
                break
            try:
                self.file_started.emit(idx, path)

                def cb(cur, total, i=idx):
                    self.file_progress.emit(i, cur, total)

                result = processor.process(path, progress_cb=cb)
                results.append(result)
                self.file_finished.emit(idx, result)
            except Exception as e:
                self.error.emit(idx, path, str(e))

        self.all_finished.emit(results)
