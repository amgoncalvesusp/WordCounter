"""OCR engine wrapper using Tesseract for image-only PDF pages."""
import os
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile, ZipFile

import pytesseract
from PIL import Image

OCR_TRIGGER_CHAR_COUNT = 50
BUNDLED_TESSERACT_ARCHIVE = Path("bundled_tools") / "tesseract.zip"


def _bundle_fingerprint(archive: Path) -> str:
    digest = hashlib.sha256()
    with ZipFile(archive) as bundle:
        for item in sorted(bundle.infolist(), key=lambda value: value.filename):
            digest.update(item.filename.encode("utf-8"))
            digest.update(str(item.CRC).encode("ascii"))
            digest.update(str(item.file_size).encode("ascii"))
    return digest.hexdigest()[:16]


def _validate_bundle_paths(bundle: ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for item in bundle.infolist():
        target = (destination / item.filename).resolve()
        if target != destination and destination not in target.parents:
            raise ValueError(f"Unsafe path in Tesseract bundle: {item.filename}")


def _extract_bundled_tesseract(archive: Path, cache_root: Path) -> Path:
    cache_root.mkdir(parents=True, exist_ok=True)
    destination = cache_root / f"tesseract-{_bundle_fingerprint(archive)}"
    executable = destination / "tesseract.exe"
    if executable.is_file():
        return executable

    temporary = Path(tempfile.mkdtemp(prefix="tesseract-", dir=cache_root))
    try:
        with ZipFile(archive) as bundle:
            _validate_bundle_paths(bundle, temporary)
            bundle.extractall(temporary)
        if not (temporary / "tesseract.exe").is_file():
            raise FileNotFoundError("tesseract.exe is missing from bundle")
        if destination.exists() and not executable.is_file():
            shutil.rmtree(destination, ignore_errors=True)
        if destination.exists():
            shutil.rmtree(temporary)
        else:
            temporary.replace(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return executable


def _bundled_tesseract_path() -> Optional[Path]:
    if not getattr(sys, "frozen", False):
        return None
    bundle_dir = Path(sys._MEIPASS)
    archive = bundle_dir / BUNDLED_TESSERACT_ARCHIVE
    if archive.is_file():
        local_app_data = Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir()))
        cache_root = local_app_data / "ContadorPalavras" / "tools"
        return _extract_bundled_tesseract(archive, cache_root)
    legacy_executable = bundle_dir / "tesseract" / "tesseract.exe"
    return legacy_executable if legacy_executable.is_file() else None


def configure_tesseract(custom_path: Optional[str] = None) -> bool:
    candidates = []
    if custom_path:
        candidates.append(custom_path)

    try:
        bundled = _bundled_tesseract_path()
        if bundled is not None:
            candidates.append(str(bundled))
    except (BadZipFile, OSError, ValueError):
        pass

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


def validate_bundled_tesseract() -> bool:
    """Run the bundled executable once during packaged-build smoke tests."""
    try:
        executable = _bundled_tesseract_path()
        if executable is None:
            return True
        completed = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            timeout=30,
            check=False,
        )
        return completed.returncode == 0
    except (BadZipFile, OSError, subprocess.SubprocessError, ValueError):
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
