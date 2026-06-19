from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ui.services.contract_book_audit import analyze_contract_book
from playwright_uploader import normalize_contract_no_for_compare


@dataclass(frozen=True)
class ContractListRow:
    row_index: int
    raw_value: str
    contract_no: str
    year: int
    ordinal: int


@dataclass(frozen=True)
class MissingContractNo:
    year: int
    ordinal: int
    contract_no: str


@dataclass(frozen=True)
class ContractLookupResult:
    found: bool
    query: str
    contract_no: str = ""
    row_index: int | None = None
    raw_value: str = ""
    message: str = ""

def read_exported_contract_rows(
    export_path: Path | str,
    *,
    from_date: str,
    to_date: str,
) -> list[ContractListRow]:
    analysis = analyze_contract_book(export_path, from_date=from_date, to_date=to_date)
    return [
        ContractListRow(
            row_index=row.row_index,
            raw_value=row.raw_contract_no,
            contract_no=row.contract_no,
            year=row.year,
            ordinal=row.ordinal,
        )
        for row in analysis.display_rows
    ]


def find_missing_contract_numbers(rows: list[ContractListRow]) -> list[MissingContractNo]:
    ordinals_by_year: dict[int, set[int]] = {}
    for row in rows:
        ordinals_by_year.setdefault(row.year, set()).add(row.ordinal)

    missing: list[MissingContractNo] = []
    for year in sorted(ordinals_by_year):
        ordinals = ordinals_by_year[year]
        if len(ordinals) < 2:
            continue
        for ordinal in range(min(ordinals), max(ordinals) + 1):
            if ordinal not in ordinals:
                missing.append(
                    MissingContractNo(
                        year=year,
                        ordinal=ordinal,
                        contract_no=f"{ordinal}/{year}",
                    )
                )
    return missing


def lookup_exported_contract_no(rows: list[ContractListRow], query: str) -> ContractLookupResult:
    normalized = normalize_contract_no_for_compare(query)
    if not normalized:
        return ContractLookupResult(found=False, query=query, message="So cong chung khong hop le.")

    for row in rows:
        if row.contract_no == normalized:
            return ContractLookupResult(
                found=True,
                query=query,
                contract_no=row.contract_no,
                row_index=row.row_index,
                raw_value=row.raw_value,
                message=f"Tim thay dong {row.row_index}.",
            )
    return ContractLookupResult(found=False, query=query, contract_no=normalized, message="Khong tim thay.")
