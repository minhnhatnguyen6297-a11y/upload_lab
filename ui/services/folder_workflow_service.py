from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from batch_scan import BASE_DIR, finalize_manifest, run_batch_scan
from extract_contract import extract
from playwright_uploader import (
    finalize_uploaded_records,
    load_upload_queue,
    read_exported_contract_numbers,
    split_records_by_existing_contract_nos,
)


@dataclass(frozen=True)
class QueueState:
    manifest: dict
    rows: list[dict]
    duplicate_rows: list[dict]
    total_pending: int
    existing_contract_nos: set[str]


def run_folder_scan(
    folder_path: Path,
    *,
    modified_since: str | None,
    full_rescan: bool,
    progress_callback=None,
    working_dir: Path = BASE_DIR,
) -> tuple[dict, Path]:
    manifest = run_batch_scan(
        folder_path,
        modified_since=modified_since,
        full_rescan=full_rescan,
        working_dir=working_dir,
        progress_callback=progress_callback,
    )
    manifest_path = finalize_manifest(manifest, working_dir / "runs")
    return manifest, manifest_path


def extract_one_file(file_path: Path) -> tuple[dict, Path]:
    payload = extract(file_path)
    output_path = file_path.with_name(f"{file_path.stem}_extracted.json")
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload, output_path


def records_to_rows(records, *, include_missing: bool = True) -> list[dict]:
    rows: list[dict] = []
    for record in records:
        rows.append(
            {
                "record_id": str(record.record_id),
                "contract_no": record.contract_no,
                "status": record.status,
                "missing": ", ".join(record.missing_fields) if include_missing and record.missing_fields else "",
                "source_file": str(record.source_file),
            }
        )
    return rows


def load_queue_state(
    manifest_path: Path,
    *,
    export_path: Path | None = None,
    working_dir: Path = BASE_DIR,
    cong_chung_vien: str | None = None,
    thu_ky: str | None = None,
) -> QueueState:
    manifest, records, total_pending = load_upload_queue(
        manifest_path,
        working_dir=working_dir,
        cong_chung_vien=cong_chung_vien,
        thu_ky=thu_ky,
    )
    existing_contract_nos: set[str] = set()
    if export_path and export_path.exists():
        existing_contract_nos = read_exported_contract_numbers(export_path)
    filtered_records, duplicate_records = split_records_by_existing_contract_nos(records, existing_contract_nos)
    return QueueState(
        manifest=manifest,
        rows=records_to_rows(filtered_records),
        duplicate_rows=records_to_rows(duplicate_records, include_missing=False),
        total_pending=total_pending,
        existing_contract_nos=existing_contract_nos,
    )


def load_selected_queue_records(
    manifest_path: Path,
    selected_record_ids: set[int],
    *,
    working_dir: Path = BASE_DIR,
    cong_chung_vien: str | None = None,
    thu_ky: str | None = None,
):
    return load_upload_queue(
        manifest_path,
        working_dir=working_dir,
        selected_record_ids=selected_record_ids,
        cong_chung_vien=cong_chung_vien,
        thu_ky=thu_ky,
    )


def finalize_selected_records(record_ids: list[int], *, working_dir: Path = BASE_DIR) -> int:
    return finalize_uploaded_records(record_ids, working_dir=working_dir)
