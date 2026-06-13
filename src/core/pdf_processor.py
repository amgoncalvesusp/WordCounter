"""PDF processing orchestrator.

Extracts text once per PDF, then runs a list of pluggable analyzers over a
shared :class:`DocumentContext`. Intrinsic extraction fields (confidence,
observations, excluded pages) are produced here; everything else (metadata,
word counts, term search, future sentiment, ...) comes from analyzers.
"""

import io
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import fitz
from PIL import Image

from .analysis import Analyzer, DocumentContext, build_default_analyzers
from .corpus_filter import classify_all_pages
from .ocr_engine import configure_tesseract, needs_ocr, ocr_image


class PDFProcessor:
    def __init__(
        self,
        enable_ocr: bool = True,
        ocr_lang: str = "por",
        search_terms: Optional[List[Tuple[str, bool]]] = None,
        analyzers: Optional[List[Analyzer]] = None,
        detect_sentiment: bool = True,
        detect_president: bool = True,
        detect_textmetrics: bool = True,
        detect_kwic: bool = True,
        detect_climate_policy: bool = True,
    ):
        self.enable_ocr = enable_ocr
        self.ocr_lang = ocr_lang
        self.tesseract_available = configure_tesseract() if enable_ocr else False
        # Analyzers may be injected; otherwise fall back to the default set built
        # from the legacy search_terms argument for backward compatibility.
        self.analyzers = (
            analyzers
            if analyzers is not None
            else build_default_analyzers(
                search_terms,
                detect_president=detect_president,
                detect_sentiment=detect_sentiment,
                detect_textmetrics=detect_textmetrics,
                detect_kwic=detect_kwic,
                detect_climate_policy=detect_climate_policy,
            )
        )

    def process(
        self, pdf_path: str, progress_cb: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        path = Path(pdf_path)
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        pages_text: List[str] = []
        ocr_used_pages: List[int] = []
        empty_pages: List[int] = []

        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            if self.enable_ocr and self.tesseract_available and needs_ocr(text):
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = ocr_image(img, lang=self.ocr_lang)
                if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    ocr_used_pages.append(i + 1)
            if not text.strip():
                empty_pages.append(i + 1)
            pages_text.append(text)
            if progress_cb:
                progress_cb(i + 1, total_pages)

        doc.close()

        page_classifications = classify_all_pages(pages_text)
        excluded = [p for p in page_classifications if not p["is_analytical"]]
        analytical = [p for p in page_classifications if p["is_analytical"]]
        analytical_page_numbers = [p["page_number"] for p in analytical]

        pages_with_text = sum(1 for t in pages_text if t.strip())
        pages_problematic = total_pages - pages_with_text
        confidence = self._assess_confidence(
            total_pages, pages_with_text, ocr_used_pages
        )

        ctx = DocumentContext(
            filename=path.name,
            pages_text=pages_text,
            analytical_page_numbers=analytical_page_numbers,
            total_pages=total_pages,
            stats={
                "pages_with_text": pages_with_text,
                "pages_problematic": pages_problematic,
                "ocr_pages_count": len(ocr_used_pages),
            },
        )

        # Intrinsic extraction fields produced by the orchestrator itself.
        result: Dict = {
            "filename": path.name,
            "ocr_pages_list": ocr_used_pages,
            "excluded_pages": excluded,
            "empty_pages": empty_pages,
            "confidence": confidence,
            "observations": self._build_observations(
                total_pages, pages_with_text, ocr_used_pages, empty_pages, len(excluded)
            ),
        }

        # Merge every analyzer's flat output into the result dict.
        for analyzer in self.analyzers:
            result.update(analyzer.run(ctx))

        return result

    def _assess_confidence(self, total, with_text, ocr_pages):
        if total == 0:
            return "Baixo"
        ratio = with_text / total
        ocr_ratio = len(ocr_pages) / total if total else 0
        if ratio >= 0.95 and ocr_ratio < 0.2:
            return "Alto"
        if ratio >= 0.80:
            return "Médio"
        return "Baixo"

    def _build_observations(self, total, with_text, ocr_pages, empty, excluded):
        parts = []
        if ocr_pages:
            parts.append(f"OCR aplicado em {len(ocr_pages)} página(s)")
        if empty:
            parts.append(f"{len(empty)} página(s) sem texto extraível")
        parts.append(f"{excluded} página(s) excluída(s) do corpus analítico")
        return "; ".join(parts) if parts else "Extração limpa"
