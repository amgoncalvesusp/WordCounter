"""Climate-policy profile analyzer.

This analyzer builds a document-level picture of what the report itself frames
as climate policy. It does not infer that a policy exists outside the text.
Instead, it records textual evidence for reported sectors/instruments and marks
taxonomy items as absent when they are not found in the analytical corpus.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import regex

from .base import ColumnSpec, DocumentContext
from ..term_search import normalize

DIRECT = "reportado_direto"
INDIRECT = "mencao_indireta"
NOT_REPORTED = "nao_reportado"

MAX_EVIDENCE_PER_ITEM = 5
MAX_SNIPPET_CHARS = 260


@dataclass(frozen=True)
class ClimateTaxonomyItem:
    kind: str
    item_id: str
    label: str
    terms: Tuple[str, ...]
    expected: bool = True


@dataclass(frozen=True)
class ClimateEvidence:
    kind: str
    item_id: str
    label: str
    term: str
    page: int
    status: str
    snippet: str


def _data_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "src" / "core" / "data"
    else:
        base = Path(__file__).resolve().parent.parent / "data"
    return base / "climate_policy_taxonomy.json"


def _load_taxonomy(path: Optional[Path] = None) -> Dict[str, object]:
    source = path or _data_path()
    with open(source, encoding="utf-8") as f:
        return json.load(f)


def _items_from_taxonomy(taxonomy: Dict[str, object]) -> List[ClimateTaxonomyItem]:
    items: List[ClimateTaxonomyItem] = []
    for kind, section in (("sector", "sectors"), ("instrument", "instruments")):
        for raw in taxonomy.get(section, []):
            items.append(
                ClimateTaxonomyItem(
                    kind=kind,
                    item_id=str(raw["id"]),
                    label=str(raw["label"]),
                    terms=tuple(str(t) for t in raw.get("terms", [])),
                    expected=bool(raw.get("expected", True)),
                )
            )
    return items


def _split_units(text: str) -> List[str]:
    """Split text into sentence-like units while keeping paragraph fallbacks."""
    units = []
    for paragraph in regex.split(r"\n{2,}", text):
        paragraph = regex.sub(r"\s+", " ", paragraph).strip()
        if not paragraph:
            continue
        parts = regex.split(r"(?<=[.!?;:])\s+", paragraph)
        units.extend(p.strip() for p in parts if p.strip())
    return units


def _contains_term(norm_text: str, norm_term: str) -> bool:
    if not norm_text or not norm_term:
        return False
    words = norm_term.split()
    pattern = r"\b" + r"\s+".join(regex.escape(w) for w in words) + r"\b"
    return bool(regex.search(pattern, norm_text, regex.IGNORECASE))


def _trim_snippet(text: str) -> str:
    cleaned = regex.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= MAX_SNIPPET_CHARS:
        return cleaned
    return cleaned[: MAX_SNIPPET_CHARS - 3].rstrip() + "..."


def _status_rank(status: str) -> int:
    return {NOT_REPORTED: 0, INDIRECT: 1, DIRECT: 2}.get(status, 0)


def _best_status(statuses: Iterable[str]) -> str:
    ranked = sorted(statuses, key=_status_rank, reverse=True)
    return ranked[0] if ranked else NOT_REPORTED


class ClimatePolicyAnalyzer:
    name = "climate_policy"

    def __init__(self, taxonomy_path: Optional[Path] = None):
        self.taxonomy = _load_taxonomy(taxonomy_path)
        self.items = _items_from_taxonomy(self.taxonomy)
        self.climate_terms = tuple(str(t) for t in self.taxonomy.get("climate_terms", []))

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("clim_setores_reportados", "Setores climaticos reportados", 20, "climate"),
            ColumnSpec("clim_instrumentos_reportados", "Instrumentos reportados", 20, "climate"),
            ColumnSpec("clim_cobertura_pct", "Cobertura da taxonomia (%)", 18, "climate"),
            ColumnSpec("clim_intensidade", "Intensidade climatica", 18, "climate"),
            ColumnSpec("clim_setores_dominantes", "Setores dominantes", 34, "climate"),
            ColumnSpec("clim_instrumentos_dominantes", "Instrumentos dominantes", 34, "climate"),
            ColumnSpec("clim_lacunas", "Lacunas no reporte", 40, "climate"),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        evidence = self._collect_evidence(ctx)
        profile = self._summarize(evidence)
        gaps = self._find_gaps(evidence)
        direct_items = {
            (e.kind, e.item_id)
            for e in evidence
            if e.status == DIRECT
        }
        expected_count = sum(1 for item in self.items if item.expected)
        coverage = round((len(direct_items) / expected_count) * 100, 1) if expected_count else 0

        sector_labels = self._dominant_labels(profile, "sector")
        instrument_labels = self._dominant_labels(profile, "instrument")
        intensity = self._intensity_label(len(evidence), len(direct_items))

        return {
            "clim_setores_reportados": profile["sector"]["direct_count"],
            "clim_instrumentos_reportados": profile["instrument"]["direct_count"],
            "clim_cobertura_pct": coverage,
            "clim_intensidade": intensity,
            "clim_setores_dominantes": "; ".join(sector_labels),
            "clim_instrumentos_dominantes": "; ".join(instrument_labels),
            "clim_lacunas": "; ".join(g["label"] for g in gaps[:8]),
            "climate_policy_evidence": [e.__dict__ for e in evidence],
            "climate_policy_gaps": gaps,
            "climate_policy_profile": profile,
        }

    def _collect_evidence(self, ctx: DocumentContext) -> List[ClimateEvidence]:
        evidence: List[ClimateEvidence] = []
        counts: Dict[Tuple[str, str], int] = {}
        for page in ctx.analytical_page_numbers:
            for unit in _split_units(ctx.pages_text[page - 1]):
                norm_unit = normalize(unit)
                has_climate_anchor = any(
                    _contains_term(norm_unit, normalize(term))
                    for term in self.climate_terms
                )
                for item in self.items:
                    matched = self._matched_term(norm_unit, item.terms)
                    if matched is None:
                        continue
                    key = (item.kind, item.item_id)
                    if counts.get(key, 0) >= MAX_EVIDENCE_PER_ITEM:
                        continue
                    status = DIRECT if has_climate_anchor else INDIRECT
                    evidence.append(
                        ClimateEvidence(
                            kind=item.kind,
                            item_id=item.item_id,
                            label=item.label,
                            term=matched,
                            page=page,
                            status=status,
                            snippet=_trim_snippet(unit),
                        )
                    )
                    counts[key] = counts.get(key, 0) + 1
        return evidence

    def _matched_term(self, norm_unit: str, terms: Tuple[str, ...]) -> Optional[str]:
        for term in terms:
            if _contains_term(norm_unit, normalize(term)):
                return term
        return None

    def _summarize(self, evidence: List[ClimateEvidence]) -> Dict[str, Dict[str, object]]:
        profile = {
            "sector": {"direct_count": 0, "indirect_count": 0, "items": {}},
            "instrument": {"direct_count": 0, "indirect_count": 0, "items": {}},
        }
        by_item: Dict[Tuple[str, str], List[ClimateEvidence]] = {}
        for item_evidence in evidence:
            key = (item_evidence.kind, item_evidence.item_id)
            by_item.setdefault(key, []).append(item_evidence)

        for (kind, item_id), rows in by_item.items():
            status = _best_status(row.status for row in rows)
            direct_hits = sum(1 for row in rows if row.status == DIRECT)
            indirect_hits = sum(1 for row in rows if row.status == INDIRECT)
            label = rows[0].label
            profile[kind]["items"][item_id] = {
                "label": label,
                "status": status,
                "direct_hits": direct_hits,
                "indirect_hits": indirect_hits,
                "total_hits": len(rows),
            }
            if status == DIRECT:
                profile[kind]["direct_count"] += 1
            elif status == INDIRECT:
                profile[kind]["indirect_count"] += 1
        return profile

    def _find_gaps(self, evidence: List[ClimateEvidence]) -> List[Dict[str, object]]:
        reported = {
            (row.kind, row.item_id)
            for row in evidence
            if row.status == DIRECT
        }
        gaps = []
        for item in self.items:
            if item.expected and (item.kind, item.item_id) not in reported:
                gaps.append(
                    {
                        "kind": item.kind,
                        "item_id": item.item_id,
                        "label": item.label,
                        "status": NOT_REPORTED,
                    }
                )
        return gaps

    def _dominant_labels(
        self, profile: Dict[str, Dict[str, object]], kind: str, limit: int = 4
    ) -> List[str]:
        items = profile[kind]["items"].values()
        ranked = sorted(
            items,
            key=lambda data: (data["direct_hits"], data["total_hits"], data["label"]),
            reverse=True,
        )
        return [
            f"{data['label']} ({data['direct_hits']})"
            for data in ranked[:limit]
            if data["status"] == DIRECT
        ]

    def _intensity_label(self, evidence_count: int, direct_item_count: int) -> str:
        if direct_item_count >= 8 or evidence_count >= 25:
            return "Alta"
        if direct_item_count >= 3 or evidence_count >= 8:
            return "Media"
        if direct_item_count >= 1:
            return "Baixa"
        return "Ausente"
