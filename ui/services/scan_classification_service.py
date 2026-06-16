from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Protocol

from ui.services.contract_book_audit import ContractBookAnalysis
from playwright_uploader import normalize_contract_no_for_compare


class _ScanRecord(Protocol):
    record_id: int
    contract_no: str
    status: str
    source_file: object
    missing_fields: list[str]


@dataclass(frozen=True)
class ClassifiedScanRow:
    record_id: int
    contract_no: str
    status: str
    source_file: str
    missing_fields: list[str]
    selected: bool


@dataclass(frozen=True)
class ScanClassification:
    valid_upload_rows: list[ClassifiedScanRow]
    not_in_excel_rows: list[ClassifiedScanRow]
    missing_field_rows: list[ClassifiedScanRow]
    web_duplicate_rows: list[ClassifiedScanRow]
    duplicate_local_rows: list[ClassifiedScanRow]
    excel_missing_in_folder: list[str]


def _make_row(record: _ScanRecord, *, contract_no: str, selected: bool) -> ClassifiedScanRow:
    return ClassifiedScanRow(
        record_id=int(record.record_id),
        contract_no=contract_no,
        status=str(record.status),
        source_file=str(record.source_file),
        missing_fields=list(record.missing_fields or []),
        selected=selected,
    )


def _sort_contract_no(value: str) -> tuple[int, int, str]:
    match = re.fullmatch(r"(\d+)/(\d{4})", str(value or "").strip())
    if match:
        return int(match.group(2)), int(match.group(1)), value
    return (0, 0, value)


def _canonical_contract_no(value: str) -> str:
    normalized = normalize_contract_no_for_compare(value)
    match = re.fullmatch(r"0*(\d+)/(\d{4})", normalized)
    if match:
        return f"{int(match.group(1))}/{match.group(2)}"
    return normalized


def classify_scan_records(
    records: Iterable[_ScanRecord],
    contract_book: ContractBookAnalysis,
    *,
    existing_web_contract_nos: set[str],
) -> ScanClassification:
    excel_contract_nos = {_canonical_contract_no(row.contract_no) for row in contract_book.valid_rows}
    web_contract_nos = {_canonical_contract_no(value) for value in existing_web_contract_nos}
    valid_rows: list[ClassifiedScanRow] = []
    not_in_excel_rows: list[ClassifiedScanRow] = []
    missing_field_rows: list[ClassifiedScanRow] = []
    web_duplicate_rows: list[ClassifiedScanRow] = []
    duplicate_local_rows: list[ClassifiedScanRow] = []
    seen_non_empty_contract_nos: set[str] = set()
    found_excel_contract_nos: set[str] = set()

    for record in records:
        normalized_contract_no = _canonical_contract_no(record.contract_no)
        row = _make_row(record, contract_no=normalized_contract_no, selected=False)

        if normalized_contract_no:
            if normalized_contract_no in seen_non_empty_contract_nos:
                duplicate_local_rows.append(row)
                continue
            seen_non_empty_contract_nos.add(normalized_contract_no)

        if normalized_contract_no in excel_contract_nos:
            found_excel_contract_nos.add(normalized_contract_no)
            if normalized_contract_no in web_contract_nos:
                web_duplicate_rows.append(row)
                continue
        elif normalized_contract_no in web_contract_nos:
            web_duplicate_rows.append(row)
            continue

        if normalized_contract_no not in excel_contract_nos:
            not_in_excel_rows.append(row)
            continue

        if list(record.missing_fields or []):
            missing_field_rows.append(row)
            continue

        valid_rows.append(
            ClassifiedScanRow(
                record_id=row.record_id,
                contract_no=row.contract_no,
                status=row.status,
                source_file=row.source_file,
                missing_fields=row.missing_fields,
                selected=True,
            )
        )

    excel_missing_in_folder = sorted(
        (contract_no for contract_no in excel_contract_nos if contract_no not in found_excel_contract_nos),
        key=_sort_contract_no,
    )

    return ScanClassification(
        valid_upload_rows=valid_rows,
        not_in_excel_rows=not_in_excel_rows,
        missing_field_rows=missing_field_rows,
        web_duplicate_rows=web_duplicate_rows,
        duplicate_local_rows=duplicate_local_rows,
        excel_missing_in_folder=excel_missing_in_folder,
    )
