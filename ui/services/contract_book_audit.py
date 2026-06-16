from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
import re
import unicodedata


class ContractBookWarningKind(str, Enum):
    PARSE_ERROR = "parse_error"
    DATE_PARSE_ERROR = "date_parse_error"
    DATE_ORDER = "date_order"
    ORDINAL_ORDER = "ordinal_order"
    YEAR_MISMATCH = "year_mismatch"


@dataclass(frozen=True)
class ContractBookRow:
    row_index: int
    raw_contract_no: str
    raw_date: str
    contract_no: str
    year: int
    ordinal: int
    contract_date: date | None = None


@dataclass(frozen=True)
class MissingContractNumber:
    year: int
    ordinal: int
    contract_no: str


@dataclass(frozen=True)
class ContractBookWarning:
    row_index: int
    kind: ContractBookWarningKind
    raw_contract_no: str
    raw_date: str
    message: str


@dataclass(frozen=True)
class ContractBookAnalysis:
    source_path: Path
    valid_rows: list[ContractBookRow]
    missing_numbers: list[MissingContractNumber]
    parse_error_rows: list[ContractBookWarning]
    warning_rows: list[ContractBookWarning]
    min_ordinal: int | None
    max_ordinal: int | None


def _fold_text(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    normalized = normalized.replace("\u0111", "d").replace("\u0110", "D")
    folded = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return folded.upper()


def _header_key(value: object) -> str:
    return re.sub(r"[^A-Z]", "", _fold_text(value))


def _stringify_cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_contract_book_no(value: object, *, default_year: int | None = None) -> tuple[int, int, str] | None:
    text = re.sub(r"\s+", "", _fold_text(value))
    if not text:
        return None

    direct_match = re.fullmatch(r"0*(\d+)", text)
    if direct_match:
        if default_year is None:
            return None
        ordinal = int(direct_match.group(1))
        return default_year, ordinal, f"{ordinal}/{default_year}"

    match = re.fullmatch(r"0*(\d+)[./](\d{4})(?:/[A-Z0-9]+)*(?:/CCGD)?", text)
    if not match:
        return None

    ordinal = int(match.group(1))
    year = int(match.group(2))
    return year, ordinal, f"{ordinal}/{year}"


def parse_contract_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _read_rows(path: Path) -> list[tuple[int, object, object]]:
    try:
        from openpyxl import load_workbook
    except Exception as exc:  # pragma: no cover - dependency wiring
        raise RuntimeError("Thieu openpyxl trong moi truong tool.") from exc

    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows = list(sheet.iter_rows(min_col=1, max_col=2, values_only=True))
    finally:
        workbook.close()

    start_index = 1
    if rows:
        header_a = _header_key(rows[0][0])
        if "SOCONGCHUNG" in header_a:
            start_index = 2

    return [
        (row_index, row[0], row[1])
        for row_index, row in enumerate(rows[start_index - 1 :], start=start_index)
    ]


def _build_missing_numbers(rows: list[ContractBookRow]) -> list[MissingContractNumber]:
    ordinals_by_year: dict[int, set[int]] = {}
    for row in rows:
        ordinals_by_year.setdefault(row.year, set()).add(row.ordinal)

    missing: list[MissingContractNumber] = []
    for year in sorted(ordinals_by_year):
        ordinals = ordinals_by_year[year]
        if len(ordinals) < 2:
            continue
        for ordinal in range(min(ordinals), max(ordinals) + 1):
            if ordinal not in ordinals:
                missing.append(
                    MissingContractNumber(
                        year=year,
                        ordinal=ordinal,
                        contract_no=f"{ordinal}/{year}",
                    )
                )
    return missing


def analyze_contract_book(export_path: Path | str) -> ContractBookAnalysis:
    path = Path(export_path)
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file Excel: {path}")

    valid_rows: list[ContractBookRow] = []
    warning_rows: list[ContractBookWarning] = []
    previous_date: date | None = None
    previous_ordinal_by_year: dict[int, int] = {}

    for row_index, raw_contract_no, raw_date in _read_rows(path):
        raw_contract_text = _stringify_cell_value(raw_contract_no)
        raw_date_text = _stringify_cell_value(raw_date)

        if not raw_contract_text and not raw_date_text:
            continue

        contract_date = parse_contract_date(raw_date)
        parsed = parse_contract_book_no(raw_contract_no, default_year=contract_date.year if contract_date else None)
        if not parsed:
            warning_rows.append(
                ContractBookWarning(
                    row_index=row_index,
                    kind=ContractBookWarningKind.PARSE_ERROR,
                    raw_contract_no=raw_contract_text,
                    raw_date=raw_date_text,
                    message="Khong parse duoc so cong chung cot A.",
                )
            )
            continue

        year, ordinal, contract_no = parsed
        valid_rows.append(
            ContractBookRow(
                row_index=row_index,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                contract_no=contract_no,
                year=year,
                ordinal=ordinal,
                contract_date=contract_date,
            )
        )

        if contract_date is None:
            warning_rows.append(
                ContractBookWarning(
                    row_index=row_index,
                    kind=ContractBookWarningKind.DATE_PARSE_ERROR,
                    raw_contract_no=raw_contract_text,
                    raw_date=raw_date_text,
                    message="Khong parse duoc ngay cot B theo dd/mm/yyyy.",
                )
            )
        else:
            if previous_date is not None and contract_date < previous_date:
                warning_rows.append(
                    ContractBookWarning(
                        row_index=row_index,
                        kind=ContractBookWarningKind.DATE_ORDER,
                        raw_contract_no=raw_contract_text,
                        raw_date=raw_date_text,
                        message="Ngay cot B bi lui so voi dong truoc.",
                    )
                )
            if year != contract_date.year:
                warning_rows.append(
                    ContractBookWarning(
                        row_index=row_index,
                        kind=ContractBookWarningKind.YEAR_MISMATCH,
                        raw_contract_no=raw_contract_text,
                        raw_date=raw_date_text,
                        message="Nam trong so cong chung khac nam cua ngay cot B.",
                    )
                )
            previous_date = contract_date

        previous_ordinal = previous_ordinal_by_year.get(year)
        if previous_ordinal is not None and ordinal < previous_ordinal:
            warning_rows.append(
                ContractBookWarning(
                    row_index=row_index,
                    kind=ContractBookWarningKind.ORDINAL_ORDER,
                    raw_contract_no=raw_contract_text,
                    raw_date=raw_date_text,
                    message="So cong chung bi lui so voi dong truoc.",
                )
            )
        previous_ordinal_by_year[year] = ordinal

    missing_numbers = _build_missing_numbers(valid_rows)
    ordinals = [row.ordinal for row in valid_rows]
    parse_error_rows = [warning for warning in warning_rows if warning.kind == ContractBookWarningKind.PARSE_ERROR]
    return ContractBookAnalysis(
        source_path=path,
        valid_rows=valid_rows,
        missing_numbers=missing_numbers,
        parse_error_rows=parse_error_rows,
        warning_rows=warning_rows,
        min_ordinal=min(ordinals) if ordinals else None,
        max_ordinal=max(ordinals) if ordinals else None,
    )
