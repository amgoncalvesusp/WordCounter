"""Shared pytest fixtures."""

import fitz
import pytest


@pytest.fixture
def sample_pages():
    """A small synthetic corpus: a cover page plus two content pages."""
    return [
        "Mensagem ao Congresso Nacional\n2020",  # cover-ish, short
        "O clima melhorou muito e o pais avancou. Foi um otimo resultado.",
        "A crise foi terrivel. O desmatamento aumentou de forma dramatica.",
    ]


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal real PDF on disk and return its path."""
    doc = fitz.open()
    # Content pages must clear the editorial word threshold (>80 words) to enter
    # the analytical corpus, so the bodies are intentionally long.
    pos = (
        "O clima melhorou muito e o pais avancou de forma positiva. "
        "Foi um otimo resultado para todos os setores. " * 6
    )
    neg = (
        "A crise foi terrivel e o desmatamento aumentou de forma dramatica. "
        "O periodo trouxe perdas graves para a populacao. " * 6
    )
    texts = [
        "Mensagem ao Congresso Nacional - 2020 - Presidente Jair Bolsonaro",
        pos,
        neg,
    ]
    rect = fitz.Rect(72, 72, 520, 760)
    for body in texts:
        page = doc.new_page()
        page.insert_textbox(rect, body, fontsize=12)
    out = tmp_path / "msg2020.pdf"
    doc.save(str(out))
    doc.close()
    return str(out)
