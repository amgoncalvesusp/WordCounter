"""Unit tests for OCR helper logic (no Tesseract required)."""

import pytest

from src.core.ocr_engine import needs_ocr, ocr_image

pytestmark = pytest.mark.unit


def test_needs_ocr_on_empty_text():
    assert needs_ocr("") is True


def test_needs_ocr_on_short_text():
    assert needs_ocr("poucos chars") is True


def test_no_ocr_on_long_text():
    assert needs_ocr("x" * 100) is False


def test_ocr_image_returns_empty_on_bad_input():
    # Passing a non-image must be swallowed and return "".
    assert ocr_image(object()) == ""
