"""Ensure the bundled Qt runtime wins Windows DLL resolution."""

import os
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []


def _configure_qt_runtime() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return

    bundle_root = Path(sys._MEIPASS)
    qt_root = bundle_root / "PyQt6" / "Qt6"
    qt_bin = qt_root / "bin"
    qt_plugins = qt_root / "plugins"

    if qt_bin.is_dir():
        os.environ["PATH"] = f"{qt_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(qt_bin)))

    if qt_plugins.is_dir():
        os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)


_configure_qt_runtime()
