"""Validate native bundle layout and launch the packaged application."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


REQUIRED_QT_ENTRIES = {
    "pyqt6/qt6/bin/qt6core.dll",
    "pyqt6/qt6/bin/qt6gui.dll",
    "pyqt6/qt6/bin/qt6widgets.dll",
    "pyqt6/qtwidgets.pyd",
}

FORBIDDEN_ROOT_DLLS = {
    "libfreetype-6.dll",
    "libgcc_s_seh-1.dll",
    "libharfbuzz-0.dll",
    "libleptonica-6.dll",
    "libstdc++-6.dll",
    "libtesseract-5.dll",
    "libwinpthread-1.dll",
    "zlib1.dll",
}


def _archive_entries(executable: Path) -> set[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller.utils.cliutils.archive_viewer",
        "--list",
        "--brief",
        str(executable),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return {
        line.strip().replace("\\", "/").lower()
        for line in completed.stdout.splitlines()
        if line.strip()
    }


def _validate_archive(entries: set[str], require_tesseract: bool) -> None:
    missing_qt = REQUIRED_QT_ENTRIES - entries
    if missing_qt:
        raise RuntimeError(f"Missing Qt runtime entries: {sorted(missing_qt)}")

    root_dlls = {entry for entry in entries if "/" not in entry}
    conflicts = root_dlls & FORBIDDEN_ROOT_DLLS
    conflicts.update(
        entry
        for entry in root_dlls
        if entry.endswith(".dll")
        and entry.startswith(("icudt", "icuin", "icuuc"))
    )
    if conflicts:
        raise RuntimeError(
            "Conflicting native DLLs found at bundle root: "
            f"{sorted(conflicts)}"
        )

    if require_tesseract and "bundled_tools/tesseract.zip" not in entries:
        raise RuntimeError("Bundled Tesseract archive is missing")


def _run_smoke_test(executable: Path) -> None:
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    completed = subprocess.run(
        [str(executable), "--smoke-test"],
        env=env,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Packaged application smoke test failed with {completed.returncode}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--require-tesseract", action="store_true")
    args = parser.parse_args()

    executable = args.executable.resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)

    entries = _archive_entries(executable)
    _validate_archive(entries, args.require_tesseract)
    _run_smoke_test(executable)
    print(f"Verified Windows executable: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
