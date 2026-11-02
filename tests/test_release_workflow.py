"""Release names remain data rather than executable PowerShell source."""

import hashlib
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/release.yml"


def _run_blocks():
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.fullmatch(r"\s+run: \|", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            yield textwrap.dedent("\n".join(body))


def test_github_context_never_interpolates_into_shell_source():
    scripts = list(_run_blocks())
    assert scripts
    assert all("${{" not in script for script in scripts)
    assert "RELEASE_TAG: ${{ github.ref_name }}" in WORKFLOW.read_text(encoding="utf-8")


@pytest.mark.integration
@pytest.mark.parametrize("tag", ["v1.6", "v-probe$(throw)"])
def test_release_assets_treat_tag_as_literal_data(tmp_path, tag):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("Native release script requires PowerShell.")
    contents = b"release artifact checksum fixture"
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/ContadorPalavras.exe").write_bytes(contents)
    script = next(block for block in _run_blocks() if "Get-FileHash" in block)
    # Reproduce GitHub's substitution to expose the vulnerable form in RED.
    script = script.replace("${{ github.ref_name }}", tag)
    script_path = tmp_path / "release.ps1"
    script_path.write_text(script, encoding="utf-8-sig")
    # Let Windows PowerShell discover its own modules when launched from pwsh.
    child_env = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        env={**child_env, "RELEASE_TAG": tag}, cwd=tmp_path,
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    name = f"ContadorPalavras-{tag}.exe"
    assert (tmp_path / "dist" / name).read_bytes() == contents
    checksum = (tmp_path / "dist" / f"{name}.sha256").read_text(encoding="ascii").strip()
    assert checksum == f"{hashlib.sha256(contents).hexdigest()}  {name}", completed.stderr
