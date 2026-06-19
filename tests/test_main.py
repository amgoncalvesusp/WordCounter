"""Startup smoke tests for the desktop entry point."""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_smoke_test_mode_imports_gui_and_exits_cleanly():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    completed = subprocess.run(
        [sys.executable, "-m", "src.main", "--smoke-test"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
