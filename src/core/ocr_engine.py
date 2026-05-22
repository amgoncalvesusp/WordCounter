"""OCR engine wrapper using Tesseract for image-only PDF pages."""
import os
import sys
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image

OCR_TRIGGER_CHAR_COUNT = 50


def configure_tesseract(custom_path: Optional[str] = None) -> bool:
    candidates = []
    if custom_path:
        candidates.append(custom_path)

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        candidates.append(str(bundle_dir / "tesseract" / "tesseract.exe"))

    candidates.extend([
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ])

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return True

    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image(pil_image: Image.Image, lang: str = "por") -> str:
    try:
        return pytesseract.image_to_string(pil_image, lang=lang)
    except Exception:
        return ""


def needs_ocr(extracted_text: str) -> bool:
    if not extracted_text:
        return True
    return len(extracted_text.strip()) < OCR_TRIGGER_CHAR_COUNT
