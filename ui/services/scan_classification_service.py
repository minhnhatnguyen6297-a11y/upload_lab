from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Protocol

from playwright_uploader import normalize_contract_no_for_compare
from ui.services.contract_book_audit import ContractBookAnalysis, parse_contract_book_no


class _ScanRecord(Protocol):
    record_id: int
    contract_no: str
    status: str
    source_file: object
    missing_fields: list[str]


@dataclass(frozen=True)
class FolderScanRow:
    record_id: int
    contract_no: str
    normalized_contract_no: str
    status: str
    source_file: str
    missing_fields: list[str]
    selected: bool
    note: str
    has_issue: bool = False


@dataclass(frozen=True)
class ScanClassification:
    folder_rows: list[FolderScanRow]
    missing_in_excel_record_ids: set[int]
    has_excel: bool


def _canonical_contract_no(value: str) -> str:
    normalized = normalize_contract_no_for_compare(value)
    match = re.fullmatch(r"0*(\d+)/(\d{4})", normalized)
    if match:
        return f"{int(match.group(1))}/{match.group(2)}"
    return normalized


def _excel_contract_nos(contract_book: ContractBookAnalysis | None) -> set[str]:
    if contract_book is None:
        return set()
    return {_canonical_contract_no(row.contract_no) for row in contract_book.valid_rows}


def _allowed_years(contract_book: ContractBookAnalysis | None) -> set[int]:
    if contract_book is None:
        return set()
    return {int(row.year) for row in contract_book.valid_rows}


def _folder_contract_issue(raw_contract_no: str, *, allowed_years: set[int]) -> str:
    text = str(raw_contract_no or "").strip()
    if not text:
        return "khong co so"
    loose_year_match = re.search(r"/\s*(\d{4})\b", text)
    if loose_year_match and allowed_years and int(loose_year_match.group(1)) not in allowed_years:
        return "sai nam"
    if parse_contract_book_no(text) is None:
        return "sai format"
    if not re.fullmatch(r"\s*\d+/\d{4}/CCGD\s*", text, flags=re.IGNORECASE):
        return "sai format"
    normalized = _canonical_contract_no(text)
    match = re.fullmatch(r"(\d+)/(\d{4})", normalized)
    if match and allowed_years and int(match.group(2)) not in allowed_years:
        return "sai nam"
    return ""


def classify_scan_records(
    records: Iterable[_ScanRecord],
    contract_book: ContractBookAnalysis | None,
) -> ScanClassification:
    record_list = list(records)
    excel_contract_nos = _excel_contract_nos(contract_book)
    allowed_years = _allowed_years(contract_book)
    has_excel = contract_book is not None

    counts_by_contract_no: dict[str, int] = {}
    for record in record_list:
        normalized = _canonical_contract_no(record.contract_no)
        if normalized:
            counts_by_contract_no[normalized] = counts_by_contract_no.get(normalized, 0) + 1

    folder_rows: list[FolderScanRow] = []
    missing_in_excel_record_ids: set[int] = set()
    for record in record_list:
        normalized = _canonical_contract_no(record.contract_no)
        missing_fields = list(record.missing_fields or [])
        notes: list[str] = []
        selected = False
        issue = _folder_contract_issue(record.contract_no, allowed_years=allowed_years)

        if issue:
            notes.append(issue)
        elif has_excel:
            if normalized in excel_contract_nos:
                notes.append("da co trong Excel")
            else:
                notes.append("chua co trong Excel")
                selected = True
                missing_in_excel_record_ids.add(int(record.record_id))
        else:
            notes.append("chua load Excel")

        if missing_fields:
            notes.append("missing: " + ", ".join(missing_fields))
        if normalized and counts_by_contract_no.get(normalized, 0) > 1:
            notes.append("trung trong folder")

        folder_rows.append(
            FolderScanRow(
                record_id=int(record.record_id),
                contract_no=str(record.contract_no),
                normalized_contract_no=normalized,
                status=str(record.status),
                source_file=str(record.source_file),
                missing_fields=missing_fields,
                selected=selected,
                note="; ".join(notes),
                has_issue=bool(issue),
            )
        )

    return ScanClassification(
        folder_rows=folder_rows,
        missing_in_excel_record_ids=missing_in_excel_record_ids,
        has_excel=has_excel,
    )
