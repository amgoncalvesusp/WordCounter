"""Cancellable CSV processing away from the desktop event loop."""

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.legislative import (
    CsvMapping, classify_propositions, deduplicate_propositions, load_propositions,
)


@dataclass(frozen=True)
class ImportSpec:
    path: str
    mapping: CsvMapping
    encoding: str = "auto"
    delimiter: str = "auto"


class LegislativeWorker(QThread):
    completed = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, specs, expression, parent=None):
        super().__init__(parent)
        self.specs = tuple(specs)
        self.expression = expression

    def _check_cancelled(self):
        if self.isInterruptionRequested():
            raise InterruptedError("Processamento cancelado.")

    def _load_source(self, spec):
        path = Path(spec.path)
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                self._check_cancelled()
                digest.update(block)
        imported = load_propositions(
            spec.path, spec.mapping, encoding=spec.encoding,
            delimiter=spec.delimiter, cancel_check=self.isInterruptionRequested,
        )
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"O arquivo mudou durante a leitura: {path.name}. Importe novamente.")
        provenance = {
            "file": str(path.resolve()), "sha256": digest.hexdigest(),
            "mapping": asdict(spec.mapping), "encoding": spec.encoding,
            "delimiter": spec.delimiter,
        }
        return imported, provenance

    def run(self):
        try:
            propositions, sources = [], []
            duplicates = 0
            for spec in self.specs:
                self._check_cancelled()
                self.progress.emit(f"Lendo {Path(spec.path).name}…")
                imported, provenance = self._load_source(spec)
                propositions.extend(imported.propositions)
                duplicates += imported.duplicate_count
                sources.append(provenance)
            self._check_cancelled()
            merged = deduplicate_propositions(propositions, cancel_check=self.isInterruptionRequested)
            self.progress.emit(f"Classificando {len(merged.propositions)} proposições únicas…")
            results = classify_propositions(
                merged.propositions, self.expression,
                cancel_check=self.isInterruptionRequested,
            )
            self._check_cancelled()
            self.completed.emit({
                "results": results, "duplicates": duplicates + merged.duplicate_count,
                "sources": sources, "expression": self.expression,
                "processed_utc": datetime.now(timezone.utc).isoformat(),
            })
        except InterruptedError:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))
