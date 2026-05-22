"""PDF processing orchestrator."""
import io
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple

import fitz
from PIL import Image

from .word_counter import count_words, count_total
from .corpus_filter import classify_all_pages
from .metadata_detector import detect_metadata
from .ocr_engine import needs_ocr, ocr_image, configure_tesseract
from .term_search import search_all_terms


class PDFProcessor:
    def __init__(self, enable_ocr: bool = True, ocr_lang: str = "por",
                 search_terms: Optional[List[Tuple[str, bool]]] = None):
        self.enable_ocr = enable_ocr
        self.ocr_lang = ocr_lang
        self.tesseract_available = configure_tesseract() if enable_ocr else False
        self.search_terms = search_terms or []

    def process(self, pdf_path: str, progress_cb: Optional[Callable[[int, int], None]] = None) -> Dict:
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

        total_words = count_total(pages_text)
        analytical_words = sum(
            count_words(pages_text[p["page_number"] - 1]) for p in analytical
        )

        metadata = detect_metadata(pages_text, path.name)
        pages_with_text = sum(1 for t in pages_text if t.strip())
        pages_problematic = total_pages - pages_with_text
        confidence = self._assess_confidence(total_pages, pages_with_text, ocr_used_pages)

        term_results = {}
        if self.search_terms:
            term_results = search_all_terms(pages_text, self.search_terms, analytical_page_numbers)

        return {
            "filename": path.name,
            "year": metadata["year"],
            "president": metadata["president"],
            "document": metadata["document"],
            "total_pages": total_pages,
            "pages_with_text": pages_with_text,
            "pages_problematic": pages_problematic,
            "ocr_pages_count": len(ocr_used_pages),
            "ocr_pages_list": ocr_used_pages,
            "words_total": total_words,
            "words_analytical": analytical_words,
            "excluded_pages": excluded,
            "empty_pages": empty_pages,
            "confidence": confidence,
            "observations": self._build_observations(
                total_pages, pages_with_text, ocr_used_pages, empty_pages, len(excluded)
            ),
            "term_results": term_results,
        }

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
