"""Integration tests: full PDF processing pipeline."""

import pytest

from src.core.pdf_processor import PDFProcessor

pytestmark = pytest.mark.integration


def test_process_returns_expected_fields(sample_pdf):
    processor = PDFProcessor(enable_ocr=False)
    result = processor.process(sample_pdf)

    assert result["filename"].endswith(".pdf")
    assert result["total_pages"] == 3
    assert result["words_total"] > 0
    assert result["year"] == "2020"
    assert result["president"] == "Jair Bolsonaro"
    assert result["confidence"] in {"Alto", "Médio", "Baixo"}


def test_process_includes_sentiment_by_default(sample_pdf):
    result = PDFProcessor(enable_ocr=False).process(sample_pdf)
    assert "sent_classe" in result
    assert result["sent_n_sentencas"] >= 1
    assert isinstance(result["sentiment_sentences"], list)


def test_process_without_sentiment_or_president(sample_pdf):
    result = PDFProcessor(
        enable_ocr=False, detect_sentiment=False, detect_president=False
    ).process(sample_pdf)
    assert "sent_classe" not in result
    assert result["president"] == ""


def test_process_with_search_terms(sample_pdf):
    result = PDFProcessor(enable_ocr=False, search_terms=[("clima", False)]).process(
        sample_pdf
    )
    assert "clima" in result["term_results"]
    assert result["term_results"]["clima"]["total"] >= 1


def test_process_climate_policy_can_be_disabled(sample_pdf):
    result = PDFProcessor(
        enable_ocr=False, detect_climate_policy=False
    ).process(sample_pdf)

    assert "climate_policy_profile" not in result
    assert "clim_intensidade" not in result


def test_progress_callback_invoked(sample_pdf):
    seen = []
    PDFProcessor(enable_ocr=False).process(
        sample_pdf, progress_cb=lambda cur, total: seen.append((cur, total))
    )
    assert seen
    assert seen[-1] == (3, 3)
