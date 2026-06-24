# Qt Workflow Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6/Qt desktop workflow that loads the web Excel list, flags missing/suspicious contract numbers, scans one selected folder, shows all result groups, preselects valid files, and uploads only selected rows.

**Architecture:** Keep extraction/upload logic in existing backend modules and add small service modules for Excel auditing, scan classification, and upload selection. Add a Qt UI layer under `ui_qt/` that loads `.ui` files and calls those services; do not rewrite regex extraction or Playwright upload behavior.

**Tech Stack:** Python 3.10+, PySide6, Qt Designer `.ui` files, `openpyxl`, existing `batch_scan.py`, `extract_contract.py`, `playwright_uploader.py`, and `unittest`.

---

## File Structure

- Create `ui/services/contract_book_audit.py`: parse Excel column A/B, normalize ordinals, find missing numbers, and return warning rows without modifying data.
- Modify `ui/services/web_list_service.py`: keep current public API, delegate richer analysis to `contract_book_audit.py` where useful.
- Create `ui/services/scan_classification_service.py`: classify scanned Word records against the Excel analysis and web list into UI result groups.
- Create `ui/services/upload_selection_service.py`: maintain selected record IDs, default-select valid records, and protect invalid rows from "select all valid".
- Create `ui_qt/__init__.py`: package marker.
- Create `ui_qt/app.py`: QApplication entrypoint and app bootstrap.
- Create `ui_qt/main_window.py`: Qt main window controller.
- Create `ui_qt/workers.py`: QThread workers for Excel load, folder scan, and upload prepare/finalize.
- Create `ui_qt/widgets.py`: reusable Qt table helpers, checkbox table behavior, and file-open helper.
- Create `ui_qt/forms/main_window.ui`: Qt Designer editable main window layout.
- Modify `ui_runner.py`: choose Qt app by default, with a narrow fallback option only if needed during migration.
- Modify `requirements.txt`: add `PySide6`.
- Modify `bootstrap_ui.py`: include PySide6 in dependency probe.
- Modify `build_standalone_release.ps1`: include `ui_qt/` and `.ui` files in release output.
- Create `docs/regex-rules.md`: systematic regex/rule catalog for future contract templates.
- Test `tests/test_contract_book_audit.py`.
- Test `tests/test_scan_classification_service.py`.
- Test `tests/test_upload_selection_service.py`.
- Test `tests/test_qt_ui_structure.py`.

---

### Task 1: Add Contract Book Audit Service

**Files:**
- Create: `ui/services/contract_book_audit.py`
- Test: `tests/test_contract_book_audit.py`

- [ ] **Step 1: Write failing tests for Excel parsing, missing range, and warnings**

Create `tests/test_contract_book_audit.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from ui.services.contract_book_audit import (
    ContractBookWarningKind,
    analyze_contract_book,
)


class ContractBookAuditTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def _make_book(self, rows: list[tuple[object, object]]) -> Path:
        path = self.root / "book.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SO CONG CHUNG"
        sheet["B1"] = "NGAY, THANG, NAM CONG CHUNG"
        for index, (contract_no, date_value) in enumerate(rows, start=2):
            sheet.cell(row=index, column=1).value = contract_no
            sheet.cell(row=index, column=2).value = date_value
        workbook.save(path)
        workbook.close()
        return path

    def test_analyze_contract_book_uses_min_to_max_ordinal_only(self):
        path = self._make_book([
            ("01/2026", "05/01/2026"),
            ("03/2026/CCGD", "05/01/2026"),
            ("5", "06/01/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertEqual([row.ordinal for row in analysis.valid_rows], [1, 3, 5])
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026", "4/2026"])
        self.assertEqual(analysis.min_ordinal, 1)
        self.assertEqual(analysis.max_ordinal, 5)

    def test_warns_for_unparseable_column_a(self):
        path = self._make_book([
            ("Nguyen Van A", "05/01/2026"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertEqual(len(analysis.parse_error_rows), 1)
        self.assertEqual(analysis.parse_error_rows[0].row_index, 2)
        self.assertEqual(analysis.parse_error_rows[0].raw_contract_no, "Nguyen Van A")

    def test_warns_when_contract_year_disagrees_with_date_year(self):
        path = self._make_book([
            ("10.2025", "05/02/2026"),
            ("11/2026", "06/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.YEAR_MISMATCH
            and warning.row_index == 2
            for warning in analysis.warning_rows
        ))

    def test_warns_when_date_order_goes_backwards(self):
        path = self._make_book([
            ("01/2026", "06/02/2026"),
            ("02/2026", "05/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.DATE_ORDER
            and warning.row_index == 3
            for warning in analysis.warning_rows
        ))

    def test_warns_when_ordinal_order_goes_backwards(self):
        path = self._make_book([
            ("05/2026", "05/02/2026"),
            ("04/2026", "05/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.ORDINAL_ORDER
            and warning.row_index == 3
            for warning in analysis.warning_rows
        ))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ui.services.contract_book_audit'`.

- [ ] **Step 3: Implement the audit service**

Create `ui/services/contract_book_audit.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
import re


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
    contract_date: date | None


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


def _header_key(value: object) -> str:
    return re.sub(r"[^A-Z]", "", str(value or "").upper())


def parse_contract_book_no(value: object, *, default_year: int | None = None) -> tuple[int, int, str] | None:
    text = re.sub(r"\s+", "", str(value or "").strip().upper())
    if not text:
        return None
    match = re.fullmatch(r"0*(\d+)(?:[./](\d{4}))?(?:/[A-Z0-9]+)*(?:/CCGD)?", text)
    if not match:
        return None
    ordinal = int(match.group(1))
    year_text = match.group(2)
    year = int(year_text) if year_text else int(default_year or 0)
    if not year:
        return None
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
            pass
    return None


def _read_rows(path: Path) -> list[tuple[int, object, object]]:
    try:
        from openpyxl import load_workbook
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Thieu openpyxl trong moi truong tool.") from exc

    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows: list[tuple[int, object, object]] = []
        for row_index, (contract_value, date_value) in enumerate(
            sheet.iter_rows(min_col=1, max_col=2, values_only=True),
            start=1,
        ):
            if row_index == 1 and "SOCONGCHUNG" in _header_key(contract_value):
                continue
            if contract_value in (None, "") and date_value in (None, ""):
                continue
            rows.append((row_index, contract_value, date_value))
        return rows
    finally:
        workbook.close()


def analyze_contract_book(export_path: Path | str) -> ContractBookAnalysis:
    path = Path(export_path)
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file Excel: {path}")

    valid_rows: list[ContractBookRow] = []
    parse_errors: list[ContractBookWarning] = []
    warnings: list[ContractBookWarning] = []
    previous_date: date | None = None
    previous_ordinal: int | None = None

    for row_index, raw_contract_no, raw_date in _read_rows(path):
        raw_contract_text = str(raw_contract_no or "").strip()
        raw_date_text = str(raw_date or "").strip()
        contract_date = parse_contract_date(raw_date)
        parsed = parse_contract_book_no(raw_contract_no, default_year=contract_date.year if contract_date else None)
        if not parsed:
            parse_errors.append(ContractBookWarning(
                row_index=row_index,
                kind=ContractBookWarningKind.PARSE_ERROR,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                message="Khong parse duoc so cong chung cot A.",
            ))
            continue

        year, ordinal, contract_no = parsed
        row = ContractBookRow(
            row_index=row_index,
            raw_contract_no=raw_contract_text,
            raw_date=raw_date_text,
            contract_no=contract_no,
            year=year,
            ordinal=ordinal,
            contract_date=contract_date,
        )
        valid_rows.append(row)

        if contract_date is None:
            warnings.append(ContractBookWarning(
                row_index=row_index,
                kind=ContractBookWarningKind.DATE_PARSE_ERROR,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                message="Khong parse duoc ngay cot B theo dd/mm/yyyy.",
            ))
        else:
            if previous_date and contract_date < previous_date:
                warnings.append(ContractBookWarning(
                    row_index=row_index,
                    kind=ContractBookWarningKind.DATE_ORDER,
                    raw_contract_no=raw_contract_text,
                    raw_date=raw_date_text,
                    message="Ngay cot B bi lui so voi dong truoc.",
                ))
            if year != contract_date.year:
                warnings.append(ContractBookWarning(
                    row_index=row_index,
                    kind=ContractBookWarningKind.YEAR_MISMATCH,
                    raw_contract_no=raw_contract_text,
                    raw_date=raw_date_text,
                    message="Nam trong so cong chung khac nam cua ngay cot B.",
                ))
            previous_date = contract_date

        if previous_ordinal is not None and ordinal < previous_ordinal:
            warnings.append(ContractBookWarning(
                row_index=row_index,
                kind=ContractBookWarningKind.ORDINAL_ORDER,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                message="So cong chung bi lui so voi dong truoc.",
            ))
        previous_ordinal = ordinal

    ordinals_by_year: dict[int, set[int]] = {}
    for row in valid_rows:
        ordinals_by_year.setdefault(row.year, set()).add(row.ordinal)

    missing: list[MissingContractNumber] = []
    for year in sorted(ordinals_by_year):
        ordinals = ordinals_by_year[year]
        if len(ordinals) < 2:
            continue
        for ordinal in range(min(ordinals), max(ordinals) + 1):
            if ordinal not in ordinals:
                missing.append(MissingContractNumber(year=year, ordinal=ordinal, contract_no=f"{ordinal}/{year}"))

    all_ordinals = [row.ordinal for row in valid_rows]
    return ContractBookAnalysis(
        source_path=path,
        valid_rows=valid_rows,
        missing_numbers=missing,
        parse_error_rows=parse_errors,
        warning_rows=warnings,
        min_ordinal=min(all_ordinals) if all_ordinals else None,
        max_ordinal=max(all_ordinals) if all_ordinals else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui/services/contract_book_audit.py tests/test_contract_book_audit.py
git commit -m "add contract book audit service"
```

---

### Task 2: Keep Web List API Compatible With Audit Service

**Files:**
- Modify: `ui/services/web_list_service.py`
- Test: `tests/test_web_list_service.py`

- [ ] **Step 1: Add compatibility tests**

Append to `tests/test_web_list_service.py`:

```python
    def test_read_exported_contract_rows_accepts_short_number_with_date_year(self):
        export_path = self.root / "short.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SO CONG CHUNG"
        sheet["B1"] = "NGAY"
        sheet["A2"] = "123"
        sheet["B2"] = "05/02/2026"
        workbook.save(export_path)
        workbook.close()

        rows = read_exported_contract_rows(export_path)

        self.assertEqual(rows[0].contract_no, "123/2026")
        self.assertEqual(rows[0].year, 2026)
        self.assertEqual(rows[0].ordinal, 123)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_web_list_service.WebListServiceTests.test_read_exported_contract_rows_accepts_short_number_with_date_year
```

Expected: FAIL because current service reads only column A and cannot infer year from column B.

- [ ] **Step 3: Update `web_list_service.py` to delegate to audit**

Replace the body of `read_exported_contract_rows` with:

```python
def read_exported_contract_rows(export_path: Path | str) -> list[ContractListRow]:
    from ui.services.contract_book_audit import analyze_contract_book

    analysis = analyze_contract_book(export_path)
    return [
        ContractListRow(
            row_index=row.row_index,
            raw_value=row.raw_contract_no,
            contract_no=row.contract_no,
            year=row.year,
            ordinal=row.ordinal,
        )
        for row in analysis.valid_rows
    ]
```

Keep `find_missing_contract_numbers` and `lookup_exported_contract_no` intact so existing UI code still works.

- [ ] **Step 4: Run web list tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_web_list_service
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui/services/web_list_service.py tests/test_web_list_service.py
git commit -m "reuse audit service for web list parsing"
```

---

### Task 3: Add Scan Classification Service

**Files:**
- Create: `ui/services/scan_classification_service.py`
- Test: `tests/test_scan_classification_service.py`

- [ ] **Step 1: Write failing classification tests**

Create `tests/test_scan_classification_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest

from ui.services.contract_book_audit import ContractBookAnalysis, ContractBookRow
from ui.services.scan_classification_service import classify_scan_records


@dataclass(frozen=True)
class FakeRecord:
    record_id: int
    contract_no: str
    status: str
    source_file: Path
    missing_fields: list[str]


class ScanClassificationServiceTests(unittest.TestCase):
    def _analysis(self) -> ContractBookAnalysis:
        rows = [
            ContractBookRow(2, "1/2026", "05/01/2026", "1/2026", 2026, 1, None),
            ContractBookRow(3, "2/2026", "05/01/2026", "2/2026", 2026, 2, None),
        ]
        return ContractBookAnalysis(Path("book.xlsx"), rows, [], [], [], 1, 2)

    def test_classifies_valid_match_and_defaults_selected(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "9/2026/CCGD", "extracted", Path("b.docx"), []),
                FakeRecord(12, "2/2026/CCGD", "extracted", Path("c.docx"), ["tai_san"]),
            ],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.valid_upload_rows], [10])
        self.assertEqual(result.valid_upload_rows[0].selected, True)
        self.assertEqual([row.record_id for row in result.not_in_excel_rows], [11])
        self.assertEqual([row.record_id for row in result.missing_field_rows], [12])

    def test_classifies_web_duplicates(self):
        result = classify_scan_records(
            [FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), [])],
            self._analysis(),
            existing_web_contract_nos={"1/2026"},
        )

        self.assertEqual([row.record_id for row in result.web_duplicate_rows], [10])
        self.assertEqual(result.valid_upload_rows, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scan_classification_service
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement classification service**

Create `ui/services/scan_classification_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from playwright_uploader import normalize_contract_no_for_compare
from ui.services.contract_book_audit import ContractBookAnalysis


class ScanRecordLike(Protocol):
    record_id: int
    contract_no: str
    status: str
    source_file: Path
    missing_fields: list[str]


@dataclass(frozen=True)
class ClassifiedScanRow:
    record_id: int
    contract_no: str
    normalized_contract_no: str
    status: str
    source_file: str
    missing_fields: tuple[str, ...]
    selected: bool
    reason: str


@dataclass(frozen=True)
class ScanClassification:
    valid_upload_rows: list[ClassifiedScanRow]
    not_in_excel_rows: list[ClassifiedScanRow]
    missing_field_rows: list[ClassifiedScanRow]
    web_duplicate_rows: list[ClassifiedScanRow]
    duplicate_local_rows: list[ClassifiedScanRow]
    excel_missing_in_folder: list[str]


def _row(record: ScanRecordLike, *, selected: bool, reason: str) -> ClassifiedScanRow:
    normalized = normalize_contract_no_for_compare(record.contract_no)
    return ClassifiedScanRow(
        record_id=int(record.record_id),
        contract_no=str(record.contract_no or ""),
        normalized_contract_no=normalized,
        status=str(record.status or ""),
        source_file=str(record.source_file),
        missing_fields=tuple(record.missing_fields or []),
        selected=selected,
        reason=reason,
    )


def classify_scan_records(
    records: Iterable[ScanRecordLike],
    contract_book: ContractBookAnalysis,
    *,
    existing_web_contract_nos: set[str],
) -> ScanClassification:
    excel_numbers = {row.contract_no for row in contract_book.valid_rows}
    seen: set[str] = set()
    found_excel_numbers: set[str] = set()
    valid: list[ClassifiedScanRow] = []
    not_in_excel: list[ClassifiedScanRow] = []
    missing_fields: list[ClassifiedScanRow] = []
    web_duplicates: list[ClassifiedScanRow] = []
    local_duplicates: list[ClassifiedScanRow] = []

    for record in records:
        normalized = normalize_contract_no_for_compare(record.contract_no)
        if normalized in seen:
            local_duplicates.append(_row(record, selected=False, reason="Trung so trong folder dang quet."))
            continue
        if normalized:
            seen.add(normalized)
        if normalized in existing_web_contract_nos:
            web_duplicates.append(_row(record, selected=False, reason="Da co trong danh sach web/export."))
            continue
        if normalized not in excel_numbers:
            not_in_excel.append(_row(record, selected=False, reason="So hop dong khong nam trong Excel."))
            continue
        found_excel_numbers.add(normalized)
        if record.missing_fields:
            missing_fields.append(_row(record, selected=False, reason="Thieu field bat buoc."))
            continue
        valid.append(_row(record, selected=True, reason="Hop le de upload."))

    return ScanClassification(
        valid_upload_rows=valid,
        not_in_excel_rows=not_in_excel,
        missing_field_rows=missing_fields,
        web_duplicate_rows=web_duplicates,
        duplicate_local_rows=local_duplicates,
        excel_missing_in_folder=sorted(excel_numbers - found_excel_numbers),
    )
```

- [ ] **Step 4: Run classification tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scan_classification_service
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui/services/scan_classification_service.py tests/test_scan_classification_service.py
git commit -m "classify scanned records for upload workflow"
```

---

### Task 4: Add Upload Selection Service

**Files:**
- Create: `ui/services/upload_selection_service.py`
- Test: `tests/test_upload_selection_service.py`

- [ ] **Step 1: Write failing selection tests**

Create `tests/test_upload_selection_service.py`:

```python
from __future__ import annotations

import unittest

from ui.services.scan_classification_service import ClassifiedScanRow
from ui.services.upload_selection_service import UploadSelection


def row(record_id: int, *, selected: bool = True) -> ClassifiedScanRow:
    return ClassifiedScanRow(
        record_id=record_id,
        contract_no=f"{record_id}/2026/CCGD",
        normalized_contract_no=f"{record_id}/2026",
        status="extracted",
        source_file=f"{record_id}.docx",
        missing_fields=(),
        selected=selected,
        reason="Hop le de upload.",
    )


class UploadSelectionServiceTests(unittest.TestCase):
    def test_defaults_to_valid_row_selection(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])

        self.assertEqual(selection.selected_record_ids(), [1, 2])

    def test_can_unselect_one_row(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])
        selection.set_selected(2, False)

        self.assertEqual(selection.selected_record_ids(), [1])

    def test_select_all_valid_does_not_include_invalid_ids(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])
        selection.set_selected(99, True)
        selection.select_all_valid()

        self.assertEqual(selection.selected_record_ids(), [1, 2])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_selection_service
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement selection service**

Create `ui/services/upload_selection_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from ui.services.scan_classification_service import ClassifiedScanRow


@dataclass
class UploadSelection:
    valid_ids: set[int]
    selected_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_valid_rows(cls, rows: list[ClassifiedScanRow]) -> "UploadSelection":
        valid_ids = {int(row.record_id) for row in rows}
        return cls(valid_ids=valid_ids, selected_ids=set(valid_ids))

    def set_selected(self, record_id: int, selected: bool) -> None:
        record_id = int(record_id)
        if record_id not in self.valid_ids:
            return
        if selected:
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def select_all_valid(self) -> None:
        self.selected_ids = set(self.valid_ids)

    def clear(self) -> None:
        self.selected_ids.clear()

    def selected_record_ids(self) -> list[int]:
        return sorted(self.selected_ids)
```

- [ ] **Step 4: Run selection tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_selection_service
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui/services/upload_selection_service.py tests/test_upload_selection_service.py
git commit -m "add upload selection model"
```

---

### Task 5: Add PySide6 Runtime Wiring

**Files:**
- Modify: `requirements.txt`
- Modify: `bootstrap_ui.py`
- Modify: `build_standalone_release.ps1`
- Test: `tests/test_qt_ui_structure.py`

- [ ] **Step 1: Write failing dependency/structure test**

Create `tests/test_qt_ui_structure.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class QtUIStructureTests(unittest.TestCase):
    def test_pyside6_dependency_declared(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("PySide6", requirements)

    def test_qt_package_files_exist(self):
        self.assertTrue(Path("ui_qt").is_dir())
        self.assertTrue(Path("ui_qt/forms/main_window.ui").exists())

    def test_pyside6_import_available_after_install(self):
        self.assertIsNotNone(importlib.util.find_spec("PySide6"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails before dependency install**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure
```

Expected: FAIL because `PySide6` and `ui_qt/` are not present yet.

- [ ] **Step 3: Add dependency and bootstrap probe**

Append to `requirements.txt`:

```text
PySide6
```

In `bootstrap_ui.py`, update every module probe list from:

```python
("docx", "dotenv", "playwright", "openpyxl")
```

to:

```python
("docx", "dotenv", "playwright", "openpyxl", "PySide6")
```

In `build_standalone_release.ps1`, include the `ui_qt` directory in the release copy list and preserve `.ui` files.

- [ ] **Step 4: Install dependencies**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: exit code 0.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt bootstrap_ui.py build_standalone_release.ps1 tests/test_qt_ui_structure.py
git commit -m "wire PySide6 runtime dependency"
```

---

### Task 6: Add Qt App Shell and Editable `.ui` Layout

**Files:**
- Create: `ui_qt/__init__.py`
- Create: `ui_qt/app.py`
- Create: `ui_qt/main_window.py`
- Create: `ui_qt/widgets.py`
- Create: `ui_qt/forms/main_window.ui`
- Modify: `tests/test_qt_ui_structure.py`

- [ ] **Step 1: Extend Qt structure tests**

Append to `tests/test_qt_ui_structure.py`:

```python
    def test_qt_entrypoint_imports(self):
        from ui_qt.app import run_qt_app
        from ui_qt.main_window import UploadLabMainWindow

        self.assertTrue(callable(run_qt_app))
        self.assertEqual(UploadLabMainWindow.__name__, "UploadLabMainWindow")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure.QtUIStructureTests.test_qt_entrypoint_imports
```

Expected: FAIL with missing `ui_qt` package.

- [ ] **Step 3: Create Qt package**

Create `ui_qt/__init__.py`:

```python
from __future__ import annotations
```

Create `ui_qt/widgets.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


def open_with_windows_default(path: str) -> bool:
    file_path = Path(path)
    if not file_path.exists() or not hasattr(os, "startfile"):
        return False
    os.startfile(str(file_path))  # type: ignore[attr-defined]
    return True


def set_table_rows(table: QTableWidget, headers: list[str], rows: list[list[str]]) -> None:
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
    table.resizeColumnsToContents()
```

Create `ui_qt/app.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

from batch_scan import BASE_DIR
from PySide6.QtWidgets import QApplication

from ui_qt.main_window import UploadLabMainWindow


def run_qt_app(*, working_dir: Path = BASE_DIR) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = UploadLabMainWindow(working_dir=working_dir)
    window.show()
    return int(app.exec())
```

Create `ui_qt/main_window.py` with a minimal loadable controller:

```python
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QWidget

from batch_scan import BASE_DIR


class UploadLabMainWindow(QMainWindow):
    def __init__(self, *, working_dir: Path = BASE_DIR):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.setWindowTitle("Upload Lab")
        self.resize(1280, 860)
        self._load_ui()

    def _load_ui(self) -> None:
        ui_path = Path(__file__).resolve().parent / "forms" / "main_window.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Khong mo duoc UI file: {ui_path}")
        try:
            widget = QUiLoader().load(ui_file, self)
        finally:
            ui_file.close()
        if not isinstance(widget, QWidget):
            raise RuntimeError(f"UI file khong tao duoc QWidget: {ui_path}")
        self.setCentralWidget(widget)
```

Create `ui_qt/forms/main_window.ui` as a Qt Designer editable skeleton:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>UploadLabMainWindow</class>
 <widget class="QWidget" name="centralWidget">
  <layout class="QVBoxLayout" name="mainLayout">
   <item>
    <widget class="QTabWidget" name="mainTabs">
     <property name="currentIndex">
      <number>0</number>
     </property>
     <widget class="QWidget" name="excelTab">
      <attribute name="title">
       <string>Excel &amp; Missing Numbers</string>
      </attribute>
      <layout class="QVBoxLayout" name="excelLayout">
       <item>
        <widget class="QLabel" name="excelPlaceholder">
         <property name="text">
          <string>Load Excel, show parsed numbers, missing numbers, and warnings.</string>
         </property>
        </widget>
       </item>
      </layout>
     </widget>
     <widget class="QWidget" name="folderTab">
      <attribute name="title">
       <string>Folder Scan &amp; Upload</string>
      </attribute>
      <layout class="QVBoxLayout" name="folderLayout">
       <item>
        <widget class="QLabel" name="folderPlaceholder">
         <property name="text">
          <string>Scan one selected folder, preselect valid files, and upload selected rows.</string>
         </property>
        </widget>
       </item>
      </layout>
     </widget>
     <widget class="QWidget" name="regexTab">
      <attribute name="title">
       <string>Regex Review</string>
      </attribute>
      <layout class="QVBoxLayout" name="regexLayout">
       <item>
        <widget class="QLabel" name="regexPlaceholder">
         <property name="text">
          <string>Maintainer-only regex review workflow.</string>
         </property>
        </widget>
       </item>
      </layout>
     </widget>
    </widget>
   </item>
   <item>
    <widget class="QPlainTextEdit" name="logText">
     <property name="readOnly">
      <bool>true</bool>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <resources/>
 <connections/>
</ui>
```

- [ ] **Step 4: Run Qt structure tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui_qt tests/test_qt_ui_structure.py
git commit -m "add Qt app shell"
```

---

### Task 7: Wire Launcher to Qt App

**Files:**
- Modify: `ui_runner.py`
- Test: `tests/test_qt_ui_structure.py`
- Test: `tests/test_tkinter_ui_structure.py`

- [ ] **Step 1: Add launcher test**

Append to `tests/test_qt_ui_structure.py`:

```python
    def test_ui_runner_uses_qt_entrypoint(self):
        source = Path("ui_runner.py").read_text(encoding="utf-8")

        self.assertIn("from ui_qt.app import run_qt_app", source)
        self.assertIn("return run_qt_app()", source)
```

- [ ] **Step 2: Run launcher test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure.QtUIStructureTests.test_ui_runner_uses_qt_entrypoint
```

Expected: FAIL because `ui_runner.py` still imports `UploadLabApp`.

- [ ] **Step 3: Update `ui_runner.py`**

Replace with:

```python
from __future__ import annotations

from ui_qt.app import run_qt_app


def main() -> int:
    return run_qt_app()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Update old Tkinter structure test**

In `tests/test_tkinter_ui_structure.py`, change `test_ui_runner_is_thin_entrypoint` so it only checks the file is thin, not that it imports Tkinter:

```python
    def test_ui_runner_is_thin_entrypoint(self):
        source = inspect.getsource(ui_runner)

        self.assertLess(len(source.splitlines()), 40)
```

- [ ] **Step 5: Run UI structure tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure tests.test_tkinter_ui_structure
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add ui_runner.py tests/test_qt_ui_structure.py tests/test_tkinter_ui_structure.py
git commit -m "switch launcher to Qt app"
```

---

### Task 8: Build Qt Excel Tab Behavior

**Files:**
- Modify: `ui_qt/forms/main_window.ui`
- Modify: `ui_qt/main_window.py`
- Modify: `ui_qt/widgets.py`
- Test: service tests from Tasks 1-2

- [ ] **Step 1: Replace Excel placeholder with controls in `.ui`**

Use Qt Designer or edit XML so `excelTab` contains:

- `QLineEdit` named `excelPathEdit`
- `QPushButton` named `browseExcelButton`
- `QPushButton` named `loadExcelButton`
- `QLabel` named `excelSummaryLabel`
- `QTabWidget` named `excelResultTabs`
- `QTableWidget` named `parsedExcelTable`
- `QTableWidget` named `missingExcelTable`
- `QTableWidget` named `excelWarningTable`
- `QTableWidget` named `excelParseErrorTable`

- [ ] **Step 2: Add controller methods**

In `ui_qt/main_window.py`, add:

```python
from PySide6.QtWidgets import QFileDialog, QMessageBox
from ui.services.contract_book_audit import analyze_contract_book
from ui_qt.widgets import set_table_rows
```

Add methods:

```python
    def _connect_excel_tab(self) -> None:
        self.ui.browseExcelButton.clicked.connect(self.browse_excel)
        self.ui.loadExcelButton.clicked.connect(self.load_excel)

    def browse_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chon Excel so cong chung",
            str(self.working_dir),
            "Excel files (*.xlsx *.xlsm *.xls)",
        )
        if path:
            self.ui.excelPathEdit.setText(path)
            self.load_excel()

    def load_excel(self) -> None:
        path = self.ui.excelPathEdit.text().strip()
        if not path:
            QMessageBox.warning(self, "Upload Lab", "Chua chon file Excel.")
            return
        try:
            self.contract_book_analysis = analyze_contract_book(path)
        except Exception as exc:
            QMessageBox.critical(self, "Upload Lab", str(exc))
            return

        analysis = self.contract_book_analysis
        set_table_rows(
            self.ui.parsedExcelTable,
            ["Dong", "So", "Ngay", "Gia tri goc"],
            [[row.row_index, row.contract_no, row.raw_date, row.raw_contract_no] for row in analysis.valid_rows],
        )
        set_table_rows(
            self.ui.missingExcelTable,
            ["So thieu", "Nam", "STT"],
            [[item.contract_no, item.year, item.ordinal] for item in analysis.missing_numbers],
        )
        set_table_rows(
            self.ui.excelWarningTable,
            ["Dong", "Loai", "So goc", "Ngay", "Ly do"],
            [[w.row_index, w.kind.value, w.raw_contract_no, w.raw_date, w.message] for w in analysis.warning_rows],
        )
        set_table_rows(
            self.ui.excelParseErrorTable,
            ["Dong", "So goc", "Ngay", "Ly do"],
            [[w.row_index, w.raw_contract_no, w.raw_date, w.message] for w in analysis.parse_error_rows],
        )
        self.ui.excelSummaryLabel.setText(
            f"Excel={len(analysis.valid_rows)} | thieu={len(analysis.missing_numbers)} | canh bao={len(analysis.warning_rows)} | loi={len(analysis.parse_error_rows)}"
        )
```

In `_load_ui`, assign loaded widget to `self.ui` before `setCentralWidget`, then call `_connect_excel_tab()`.

- [ ] **Step 3: Run service tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit tests.test_web_list_service
```

Expected: PASS.

- [ ] **Step 4: Smoke-run Qt app**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from ui_qt.main_window import UploadLabMainWindow; from PySide6.QtWidgets import QApplication; import sys; app=QApplication([]); w=UploadLabMainWindow(); print(w.windowTitle())"
```

Expected output contains `Upload Lab`.

- [ ] **Step 5: Commit**

```powershell
git add ui_qt
git commit -m "build Qt Excel audit tab"
```

---

### Task 9: Build Qt Folder Scan and Result Group Tables

**Files:**
- Modify: `ui_qt/forms/main_window.ui`
- Modify: `ui_qt/main_window.py`
- Create: `ui_qt/workers.py`
- Test: `tests/test_scan_classification_service.py`

- [ ] **Step 1: Add folder tab controls in `.ui`**

Use Qt Designer or edit XML so `folderTab` contains:

- `QLineEdit` named `folderPathEdit`
- `QPushButton` named `browseFolderButton`
- `QPushButton` named `scanFolderButton`
- `QProgressBar` named `scanProgressBar`
- `QLabel` named `scanSummaryLabel`
- `QTabWidget` named `scanResultTabs`
- `QTableWidget` named `validUploadTable`
- `QTableWidget` named `notInExcelTable`
- `QTableWidget` named `missingFieldsTable`
- `QTableWidget` named `webDuplicateTable`
- `QTableWidget` named `localDuplicateTable`
- `QTableWidget` named `excelMissingInFolderTable`

- [ ] **Step 2: Create worker shell**

Create `ui_qt/workers.py`:

```python
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ui.services.folder_workflow_service import run_folder_scan


class FolderScanWorker(QObject):
    finished = Signal(dict, str)
    failed = Signal(str)
    progress = Signal(dict)

    def __init__(self, folder_path: str, working_dir: Path):
        super().__init__()
        self.folder_path = Path(folder_path)
        self.working_dir = Path(working_dir)

    @Slot()
    def run(self) -> None:
        try:
            manifest, manifest_path = run_folder_scan(
                self.folder_path,
                modified_since=None,
                full_rescan=False,
                progress_callback=lambda snapshot: self.progress.emit(dict(snapshot)),
                working_dir=self.working_dir,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(manifest, str(manifest_path))
```

- [ ] **Step 3: Add main window folder methods**

In `ui_qt/main_window.py`, add methods that browse folder, start worker, load queue records via existing `load_upload_queue`, classify with `classify_scan_records`, and render all group tables. Use `open_with_windows_default` on row double-click.

Use this rendering helper in `main_window.py`:

```python
    def render_scan_classification(self, classification) -> None:
        set_table_rows(
            self.ui.validUploadTable,
            ["Chon", "ID", "So", "Trang thai", "File"],
            [["x" if row.selected else "", row.record_id, row.contract_no, row.status, row.source_file] for row in classification.valid_upload_rows],
        )
        set_table_rows(
            self.ui.notInExcelTable,
            ["ID", "So", "Ly do", "File"],
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.not_in_excel_rows],
        )
        set_table_rows(
            self.ui.missingFieldsTable,
            ["ID", "So", "Thieu", "File"],
            [[row.record_id, row.contract_no, ", ".join(row.missing_fields), row.source_file] for row in classification.missing_field_rows],
        )
        set_table_rows(
            self.ui.webDuplicateTable,
            ["ID", "So", "Ly do", "File"],
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.web_duplicate_rows],
        )
        set_table_rows(
            self.ui.localDuplicateTable,
            ["ID", "So", "Ly do", "File"],
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.duplicate_local_rows],
        )
        set_table_rows(
            self.ui.excelMissingInFolderTable,
            ["So trong Excel chua thay file"],
            [[number] for number in classification.excel_missing_in_folder],
        )
```

- [ ] **Step 4: Run classification tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scan_classification_service
```

Expected: PASS.

- [ ] **Step 5: Smoke-run Qt import**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from ui_qt.workers import FolderScanWorker; print(FolderScanWorker.__name__)"
```

Expected output: `FolderScanWorker`.

- [ ] **Step 6: Commit**

```powershell
git add ui_qt
git commit -m "build Qt folder scan result groups"
```

---

### Task 10: Add Checkbox Upload Queue Behavior

**Files:**
- Modify: `ui_qt/widgets.py`
- Modify: `ui_qt/main_window.py`
- Test: `tests/test_upload_selection_service.py`

- [ ] **Step 1: Add Qt checkbox table helper**

In `ui_qt/widgets.py`, add:

```python
from PySide6.QtCore import Qt


def set_checkable_upload_rows(table: QTableWidget, rows: list) -> None:
    headers = ["Chon", "ID", "So", "Trang thai", "File"]
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Checked if row.selected else Qt.Unchecked)
        check_item.setData(Qt.UserRole, int(row.record_id))
        table.setItem(row_index, 0, check_item)
        for column_index, value in enumerate([row.record_id, row.contract_no, row.status, row.source_file], start=1):
            table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
    table.resizeColumnsToContents()


def checked_record_ids(table: QTableWidget) -> list[int]:
    ids: list[int] = []
    for row_index in range(table.rowCount()):
        item = table.item(row_index, 0)
        if item and item.checkState() == Qt.Checked:
            ids.append(int(item.data(Qt.UserRole)))
    return sorted(ids)
```

- [ ] **Step 2: Add UI controls**

In `ui_qt/forms/main_window.ui`, add:

- `QPushButton` named `selectAllValidButton`
- `QPushButton` named `clearValidSelectionButton`
- `QPushButton` named `uploadSelectedButton`

- [ ] **Step 3: Wire controller**

In `ui_qt/main_window.py`, use `set_checkable_upload_rows` for `validUploadTable`, wire `selectAllValidButton`, `clearValidSelectionButton`, and `uploadSelectedButton`. For upload, call the existing uploader path with selected record IDs or prepare selected rows only if `playwright_uploader` exposes a selected-record API; if it does not, keep `uploadSelectedButton` disabled and log `"Upload selected requires selected-record upload API"` until Task 11.

- [ ] **Step 4: Run selection tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_selection_service
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ui_qt tests/test_upload_selection_service.py
git commit -m "add Qt upload checkbox behavior"
```

---

### Task 11: Add Selected-Record Upload API

**Files:**
- Modify: `playwright_uploader.py`
- Modify: `ui/services/folder_workflow_service.py`
- Test: `tests/test_playwright_uploader.py`

- [ ] **Step 1: Add test for selected record filtering**

Append to `tests/test_playwright_uploader.py` a focused test near existing upload queue tests:

```python
    def test_load_upload_queue_can_filter_selected_record_ids(self):
        run_id = "selected-run"
        output1 = make_output_json(self.workdir / "output" / "selected1.json", contract_no="111/2026/CCGD", file_goc=str(self.root / "a.docx"))
        output2 = make_output_json(self.workdir / "output" / "selected2.json", contract_no="222/2026/CCGD", file_goc=str(self.root / "b.docx"))
        first_id = self._seed_record(file_key="sel-1", run_id=run_id, contract_no="111/2026/CCGD", status="extracted", output_json_path=output1)
        second_id = self._seed_record(file_key="sel-2", run_id=run_id, contract_no="222/2026/CCGD", status="extracted", output_json_path=output2)
        manifest_path = self.workdir / "runs" / "selected.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")

        _manifest, records, _total = load_upload_queue(
            manifest_path,
            working_dir=self.workdir,
            selected_record_ids={second_id},
        )

        self.assertEqual([record.record_id for record in records], [second_id])
        self.assertNotEqual(first_id, second_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_playwright_uploader.PlaywrightUploaderTests.test_load_upload_queue_can_filter_selected_record_ids
```

Expected: FAIL because `load_upload_queue` does not accept `selected_record_ids`.

- [ ] **Step 3: Implement selected filtering**

In `playwright_uploader.py`, update `load_upload_queue` signature:

```python
def load_upload_queue(
    manifest_path: Path | str,
    *,
    working_dir: Path = BASE_DIR,
    selected_record_ids: set[int] | None = None,
) -> tuple[dict, list[UploadRecord], int]:
```

After records are loaded and before returning:

```python
    if selected_record_ids is not None:
        selected = {int(record_id) for record_id in selected_record_ids}
        records = [record for record in records if int(record.record_id) in selected]
```

In `ui/services/folder_workflow_service.py`, add:

```python
def load_selected_queue_records(
    manifest_path: Path,
    selected_record_ids: set[int],
    *,
    working_dir: Path = BASE_DIR,
):
    return load_upload_queue(
        manifest_path,
        working_dir=working_dir,
        selected_record_ids=selected_record_ids,
    )
```

- [ ] **Step 4: Run uploader tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_playwright_uploader
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add playwright_uploader.py ui/services/folder_workflow_service.py tests/test_playwright_uploader.py
git commit -m "support selected upload records"
```

---

### Task 12: Add Regex Rule Catalog

**Files:**
- Create: `docs/regex-rules.md`
- Modify: `README.md`
- Modify: `HUONG_DAN.md`

- [ ] **Step 1: Create rule catalog**

Create `docs/regex-rules.md`:

```markdown
# Regex Rule Catalog

This catalog documents extraction rules used by `extract_contract.py`.
Do not place real contract content here. Use synthetic examples or shortened anonymized snippets.

## Common Rules

### `so_cong_chung`

Accepted raw forms:

- `428/2026/CCGD`
- `428.2026/CCGD`
- `2433.2025/PCDS/CCGD`
- `2233.2025/TCDS/CCGD`

Scan/raw may keep inheritance suffixes such as `PCDS` and `TCDS`.
Web field value should be shortened to `xxx/yyyy`.

## Document Type: Hop dong chuyen nhuong

Canonical title markers:

- `hop dong chuyen nhuong`

Fields:

- `so_cong_chung`
- `ten_hop_dong`
- `duong_su`
- `tai_san`

`tai_san` start anchors:

- `quyen su dung dat ... co dia chi tai`
- `quyen su dung dat va tai san gan lien voi dat ... co dia chi tai`

`tai_san` end anchors:

- `1.2`
- `Dieu 2`
- `Bang Hop dong nay`
- `va duoc Cong chung vien`

Must match:

- Synthetic text containing `quyen su dung dat cua ben A co dia chi tai ... Giay chung nhan ...`

Must not match:

- Explanatory text that mentions land use rights but does not describe the transferred asset block.

## Document Type: Van ban phan chia di san

Canonical title markers:

- `van ban phan chia di san`

`duong_su` start anchor:

- `Chung toi la nhung nguoi duoc huong di san`

`duong_su` end anchors:

- `Chung toi tu nguyen lap Van ban nay`
- `Nguoi de lai di san:`

`tai_san` start anchors:

- `Di san:`
- `Di san cua ... de lai la:`
- `quyen su dung dat ... co dia chi tai`

`tai_san` end anchors:

- `Nguoi thua ke:`
- `Noi dung phan chia di san`
- `Bang Van ban nay`
- `Loi chung`

## Document Type: Van ban tu choi nhan di san

Canonical title markers:

- `van ban tu choi nhan di san`

`duong_su` start anchor:

- `Toi la:`

`duong_su` end anchors:

- `Nay, toi tu nguyen lap Van ban nay`
- `Theo quy dinh cua phap luat`

`tai_san` start anchors:

- `1. Tai san thu nhat:`
- `quyen su dung dat ... co dia chi tai`

`tai_san` end anchors:

- `Bang Van ban nay, toi`
- `Toi xin cam doan`
- `Nguoi tu choi huong di san`
- `Loi chung`
```

- [ ] **Step 2: Link catalog from docs**

In `README.md` and `HUONG_DAN.md`, add one sentence in the regex review section:

```markdown
Rule trich xuat duoc ghi co he thong tai `docs/regex-rules.md`; khi them mau hop dong moi, cap nhat file nay cung voi test/review sample.
```

- [ ] **Step 3: Commit**

```powershell
git add docs/regex-rules.md README.md HUONG_DAN.md
git commit -m "document regex rule catalog"
```

---

### Task 13: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run full unit test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit tests.test_scan_classification_service tests.test_upload_selection_service tests.test_web_list_service tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_regex_review_samples tests.test_tkinter_ui_structure tests.test_qt_ui_structure
```

Expected: PASS.

- [ ] **Step 2: Run Qt smoke import**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from ui_qt.app import run_qt_app; print(callable(run_qt_app))"
```

Expected output: `True`.

- [ ] **Step 3: Check git status**

Run:

```powershell
git status --short --branch
```

Expected: clean branch except expected untracked runtime files ignored by `.gitignore`.

- [ ] **Step 4: Commit any final docs/test adjustments**

```powershell
git add .
git commit -m "finish Qt workflow redesign foundation"
```

Only run this commit if Step 1 or Step 2 required small follow-up edits.

---

## Self-Review

- Spec coverage:
  - Excel parsing/min-max/missing/warnings: Tasks 1-2.
  - Folder-only scan and result grouping: Tasks 3 and 9.
  - Valid rows preselected with select-all valid: Tasks 4 and 10.
  - Open Word file with Windows default app: Task 6 helper and Task 9 double-click wiring.
  - No source-file post-processing: preserved by not adding move/rename/delete behavior.
  - Regex workflow separated from user upload flow: Task 12.
  - Qt/PySide6 migration with editable `.ui`: Tasks 5-8.
- Placeholder scan: no `TBD`, `TODO`, or "implement later" instructions are used as plan steps.
- Type consistency: `ContractBookAnalysis`, `ClassifiedScanRow`, and `UploadSelection` names are introduced before later tasks consume them.
