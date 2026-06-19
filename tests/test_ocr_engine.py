"""Unit tests for OCR helper logic (no Tesseract required)."""

from zipfile import ZipFile

import pytest

from src.core.ocr_engine import (
    _extract_bundled_tesseract,
    needs_ocr,
    ocr_image,
)

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


def test_extract_bundled_tesseract_to_versioned_cache(tmp_path):
    archive = tmp_path / "tesseract.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("tesseract.exe", b"binary")
        bundle.writestr("tessdata/por.traineddata", b"language")

    executable = _extract_bundled_tesseract(archive, tmp_path / "cache")
    second = _extract_bundled_tesseract(archive, tmp_path / "cache")

    assert executable.read_bytes() == b"binary"
    assert executable == second
    assert (executable.parent / "tessdata" / "por.traineddata").is_file()

    executable.unlink()
    repaired = _extract_bundled_tesseract(archive, tmp_path / "cache")
    assert repaired.read_bytes() == b"binary"


def test_extract_bundled_tesseract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "tesseract.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", b"unsafe")
        bundle.writestr("tesseract.exe", b"binary")

    with pytest.raises(ValueError, match="Unsafe path"):
        _extract_bundled_tesseract(archive, tmp_path / "cache")
