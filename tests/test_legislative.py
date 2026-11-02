"""Legislative CSV import, auditable classification and annual denominators."""

from dataclasses import FrozenInstanceError

import pytest

from src.core.legislative import (
    ClassifiedProposition,
    CsvMapping,
    Proposition,
    annual_summary,
    classify_propositions,
    deduplicate_propositions,
    load_propositions,
    preview_csv,
    review_proposition,
)

pytestmark = pytest.mark.unit


def mapping(**overrides):
    values = dict(id_column="id", year_column="ano", type_column="tipo",
                  text_columns=("ementa", "keywords"), house="Câmara")
    return CsvMapping(**(values | overrides))


def proposition(identifier="1", year=2024, kind="PL", house="Câmara", text="clima"):
    return Proposition(identifier, house, year, kind, (("ementa", text),), "fonte.csv")


def test_utf8_bom_semicolon_multiline_and_preview(tmp_path):
    path = tmp_path / "camara.csv"
    path.write_text('id;ano;tipo;ementa;keywords\n001;2024;pl;"Mudanças\nclimáticas; ação";carbono\n',
                    encoding="utf-8-sig")
    preview = preview_csv(path)
    assert preview["headers"] == ["id", "ano", "tipo", "ementa", "keywords"]
    assert preview["delimiter"] == ";"
    assert preview["rows"][0]["ementa"] == "Mudanças\nclimáticas; ação"
    imported = load_propositions(path, mapping())
    assert imported.duplicate_count == 0
    item = imported.propositions[0]
    assert (item.identifier, item.kind, item.year, item.house) == ("001", "PL", 2024, "Câmara")
    assert dict(item.texts)["ementa"] == "Mudanças\nclimáticas; ação"


def test_cp1252_comma_and_empty_fields(tmp_path):
    path = tmp_path / "senado.csv"
    path.write_bytes("id,ano,tipo,ementa,keywords\n2,2025,PEC,Transição energética,\n".encode("cp1252"))
    assert preview_csv(path)["encoding"] == "cp1252"
    imported = load_propositions(path, mapping(house="Senado"))
    assert dict(imported.propositions[0].texts) == {"ementa": "Transição energética", "keywords": ""}


def test_preview_limits_sample_to_five_records(tmp_path):
    path = tmp_path / "many.csv"
    path.write_text("id\tano\ttipo\tementa\tkeywords\n" +
                    "".join(f"{i}\t2024\tPL\tclima\t\n" for i in range(8)), encoding="utf-8")
    assert len(preview_csv(path)["rows"]) == 5
    assert len(load_propositions(path, mapping()).propositions) == 8


@pytest.mark.parametrize("raw, message", [
    ("", "vazio"),
    ("id;ano;tipo;ementa;ementa\n1;2024;PL;clima;x\n", "duplicad"),
    ("id;ano;;ementa;keywords\n1;2024;PL;clima;x\n", "cabeçalho"),
    ("id;ano;tipo;ementa;keywords\n1;2024;PL;clima\n", "colunas"),
    ("id;ano;tipo;ementa;keywords\n1;2024;PL;clima;x;extra\n", "colunas"),
    ("id;ano;tipo;ementa;keywords\n;2024;PL;clima;x\n", "identificador"),
    ("id;ano;tipo;ementa;keywords\n1;2024;;clima;x\n", "tipo"),
    ("id;ano;tipo;ementa;keywords\n1;2024.0;PL;clima;x\n", "ano"),
    ("id;ano;tipo;ementa;keywords\n1;0;PL;clima;x\n", "ano"),
    ('id;ano;tipo;ementa;keywords\n1;2024;PL;"clima;x\n', "CSV"),
])
def test_invalid_csv_reports_error(tmp_path, raw, message):
    path = tmp_path / "invalid.csv"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_propositions(path, mapping(), delimiter=";")


@pytest.mark.parametrize("value, year", [("2024-12-31", 2024), ("2025-02-01T14:05:00Z", 2025),
                                       ("31/12/2023", 2023), ("01/02/2022 12:30:00", 2022)])
def test_presentation_date_determines_year(tmp_path, value, year):
    path = tmp_path / "date.csv"
    path.write_text(f"id;ano;tipo;ementa;keywords\n1;{value};PL;clima;\n", encoding="utf-8")
    assert load_propositions(path, mapping(year_is_date=True)).propositions[0].year == year


@pytest.mark.parametrize("value", ["31/02/2024", "2024", "02/03/24", "2024-13-01", ""])
def test_invalid_dates_fail(tmp_path, value):
    path = tmp_path / "date.csv"
    path.write_text(f"id;ano;tipo;ementa;keywords\n1;{value};PL;clima;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="data"):
        load_propositions(path, mapping(year_is_date=True))


def test_mapping_and_csv_options_are_validated(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("id;ano;tipo;ementa;keywords\n1;2024;PL;clima;\n", encoding="utf-8")
    for changes in ({"id_column": "missing"}, {"house": ""}, {"text_columns": ()},
                    {"text_columns": ("ementa", "ementa")}, {"type_column": "id"}):
        with pytest.raises(ValueError):
            load_propositions(path, mapping(**changes))
    for options in ({"encoding": "unknown-encoding"}, {"delimiter": "||"}, {"delimiter": ""}):
        with pytest.raises(ValueError):
            preview_csv(path, **options)


def test_header_only_csv_is_accepted_as_empty_universe(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("id;ano;tipo;ementa;keywords\n", encoding="utf-8")
    assert load_propositions(path, mapping()).propositions == ()


def test_dedup_merges_evidence_and_sources_without_mutating():
    first = proposition(text="clima")
    second = Proposition("1", "Câmara", 2024, "PL", (("ementa", "carbono"), ("keywords", "emissões")), "outro.csv")
    imported = deduplicate_propositions((first, second, first, proposition(house="Senado")))
    assert imported.duplicate_count == 2
    assert len(imported.propositions) == 2
    merged = imported.propositions[0]
    assert dict(merged.texts) == {"ementa": "clima", "ementa [versão 2]": "carbono", "keywords": "emissões"}
    assert merged.source_file == "fonte.csv; outro.csv"
    assert first.texts == (("ementa", "clima"),)
    with pytest.raises(FrozenInstanceError):
        merged.year = 2023


@pytest.mark.parametrize("second", [proposition(year=2025), proposition(kind="PEC")])
def test_conflicting_duplicates_fail(second):
    with pytest.raises(ValueError, match="conflit"):
        deduplicate_propositions((proposition(), second))


def test_multiline_duplicate_does_not_accumulate_after_merging():
    first = proposition(text="mudanças\nclimáticas")
    other = proposition(text="carbono")
    merged = deduplicate_propositions((first, other, first, other)).propositions[0]
    assert dict(merged.texts) == {"ementa": "mudanças\nclimáticas", "ementa [versão 2]": "carbono"}


def test_phrase_never_crosses_duplicate_text_versions():
    merged = deduplicate_propositions((proposition(text="mudanças"), proposition(text="climáticas")))
    phrase = classify_propositions(merged.propositions, '"mudanças climáticas"')[0]
    assert phrase.automatic is False
    conjunction = classify_propositions(merged.propositions, "mudanças AND climáticas")[0]
    assert conjunction.automatic is True
    assert {evidence.field for evidence in conjunction.evidence} == {"ementa", "ementa [versão 2]"}


def test_version_labels_preserve_real_column_names_and_repeated_versions():
    original = Proposition("1", "Câmara", 2024, "PL",
                           (("ementa", "mudanças"), ("ementa [versão 2]", "coluna original")), "a.csv")
    other = proposition(text="climáticas")
    merged = deduplicate_propositions((original, other, other, original)).propositions[0]
    assert dict(merged.texts) == {"ementa": "mudanças", "ementa [versão 2]": "coluna original",
                                 "ementa [versão 3]": "climáticas"}


def test_new_versions_do_not_take_names_of_incoming_original_columns():
    original = proposition(text="mudanças")
    other = Proposition("1", "Câmara", 2024, "PL",
                        (("ementa", "climáticas"), ("ementa [versão 2]", "coluna real")), "b.csv")
    merged = deduplicate_propositions((original, other, other)).propositions[0]
    assert dict(merged.texts) == {"ementa": "mudanças", "ementa [versão 3]": "climáticas",
                                 "ementa [versão 2]": "coluna real"}


def test_previously_merged_files_deduplicate_reordered_versions(tmp_path):
    paths = (tmp_path / "a.csv", tmp_path / "b.csv")
    for path, values in zip(paths, (("mudanças", "climáticas"), ("climáticas", "mudanças"))):
        path.write_text("id;ano;tipo;ementa;keywords\n" +
                        "".join(f"1;2024;PL;{value};\n" for value in values), encoding="utf-8")
    items = tuple(item for path in paths for item in load_propositions(path, mapping()).propositions)
    merged = deduplicate_propositions(items).propositions[0]
    assert dict(merged.texts) == {"ementa": "mudanças", "keywords": "", "ementa [versão 2]": "climáticas"}
    assert classify_propositions((merged,), '"mudanças climáticas"')[0].automatic is False


def test_automatic_decisions_preserve_evidence_and_blank_is_pending():
    result = classify_propositions((proposition(text="Mudanças climáticas"),
                                    proposition("2", text="Escolas públicas"),
                                    proposition("3", text=" \n")), "mudanç* climátic*")
    assert [row.automatic for row in result] == [True, False, None]
    assert result[0].evidence[0].field == "ementa"
    assert "climáticas" in result[0].evidence[0].snippet
    assert result[1].evidence == result[2].evidence == ()


def test_review_is_immutable_and_can_restore_automatic():
    original = classify_propositions((proposition(text="clima"),), "clima")[0]
    reviewed = review_proposition(original, False, "contexto econômico")
    assert reviewed.climatic is False
    assert reviewed.automatic is True
    assert reviewed.note == "contexto econômico"
    assert reviewed.evidence == original.evidence
    assert original.climatic is True
    assert review_proposition(reviewed, None).climatic is True
    with pytest.raises(ValueError):
        review_proposition(original, "sim")


def test_annual_denominator_filters_and_pending_uncertainty():
    rows = tuple(ClassifiedProposition(p, climatic, ()) for p, climatic in [
        (proposition("1", 2024), True), (proposition("2", 2024), False),
        (proposition("3", 2024), None), (proposition("4", 2024, "REQ"), True),
        (proposition("5", 2023), True), (proposition("1", 2024, house="Senado"), False),
    ])
    summary = annual_summary(rows, kinds=("pl",), start_year=2024, end_year=2024)
    assert len(summary) == 2
    camara, senado = summary
    assert camara == dict(house="Câmara", year=2024, total=3, climatic=1,
                         not_identified=1, pending=1, attention_pct=None, identified_pct=100 / 3)
    assert senado["total"] == 1 and senado["attention_pct"] == 0
    reviewed = tuple(review_proposition(row, True) if row.automatic is None else row for row in rows)
    assert annual_summary(reviewed, kinds=("PL",), start_year=2024)[0]["attention_pct"] == pytest.approx(200 / 3)
    assert annual_summary((), kinds=("PL",)) == []


@pytest.mark.parametrize("options", [{"start_year": 2025, "end_year": 2024}, {"start_year": 0},
                                     {"start_year": True}, {"end_year": 2024.0}, {"kinds": ("",)}])
def test_invalid_summary_filters_fail(options):
    with pytest.raises(ValueError):
        annual_summary((), **options)


def test_summary_rejects_duplicate_records_instead_of_double_counting():
    row = ClassifiedProposition(proposition(), True, ())
    with pytest.raises(ValueError, match="duplicad"):
        annual_summary((row, row))


def test_cancel_import_dedup_and_classification(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("id;ano;tipo;ementa;keywords\n1;2024;PL;clima;\n", encoding="utf-8")
    callbacks = [lambda: load_propositions(path, mapping(), cancel_check=lambda: True),
                 lambda: deduplicate_propositions((proposition(),), cancel_check=lambda: True),
                 lambda: classify_propositions((proposition(),), "clima", cancel_check=lambda: True)]
    for callback in callbacks:
        with pytest.raises(InterruptedError, match="cancelado"):
            callback()
