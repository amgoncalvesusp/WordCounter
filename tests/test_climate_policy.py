"""Unit tests for the climate-policy profile analyzer."""

import pytest

from src.core.analysis import DocumentContext
from src.core.analysis.climate_policy import (
    DIRECT,
    INDIRECT,
    ClimatePolicyAnalyzer,
)

pytestmark = pytest.mark.unit


def _ctx(text):
    return DocumentContext(
        filename="clima.pdf",
        pages_text=[text],
        analytical_page_numbers=[1],
        total_pages=1,
    )


def test_climate_policy_detects_direct_reported_sector_and_instrument():
    analyzer = ClimatePolicyAnalyzer()
    result = analyzer.run(
        _ctx(
            "O governo criou um plano de energia renovavel para reduzir "
            "emissoes e enfrentar a mudanca do clima."
        )
    )

    assert result["clim_setores_reportados"] >= 1
    assert result["clim_instrumentos_reportados"] >= 1
    assert result["clim_intensidade"] in {"Baixa", "Media", "Alta"}
    statuses = {row["status"] for row in result["climate_policy_evidence"]}
    assert DIRECT in statuses


def test_climate_policy_keeps_indirect_mentions_separate_from_reported_policy():
    analyzer = ClimatePolicyAnalyzer()
    result = analyzer.run(
        _ctx("O governo ampliou o financiamento rural e investiu em rodovias.")
    )

    assert result["clim_cobertura_pct"] == 0
    assert result["clim_intensidade"] == "Ausente"
    statuses = {row["status"] for row in result["climate_policy_evidence"]}
    assert INDIRECT in statuses
    assert DIRECT not in statuses


def test_climate_policy_lists_taxonomy_gaps_when_items_are_not_reported():
    analyzer = ClimatePolicyAnalyzer()
    result = analyzer.run(_ctx("O texto nao menciona politicas ambientais."))

    labels = {row["label"] for row in result["climate_policy_gaps"]}
    assert "Energia" in labels
    assert "Planejamento" in labels
    assert result["clim_lacunas"]


def test_climate_policy_uses_only_analytical_pages():
    analyzer = ClimatePolicyAnalyzer()
    ctx = DocumentContext(
        filename="clima.pdf",
        pages_text=[
            "Capa com energia renovavel e clima.",
            "Conteudo sem politica climatica.",
        ],
        analytical_page_numbers=[2],
        total_pages=2,
    )

    result = analyzer.run(ctx)

    assert result["clim_setores_reportados"] == 0
    assert result["clim_cobertura_pct"] == 0
