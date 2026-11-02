"""Offline legislative CSV import and auditable annual attention indicators."""

import codecs
import csv
import re
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Callable, Optional, Sequence


@dataclass(frozen=True)
class CsvMapping:
    id_column: str
    year_column: str
    type_column: str
    text_columns: tuple[str, ...]
    house: str
    year_is_date: bool = False


@dataclass(frozen=True)
class Proposition:
    identifier: str
    house: str
    year: int
    kind: str
    texts: tuple[tuple[str, str], ...]
    source_file: str
    text_origins: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ImportResult:
    propositions: tuple[Proposition, ...]
    duplicate_count: int


@dataclass(frozen=True)
class ClassifiedProposition:
    proposition: Proposition
    automatic: Optional[bool]
    evidence: tuple
    review: Optional[bool] = None
    note: str = ""

    @property
    def climatic(self) -> Optional[bool]:
        return self.review if self.review is not None else self.automatic


def _encodings(encoding: str) -> tuple[str, ...]:
    if encoding == "auto":
        return ("utf-8-sig", "cp1252")
    try:
        codecs.lookup(encoding)
    except (LookupError, TypeError) as error:
        raise ValueError("Codificação de caracteres inválida.") from error
    return (encoding,)


def _delimiter(sample: str, delimiter: str) -> str:
    if delimiter != "auto":
        if delimiter not in (";", ",", "\t"):
            raise ValueError("Separador CSV deve ser ponto e vírgula, vírgula ou tabulação.")
        return delimiter
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        header = sample.splitlines()[0] if sample.splitlines() else ""
        return max((";", ",", "\t"), key=header.count)


@contextmanager
def _reader(path, encoding: str, delimiter: str):
    try:
        with Path(path).open("r", encoding=encoding, newline="") as handle:
            sample = handle.read(65536)
            handle.seek(0)
            sep = _delimiter(sample, delimiter)
            reader = csv.reader(handle, delimiter=sep, strict=True)
            headers = next(reader, None)
            if not headers:
                raise ValueError("Arquivo CSV vazio: falta o cabeçalho.")
            if any(not name.strip() for name in headers):
                raise ValueError("CSV contém coluna sem nome no cabeçalho.")
            if len(headers) != len(set(headers)):
                raise ValueError("CSV contém cabeçalhos duplicados.")
            yield headers, reader, sep
    except csv.Error as error:
        raise ValueError(f"CSV inválido em {Path(path).name}: {error}") from error


def _row_dict(headers, row, line: int) -> dict[str, str]:
    if len(row) != len(headers):
        raise ValueError(f"Linha {line}: número de colunas difere do cabeçalho.")
    return {name: value.replace("\r\n", "\n").replace("\r", "\n")
            for name, value in zip(headers, row)}


def _preview(path, encoding: str, delimiter: str) -> dict:
    with _reader(path, encoding, delimiter) as (headers, reader, sep):
        rows = []
        for row in reader:
            if row:
                rows.append(_row_dict(headers, row, reader.line_num))
            if len(rows) == 5:
                break
        return dict(headers=headers, rows=rows, encoding=encoding, delimiter=sep)


def preview_csv(path, encoding: str = "auto", delimiter: str = "auto") -> dict:
    """Read the header and at most five records; decoding always stays strict."""
    for candidate in _encodings(encoding):
        try:
            return _preview(path, candidate, delimiter)
        except UnicodeError:
            continue
    raise ValueError("CSV não pôde ser decodificado. Selecione UTF-8 ou Windows-1252.")


def _validate_mapping(mapping: CsvMapping, headers: Sequence[str]) -> None:
    keys = (mapping.id_column, mapping.year_column, mapping.type_column)
    if not isinstance(mapping.house, str) or not mapping.house.strip():
        raise ValueError("Selecione a Casa legislativa.")
    if len(set(keys)) != 3:
        raise ValueError("Identificador, ano/data e tipo devem usar colunas diferentes.")
    if not mapping.text_columns or len(set(mapping.text_columns)) != len(mapping.text_columns):
        raise ValueError("Selecione ao menos uma coluna textual, sem repetições.")
    if not isinstance(mapping.year_is_date, bool):
        raise ValueError("Informe se a coluna contém ano ou data de apresentação.")
    missing = [name for name in (*keys, *mapping.text_columns) if name not in headers]
    if missing:
        raise ValueError("Colunas mapeadas ausentes: " + ", ".join(missing))


def _year(value: str, is_date: bool, line: int) -> int:
    value = value.strip()
    if not is_date:
        if not re.fullmatch(r"[0-9]{1,4}", value) or not 1 <= int(value) <= 9999:
            raise ValueError(f"Linha {line}: ano inválido: {value!r}.")
        return int(value)
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ][0-9].*)?", value):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).year
        except ValueError:
            pass
    for pattern in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        if not re.match(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}(?: |$)", value):
            continue
        try:
            return datetime.strptime(value, pattern).year
        except ValueError:
            continue
    raise ValueError(f"Linha {line}: data inválida: {value!r}. Use AAAA-MM-DD ou DD/MM/AAAA.")


def _proposition(row, mapping: CsvMapping, path, line: int) -> Proposition:
    identifier = row[mapping.id_column].strip()
    kind = row[mapping.type_column].strip().upper()
    if not identifier:
        raise ValueError(f"Linha {line}: identificador vazio.")
    if not kind:
        raise ValueError(f"Linha {line}: tipo de proposição vazio.")
    return Proposition(
        identifier=identifier, house=mapping.house.strip(),
        year=_year(row[mapping.year_column], mapping.year_is_date, line), kind=kind,
        texts=tuple((column, row[column].strip()) for column in mapping.text_columns),
        source_file=str(Path(path).resolve()),
    )


def _check_cancel(cancel_check: Optional[Callable[[], bool]]) -> None:
    if cancel_check is not None and cancel_check():
        raise InterruptedError("Processamento cancelado.")


def _load(path, mapping: CsvMapping, encoding: str, delimiter: str, cancel_check) -> ImportResult:
    with _reader(path, encoding, delimiter) as (headers, reader, _):
        _validate_mapping(mapping, headers)
        propositions = []
        for row in reader:
            _check_cancel(cancel_check)
            if row:
                data = _row_dict(headers, row, reader.line_num)
                propositions.append(_proposition(data, mapping, path, reader.line_num))
        return deduplicate_propositions(propositions, cancel_check=cancel_check)


def load_propositions(path, mapping: CsvMapping, encoding: str = "auto",
                      delimiter: str = "auto", *, cancel_check: Optional[Callable[[], bool]] = None) -> ImportResult:
    """Import a complete selected universe; invalid records fail the import."""
    for candidate in _encodings(encoding):
        _check_cancel(cancel_check)
        try:
            return _load(path, mapping, candidate, delimiter, cancel_check)
        except UnicodeError:
            continue
    raise ValueError("CSV não pôde ser decodificado. Selecione UTF-8 ou Windows-1252.")


def _merge_texts(first: Proposition, second: Proposition) -> tuple:
    # A phrase must never span text versions from different CSV records.
    fields = dict(first.texts)
    first_origins = dict(first.text_origins)
    origins = {field: first_origins.get(field, field) for field in fields}
    incoming_origins = dict(second.text_origins)
    reserved = set(fields) | {incoming_origins.get(field, field) for field, _ in second.texts}
    for field, text in second.texts:
        origin = incoming_origins.get(field, field)
        versions = [value for name, value in fields.items() if origins[name] == origin]
        if text in versions or (not text and versions):
            continue
        label = origin
        version = 2
        while label in fields:
            label = f"{origin} [versão {version}]"
            version += 1
            if label in reserved:
                label = origin
        fields = fields | {label: text}
        origins = origins | {label: origin}
    return tuple(fields.items()), tuple(origins.items())


def deduplicate_propositions(propositions: Sequence[Proposition], *,
                             cancel_check: Optional[Callable[[], bool]] = None) -> ImportResult:
    """Count each (Casa, identifier) once, retaining distinct text and sources."""
    unique = {}
    duplicates = 0
    for item in propositions:
        _check_cancel(cancel_check)
        key = (item.house, item.identifier)
        if key not in unique:
            unique[key] = item
            continue
        previous = unique[key]
        if (previous.year, previous.kind) != (item.year, item.kind):
            raise ValueError(f"Duplicata conflitante: {item.house}, ID {item.identifier}; ano ou tipo divergem.")
        sources = tuple(dict.fromkeys((*previous.source_file.split("; "), *item.source_file.split("; "))))
        texts, origins = _merge_texts(previous, item)
        unique[key] = replace(previous, texts=texts, text_origins=origins, source_file="; ".join(sources))
        duplicates += 1
    return ImportResult(tuple(unique.values()), duplicates)


def classify_propositions(propositions: Sequence[Proposition], expression: str, *,
                          cancel_check: Optional[Callable[[], bool]] = None) -> tuple[ClassifiedProposition, ...]:
    from .boolean_search import compile_query

    query = compile_query(expression)
    results = []
    for item in propositions:
        _check_cancel(cancel_check)
        fields = dict(item.texts)
        if not any(text.strip() for text in fields.values()):
            results.append(ClassifiedProposition(item, None, ()))
        else:
            match = query.match(fields)
            results.append(ClassifiedProposition(item, match.matched, match.evidence))
    return tuple(results)


def review_proposition(result: ClassifiedProposition, decision: Optional[bool],
                       note: str = "") -> ClassifiedProposition:
    if decision is not None and not isinstance(decision, bool):
        raise ValueError("Revisão deve ser sim, não ou restauração da classificação automática.")
    if not isinstance(note, str):
        raise ValueError("Observação da revisão deve ser texto.")
    return replace(result, review=decision, note=note.strip())


def _validate_filters(kinds: Sequence[str], start_year, end_year) -> tuple[str, ...]:
    for year in (start_year, end_year):
        if year is not None and (type(year) is not int or not 1 <= year <= 9999):
            raise ValueError("Ano do filtro deve ser inteiro entre 1 e 9999.")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError("Ano inicial não pode superar o ano final.")
    if isinstance(kinds, str) or any(not isinstance(kind, str) or not kind.strip() for kind in kinds):
        raise ValueError("Tipos devem formar uma lista de siglas não vazias.")
    return tuple(kind.strip().upper() for kind in kinds)


def _summary(house: str, year: int, rows: Sequence[ClassifiedProposition]) -> dict:
    total = len(rows)
    climatic = sum(row.climatic is True for row in rows)
    pending = sum(row.climatic is None for row in rows)
    identified = 100 * climatic / total
    return dict(house=house, year=year, total=total, climatic=climatic,
                not_identified=total - climatic - pending, pending=pending,
                attention_pct=None if pending else identified, identified_pct=identified)


def annual_summary(results: Sequence[ClassifiedProposition], kinds: Sequence[str] = (),
                   start_year: Optional[int] = None, end_year: Optional[int] = None) -> list[dict]:
    """Use one denominator per Casa/year; pending records prevent a final share."""
    accepted = _validate_filters(kinds, start_year, end_year)
    selected = []
    seen = set()
    for row in results:
        item = row.proposition
        key = (item.house, item.identifier)
        if key in seen:
            raise ValueError(f"Resultado duplicado: {item.house}, ID {item.identifier}.")
        seen.add(key)
        if accepted and item.kind.upper() not in accepted:
            continue
        if start_year is not None and item.year < start_year:
            continue
        if end_year is not None and item.year > end_year:
            continue
        selected.append(row)
    grouped = groupby(sorted(selected, key=lambda row: (row.proposition.house, row.proposition.year)),
                      key=lambda row: (row.proposition.house, row.proposition.year))
    return [_summary(house, year, tuple(rows)) for (house, year), rows in grouped]
