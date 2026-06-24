# Tab 1 Excel Audit Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Tab 1 Excel auditing so it shows clean Excel rows, missing numbers, and all issue/duplicate rows according to the approved date-range-driven rules.

**Architecture:** Keep Excel parsing and audit rules inside `ui/services/contract_book_audit.py`; Qt only passes the selected date range and renders the returned groups. Preserve compatibility for existing folder classification by keeping `analysis.valid_rows` as a property alias for the new clean `display_rows`.

**Tech Stack:** Python 3.10+, PySide6, Qt Designer `.ui`, `openpyxl`, `unittest`.

---

## File Structure

- Modify `ui/services/contract_book_audit.py`: replace the broad warning model with strict date-range audit output: `display_rows`, `missing_numbers`, `issue_rows`, and `summary`.
- Modify `tests/test_contract_book_audit.py`: replace old permissive tests with strict format/year/duplicate/date/jump tests.
- Modify `ui/services/web_list_service.py`: pass date range into `analyze_contract_book()` and read from `display_rows`.
- Modify `tests/test_web_list_service.py`: update service callers to provide date range.
- Modify `ui/tabs/web_list_tab.py`: keep old Tk tab coherent by passing its existing date fields to `read_exported_contract_rows()`.
- Modify `ui_qt/forms/main_window.ui`: replace the Excel result tab widget with three vertical panes/tables and add `fromDateEdit`/`toDateEdit`.
- Modify `ui_qt/main_window.py`: wire date inputs, render new audit groups, and update status.
- Modify `ui_qt/widgets.py`: add a table helper that makes scrollbars visible and predictable.
- Modify `tests/test_qt_ui_structure.py`: assert new Excel widgets, scrollbars, headers, reset behavior, and load behavior.

---

### Task 1: Rebuild Contract Book Audit Service

**Files:**
- Modify: `ui/services/contract_book_audit.py`
- Test: `tests/test_contract_book_audit.py`

- [ ] **Step 1: Replace audit tests with strict business-rule tests**

In `tests/test_contract_book_audit.py`, keep `setUp()` and `_make_book()`, then replace the existing behavior tests with:

```python
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from ui.services.contract_book_audit import (
    ContractBookIssueKind,
    analyze_contract_book,
    parse_contract_book_no,
    parse_contract_date,
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

    def test_parse_contract_book_no_accepts_only_slash_year_forms(self):
        self.assertEqual(parse_contract_book_no("001/2026"), (2026, 1, "1/2026"))
        self.assertEqual(parse_contract_book_no("09/2026/CCGD"), (2026, 9, "9/2026"))
        self.assertIsNone(parse_contract_book_no("66.2026"))
        self.assertIsNone(parse_contract_book_no("123", default_year=2026))

    def test_parse_contract_date_supports_strings_and_excel_values(self):
        self.assertEqual(parse_contract_date("05/01/2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date("05-01-2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(date(2026, 1, 5)), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(datetime(2026, 1, 5, 14, 30)), date(2026, 1, 5))

    def test_missing_uses_clean_rows_only(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], ["1/2026", "3/2026"])
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026"])
        self.assertEqual(analysis.summary.valid_count, 2)
        self.assertEqual(analysis.summary.missing_count, 1)

    def test_wrong_year_and_bad_format_do_not_create_missing_for_other_years(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
            ("296/2025", "02/01/2026"),
            ("2047.2025", "02/01/2026"),
            ("344/2006", "02/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026"])
        self.assertEqual(
            [(issue.raw_contract_no, issue.kind) for issue in analysis.issue_rows],
            [
                ("296/2025", ContractBookIssueKind.WRONG_YEAR),
                ("2047.2025", ContractBookIssueKind.BAD_FORMAT),
                ("344/2006", ContractBookIssueKind.WRONG_YEAR),
            ],
        )

    def test_duplicate_numbers_move_all_duplicate_rows_to_issues(self):
        path = self._make_book([
            ("59/2026", "01/01/2026"),
            ("60/2026", "01/01/2026"),
            ("060/2026/CCGD", "01/01/2026"),
            ("61/2026", "01/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], ["59/2026", "61/2026"])
        duplicate_issues = [issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.DUPLICATE]
        self.assertEqual([issue.contract_no for issue in duplicate_issues], ["60/2026", "60/2026"])
        self.assertEqual(analysis.summary.duplicate_count, 2)

    def test_later_number_with_earlier_date_is_date_sequence_issue(self):
        path = self._make_book([
            ("1/2026", "02/01/2026"),
            ("2/2026", "03/01/2026"),
            ("3/2026", "01/01/2026"),
            ("4/2026", "04/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        issue = next(issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.DATE_SEQUENCE)
        self.assertEqual(issue.contract_no, "3/2026")
        self.assertEqual([row.contract_no for row in analysis.display_rows], ["1/2026", "2/2026", "4/2026"])

    def test_same_day_jump_over_ten_moves_later_row_to_issue(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("2/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
            ("20/2026", "01/01/2026"),
            ("21/2026", "02/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        issue = next(issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.SAME_DAY_JUMP)
        self.assertEqual(issue.contract_no, "20/2026")
        self.assertNotIn("20/2026", [row.contract_no for row in analysis.display_rows])
        self.assertNotIn("20/2026", [item.contract_no for item in analysis.missing_numbers])

    def test_skips_header_row_when_column_a_looks_like_contract_header(self):
        path = self._make_book([
            ("SO CONG CHUNG", "NGAY, THANG, NAM CONG CHUNG"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.row_index for row in analysis.display_rows], [3])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run audit tests to verify they fail**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit
```

Expected: FAIL because `ContractBookIssueKind` does not exist and `analyze_contract_book()` does not accept `from_date`/`to_date`.

- [ ] **Step 3: Replace audit service data model and strict parser**

In `ui/services/contract_book_audit.py`, define these public types near the top:

```python
class ContractBookIssueKind(str, Enum):
    BAD_FORMAT = "sai_format"
    WRONG_YEAR = "sai_nam"
    DUPLICATE = "trung_so"
    DATE_PARSE_ERROR = "ngay_khong_hop_le"
    DATE_SEQUENCE = "ngay_bat_thuong"
    SAME_DAY_JUMP = "nhay_bat_thuong_cung_ngay"


@dataclass(frozen=True)
class ContractBookDisplayRow:
    row_index: int
    raw_contract_no: str
    raw_date: str
    contract_no: str
    year: int
    ordinal: int
    contract_date: date


@dataclass(frozen=True)
class ContractBookIssueRow:
    row_index: int
    kind: ContractBookIssueKind
    raw_contract_no: str
    raw_date: str
    contract_no: str
    year: int | None
    ordinal: int | None
    contract_date: date | None
    message: str


@dataclass(frozen=True)
class ContractBookSummary:
    excel_total: int
    valid_count: int
    missing_count: int
    issue_count: int
    duplicate_count: int
```

Replace `ContractBookAnalysis` with:

```python
@dataclass(frozen=True)
class ContractBookAnalysis:
    source_path: Path
    display_rows: list[ContractBookDisplayRow]
    missing_numbers: list[MissingContractNumber]
    issue_rows: list[ContractBookIssueRow]
    summary: ContractBookSummary
    min_ordinal: int | None
    max_ordinal: int | None

    @property
    def valid_rows(self) -> list[ContractBookDisplayRow]:
        return self.display_rows

    @property
    def warning_rows(self) -> list[ContractBookIssueRow]:
        return self.issue_rows

    @property
    def parse_error_rows(self) -> list[ContractBookIssueRow]:
        return [issue for issue in self.issue_rows if issue.kind == ContractBookIssueKind.BAD_FORMAT]
```

Keep this alias only if older tests or imports still use it:

```python
ContractBookWarningKind = ContractBookIssueKind
ContractBookRow = ContractBookDisplayRow
ContractBookWarning = ContractBookIssueRow
```

Replace `parse_contract_book_no()` with strict slash-only parsing:

```python
def parse_contract_book_no(value: object, *, default_year: int | None = None) -> tuple[int, int, str] | None:
    del default_year
    text = re.sub(r"\s+", "", _fold_text(value))
    if not text:
        return None
    match = re.fullmatch(r"0*(\d+)/(\d{4})(?:/CCGD)?", text)
    if not match:
        return None
    ordinal = int(match.group(1))
    year = int(match.group(2))
    return year, ordinal, f"{ordinal}/{year}"
```

- [ ] **Step 4: Implement date range helpers and strict analysis**

Add these helpers below `parse_contract_date()`:

```python
def _parse_required_date(value: str | date, label: str) -> date:
    parsed = parse_contract_date(value)
    if parsed is None:
        raise ValueError(f"{label} khong dung dinh dang dd/mm/yyyy: {value}")
    return parsed


def _allowed_years(from_date: date, to_date: date) -> set[int]:
    if to_date < from_date:
        raise ValueError("Ngay ket thuc nho hon ngay bat dau.")
    return set(range(from_date.year, to_date.year + 1))


def _make_issue(
    row: ContractBookDisplayRow,
    kind: ContractBookIssueKind,
    message: str,
) -> ContractBookIssueRow:
    return ContractBookIssueRow(
        row_index=row.row_index,
        kind=kind,
        raw_contract_no=row.raw_contract_no,
        raw_date=row.raw_date,
        contract_no=row.contract_no,
        year=row.year,
        ordinal=row.ordinal,
        contract_date=row.contract_date,
        message=message,
    )
```

Replace `analyze_contract_book()` with this behavior:

```python
def analyze_contract_book(
    export_path: Path | str,
    *,
    from_date: str | date,
    to_date: str | date,
) -> ContractBookAnalysis:
    path = Path(export_path)
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file Excel: {path}")

    start_date = _parse_required_date(from_date, "from_date")
    end_date = _parse_required_date(to_date, "to_date")
    years = _allowed_years(start_date, end_date)

    parsed_rows: list[ContractBookDisplayRow] = []
    issues: list[ContractBookIssueRow] = []
    excel_total = 0

    for row_index, raw_contract_no, raw_date in _read_rows(path):
        raw_contract_text = _stringify_cell_value(raw_contract_no)
        raw_date_text = _stringify_cell_value(raw_date)
        if not raw_contract_text and not raw_date_text:
            continue
        excel_total += 1

        parsed_no = parse_contract_book_no(raw_contract_no)
        contract_date = parse_contract_date(raw_date)
        if parsed_no is None:
            issues.append(ContractBookIssueRow(
                row_index=row_index,
                kind=ContractBookIssueKind.BAD_FORMAT,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                contract_no="",
                year=None,
                ordinal=None,
                contract_date=contract_date,
                message="So cong chung khong dung dang xxx/yyyy hoac xxx/yyyy/CCGD.",
            ))
            continue

        year, ordinal, contract_no = parsed_no
        if contract_date is None:
            issues.append(ContractBookIssueRow(
                row_index=row_index,
                kind=ContractBookIssueKind.DATE_PARSE_ERROR,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                contract_no=contract_no,
                year=year,
                ordinal=ordinal,
                contract_date=None,
                message="Ngay cot B khong dung dinh dang dd/mm/yyyy.",
            ))
            continue
        if year not in years:
            issues.append(ContractBookIssueRow(
                row_index=row_index,
                kind=ContractBookIssueKind.WRONG_YEAR,
                raw_contract_no=raw_contract_text,
                raw_date=raw_date_text,
                contract_no=contract_no,
                year=year,
                ordinal=ordinal,
                contract_date=contract_date,
                message=f"Nam {year} khong thuoc khoang ngay dang chon.",
            ))
            continue

        parsed_rows.append(ContractBookDisplayRow(
            row_index=row_index,
            raw_contract_no=raw_contract_text,
            raw_date=raw_date_text,
            contract_no=contract_no,
            year=year,
            ordinal=ordinal,
            contract_date=contract_date,
        ))

    rows_by_contract_no: dict[str, list[ContractBookDisplayRow]] = {}
    for row in parsed_rows:
        rows_by_contract_no.setdefault(row.contract_no, []).append(row)

    duplicate_keys = {contract_no for contract_no, rows in rows_by_contract_no.items() if len(rows) > 1}
    clean_rows = [row for row in parsed_rows if row.contract_no not in duplicate_keys]
    for contract_no in sorted(duplicate_keys):
        for row in rows_by_contract_no[contract_no]:
            issues.append(_make_issue(row, ContractBookIssueKind.DUPLICATE, "So cong chung bi trung sau khi chuan hoa."))

    clean_rows = _remove_date_sequence_issues(clean_rows, issues)
    clean_rows = _remove_same_day_jump_issues(clean_rows, issues)
    clean_rows = sorted(clean_rows, key=lambda row: (row.year, row.ordinal, row.row_index))
    missing_numbers = _build_missing_numbers(clean_rows)
    ordinals = [row.ordinal for row in clean_rows]
    duplicate_count = sum(1 for issue in issues if issue.kind == ContractBookIssueKind.DUPLICATE)

    return ContractBookAnalysis(
        source_path=path,
        display_rows=clean_rows,
        missing_numbers=missing_numbers,
        issue_rows=sorted(issues, key=lambda issue: issue.row_index),
        summary=ContractBookSummary(
            excel_total=excel_total,
            valid_count=len(clean_rows),
            missing_count=len(missing_numbers),
            issue_count=len(issues),
            duplicate_count=duplicate_count,
        ),
        min_ordinal=min(ordinals) if ordinals else None,
        max_ordinal=max(ordinals) if ordinals else None,
    )
```

Add the two removal helpers used above:

```python
def _remove_date_sequence_issues(
    rows: list[ContractBookDisplayRow],
    issues: list[ContractBookIssueRow],
) -> list[ContractBookDisplayRow]:
    clean: list[ContractBookDisplayRow] = []
    latest_date: date | None = None
    for row in sorted(rows, key=lambda item: (item.year, item.ordinal, item.row_index)):
        if latest_date is not None and row.contract_date < latest_date:
            issues.append(_make_issue(
                row,
                ContractBookIssueKind.DATE_SEQUENCE,
                "Ngay cong chung som hon ngay cua so nho hon truoc do.",
            ))
            continue
        latest_date = row.contract_date if latest_date is None else max(latest_date, row.contract_date)
        clean.append(row)
    return clean


def _remove_same_day_jump_issues(
    rows: list[ContractBookDisplayRow],
    issues: list[ContractBookIssueRow],
) -> list[ContractBookDisplayRow]:
    issue_ids: set[tuple[int, str]] = set()
    rows_by_date: dict[date, list[ContractBookDisplayRow]] = {}
    for row in rows:
        rows_by_date.setdefault(row.contract_date, []).append(row)

    for contract_date in sorted(rows_by_date):
        previous: ContractBookDisplayRow | None = None
        for row in sorted(rows_by_date[contract_date], key=lambda item: (item.ordinal, item.row_index)):
            if previous is not None and row.ordinal - previous.ordinal > 10:
                issues.append(_make_issue(
                    row,
                    ContractBookIssueKind.SAME_DAY_JUMP,
                    f"So nhay {row.ordinal - previous.ordinal} trong cung ngay, vuot nguong 10.",
                ))
                issue_ids.add((row.row_index, row.contract_no))
                continue
            previous = row

    return [row for row in rows if (row.row_index, row.contract_no) not in issue_ids]
```

- [ ] **Step 5: Run audit tests**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit
```

Expected: PASS.

- [ ] **Step 6: Commit audit service**

Run:

```powershell
git add ui/services/contract_book_audit.py tests/test_contract_book_audit.py
git commit -m "tighten Excel audit business rules"
```

---

### Task 2: Update Web List Compatibility Around Date Range

**Files:**
- Modify: `ui/services/web_list_service.py`
- Modify: `tests/test_web_list_service.py`
- Modify: `ui/tabs/web_list_tab.py`

- [ ] **Step 1: Update web list tests to pass date range**

In `tests/test_web_list_service.py`, update every call to `read_exported_contract_rows(export_path)` to:

```python
rows = read_exported_contract_rows(
    export_path,
    from_date="01/01/2026",
    to_date="18/06/2026",
)
```

Replace the old test that accepts short number inferred from date with a strict rejection test:

```python
    def test_read_exported_contract_rows_rejects_short_number_without_slash_year(self):
        export_path = self.root / "short.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SO CONG CHUNG"
        sheet["B1"] = "NGAY"
        sheet["A2"] = "123"
        sheet["B2"] = "05/02/2026"
        workbook.save(export_path)
        workbook.close()

        rows = read_exported_contract_rows(
            export_path,
            from_date="01/01/2026",
            to_date="18/06/2026",
        )

        self.assertEqual(rows, [])
```

- [ ] **Step 2: Run web list tests to verify they fail**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_web_list_service
```

Expected: FAIL because `read_exported_contract_rows()` has not accepted `from_date` and `to_date` yet.

- [ ] **Step 3: Update `read_exported_contract_rows()` signature**

In `ui/services/web_list_service.py`, replace the function with:

```python
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
```

Leave `find_missing_contract_numbers()` unchanged for old callers that already pass clean rows.

- [ ] **Step 4: Update old Tk web tab caller**

In `ui/tabs/web_list_tab.py`, replace:

```python
self.rows = read_exported_contract_rows(export_path)
```

with:

```python
self.rows = read_exported_contract_rows(
    export_path,
    from_date=self.from_date_var.get().strip(),
    to_date=self.to_date_var.get().strip(),
)
```

- [ ] **Step 5: Run web list tests**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_web_list_service
```

Expected: PASS.

- [ ] **Step 6: Run scan classification tests for compatibility**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_scan_classification_service
```

Expected: PASS because `ContractBookAnalysis.valid_rows` still aliases `display_rows`.

- [ ] **Step 7: Commit compatibility update**

Run:

```powershell
git add ui/services/web_list_service.py tests/test_web_list_service.py ui/tabs/web_list_tab.py
git commit -m "pass date range into web list audit"
```

---

### Task 3: Rebuild Qt Excel Tab Layout

**Files:**
- Modify: `ui_qt/forms/main_window.ui`
- Modify: `ui_qt/widgets.py`
- Modify: `tests/test_qt_ui_structure.py`

- [ ] **Step 1: Add failing Qt structure test for three Excel tables and scrollbars**

In `tests/test_qt_ui_structure.py`, replace the Excel widget expectations in `test_excel_tab_widgets_exist()`:

```python
("excelResultTabs", QTabWidget),
("parsedExcelTable", QTableWidget),
("missingExcelTable", QTableWidget),
("excelWarningTable", QTableWidget),
("excelParseErrorTable", QTableWidget),
```

with:

```python
("fromDateEdit", QLineEdit),
("toDateEdit", QLineEdit),
("excelDisplayTable", QTableWidget),
("excelMissingTable", QTableWidget),
("excelIssueTable", QTableWidget),
```

Replace:

```python
self.assertEqual(window.excelResultTabs.count(), 4)
```

with:

```python
for table in (window.excelDisplayTable, window.excelMissingTable, window.excelIssueTable):
    self.assertEqual(table.verticalScrollBarPolicy(), Qt.ScrollBarAlwaysOn)
self.assertEqual(window.excelIssueTable.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOn)
```

Add `Qt` to that test import:

```python
from PySide6.QtCore import Qt
```

- [ ] **Step 2: Run Qt structure test to verify it fails**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure.QtUIStructureTests.test_excel_tab_widgets_exist
```

Expected: FAIL because the new widgets do not exist.

- [ ] **Step 3: Add scrollbar helper**

In `ui_qt/widgets.py`, add:

```python
def configure_audit_table_scrollbars(table: QTableWidget, *, horizontal: bool = False) -> None:
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn if horizontal else Qt.ScrollBarAsNeeded)
```

- [ ] **Step 4: Replace Excel section in `.ui`**

In `ui_qt/forms/main_window.ui`, change the Excel tab so it contains:

- `QLineEdit` named `fromDateEdit`
- `QLineEdit` named `toDateEdit`
- existing `QLineEdit` named `excelPathEdit`
- existing `QPushButton` named `browseExcelButton`
- existing `QPushButton` named `loadExcelButton`
- existing `QLabel` named `excelSummaryLabel`
- `QSplitter` or vertical layout with three table sections:
  - `QTableWidget` named `excelDisplayTable`
  - `QTableWidget` named `excelMissingTable`
  - `QTableWidget` named `excelIssueTable`

Use these labels in the UI:

```xml
<string>Danh sach Excel</string>
<string>So con thieu</string>
<string>So loi, trung</string>
```

Set scrollbar properties in each table XML:

```xml
<property name="verticalScrollBarPolicy">
 <enum>Qt::ScrollBarAlwaysOn</enum>
</property>
```

For `excelIssueTable`, also set:

```xml
<property name="horizontalScrollBarPolicy">
 <enum>Qt::ScrollBarAlwaysOn</enum>
</property>
```

- [ ] **Step 5: Run Qt structure test**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure.QtUIStructureTests.test_excel_tab_widgets_exist
```

Expected: PASS.

- [ ] **Step 6: Commit layout update**

Run:

```powershell
git add ui_qt/forms/main_window.ui ui_qt/widgets.py tests/test_qt_ui_structure.py
git commit -m "rebuild Qt Excel audit layout"
```

---

### Task 4: Wire Qt Excel Controller to New Audit Output

**Files:**
- Modify: `ui_qt/main_window.py`
- Modify: `tests/test_qt_ui_structure.py`

- [ ] **Step 1: Add failing test for new render and reset behavior**

In `tests/test_qt_ui_structure.py`, replace `test_failed_excel_load_clears_previous_results()` with:

```python
    def test_excel_load_renders_clean_missing_and_issue_tables(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workbook_path = temp_root / "book.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet["A1"] = "SO CONG CHUNG"
            sheet["B1"] = "NGAY, THANG, NAM CONG CHUNG"
            sheet["A2"] = "1/2026"
            sheet["B2"] = "01/01/2026"
            sheet["A3"] = "3/2026"
            sheet["B3"] = "01/01/2026"
            sheet["A4"] = "66.2026"
            sheet["B4"] = "01/01/2026"
            workbook.save(workbook_path)
            workbook.close()

            window = UploadLabMainWindow(working_dir=temp_root)
            window.excelPathEdit.setText(str(workbook_path))
            window.fromDateEdit.setText("01/01/2026")
            window.toDateEdit.setText("18/06/2026")
            window.load_excel()

            self.assertIn("Excel=3 | hop_le=2 | thieu=1 | loi=1 | trung=0", window.excelSummaryLabel.text())
            self.assertEqual(window.excelDisplayTable.rowCount(), 2)
            self.assertEqual(window.excelDisplayTable.item(0, 1).text(), "1/2026")
            self.assertEqual(window.excelMissingTable.rowCount(), 1)
            self.assertEqual(window.excelMissingTable.item(0, 0).text(), "2/2026")
            self.assertEqual(window.excelIssueTable.rowCount(), 1)
            self.assertEqual(window.excelIssueTable.item(0, 0).text(), "sai_format")
            self.assertIsNotNone(app)
```

Add a reset-focused test:

```python
    def test_failed_excel_load_clears_new_excel_tables(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        window.excelDisplayTable.setRowCount(1)
        window.excelMissingTable.setRowCount(1)
        window.excelIssueTable.setRowCount(1)
        window.excelPathEdit.setText(str(Path("missing.xlsx").resolve()))

        with patch("ui_qt.main_window.QMessageBox.critical") as mocked_critical:
            window.load_excel()

        mocked_critical.assert_called_once()
        self.assertEqual(window.excelSummaryLabel.text(), "Chua doc Excel.")
        self.assertEqual(window.excelDisplayTable.rowCount(), 0)
        self.assertEqual(window.excelMissingTable.rowCount(), 0)
        self.assertEqual(window.excelIssueTable.rowCount(), 0)
        self.assertIsNotNone(app)
```

- [ ] **Step 2: Run new Qt render tests to verify they fail**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure.QtUIStructureTests.test_excel_load_renders_clean_missing_and_issue_tables tests.test_qt_ui_structure.QtUIStructureTests.test_failed_excel_load_clears_new_excel_tables
```

Expected: FAIL because `UploadLabMainWindow` still references old Excel tables and does not pass date range.

- [ ] **Step 3: Update Qt imports, constants, and attributes**

In `ui_qt/main_window.py`, import defaults:

```python
from playwright_uploader import default_export_from_date, default_export_to_date, load_upload_queue
```

Replace Excel header constants with:

```python
EXCEL_DISPLAY_HEADERS = ["Ngay", "So cong chung", "Dong Excel"]
EXCEL_MISSING_HEADERS = ["So thieu", "Nam", "STT"]
EXCEL_ISSUE_HEADERS = ["Loai loi", "Dong", "Ngay", "So goc", "So chuan", "Ly do"]
```

Replace Excel widget attributes with:

```python
self.fromDateEdit: QLineEdit | None = None
self.toDateEdit: QLineEdit | None = None
self.excelDisplayTable: QTableWidget | None = None
self.excelMissingTable: QTableWidget | None = None
self.excelIssueTable: QTableWidget | None = None
```

Remove the old attributes:

```python
self.excelResultTabs
self.parsedExcelTable
self.missingExcelTable
self.excelWarningTable
self.excelParseErrorTable
```

- [ ] **Step 4: Update `_connect_excel_tab()`**

Replace the Excel widget discovery block with:

```python
self.fromDateEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "fromDateEdit"))
self.toDateEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "toDateEdit"))
self.excelPathEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "excelPathEdit"))
self.browseExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "browseExcelButton"))
self.loadExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "loadExcelButton"))
self.excelSummaryLabel = cast(QLabel, self.ui.findChild(QLabel, "excelSummaryLabel"))
self.excelDisplayTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelDisplayTable"))
self.excelMissingTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelMissingTable"))
self.excelIssueTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelIssueTable"))

if self.fromDateEdit is not None and not self.fromDateEdit.text().strip():
    self.fromDateEdit.setText(default_export_from_date())
if self.toDateEdit is not None and not self.toDateEdit.text().strip():
    self.toDateEdit.setText(default_export_to_date())
for table, horizontal in (
    (self.excelDisplayTable, False),
    (self.excelMissingTable, False),
    (self.excelIssueTable, True),
):
    if table is not None:
        configure_audit_table_scrollbars(table, horizontal=horizontal)
```

Add `configure_audit_table_scrollbars` to the `ui_qt.widgets` import list.

- [ ] **Step 5: Update reset and load methods**

Replace `_reset_excel_results()` with:

```python
def _reset_excel_results(self, summary_text: str) -> None:
    self.contract_book_analysis = None
    if (
        self.excelDisplayTable is None
        or self.excelMissingTable is None
        or self.excelIssueTable is None
        or self.excelSummaryLabel is None
    ):
        return

    set_table_rows(self.excelDisplayTable, EXCEL_DISPLAY_HEADERS, [], resize_columns=False)
    set_table_rows(self.excelMissingTable, EXCEL_MISSING_HEADERS, [], resize_columns=False)
    set_table_rows(self.excelIssueTable, EXCEL_ISSUE_HEADERS, [], resize_columns=False)
    self.excelSummaryLabel.setText(summary_text)
```

In `load_excel()`, replace the analysis call and render block with:

```python
if self.fromDateEdit is None or self.toDateEdit is None:
    QMessageBox.critical(self, "Upload Lab", "Khong tim thay truong ngay tren giao dien.")
    return

from_date = self.fromDateEdit.text().strip()
to_date = self.toDateEdit.text().strip()
should_resize_columns = self.contract_book_analysis is None
try:
    self.contract_book_analysis = analyze_contract_book(path, from_date=from_date, to_date=to_date)
except Exception as exc:
    self._reset_excel_results("Chua doc Excel.")
    QMessageBox.critical(self, "Upload Lab", str(exc))
    return

analysis = self.contract_book_analysis
if (
    self.excelDisplayTable is None
    or self.excelMissingTable is None
    or self.excelIssueTable is None
    or self.excelSummaryLabel is None
):
    QMessageBox.critical(self, "Upload Lab", "Khong tim thay widget Excel tren giao dien.")
    return

set_table_rows(
    self.excelDisplayTable,
    EXCEL_DISPLAY_HEADERS,
    [[row.raw_date, row.contract_no, row.row_index] for row in analysis.display_rows],
    resize_columns=should_resize_columns,
)
set_table_rows(
    self.excelMissingTable,
    EXCEL_MISSING_HEADERS,
    [[item.contract_no, item.year, item.ordinal] for item in analysis.missing_numbers],
    resize_columns=should_resize_columns,
)
set_table_rows(
    self.excelIssueTable,
    EXCEL_ISSUE_HEADERS,
    [
        [
            issue.kind.value,
            issue.row_index,
            issue.raw_date,
            issue.raw_contract_no,
            issue.contract_no,
            issue.message,
        ]
        for issue in analysis.issue_rows
    ],
    resize_columns=should_resize_columns,
)
summary = analysis.summary
self.excelSummaryLabel.setText(
    f"Excel={summary.excel_total} | hop_le={summary.valid_count} | thieu={summary.missing_count} | loi={summary.issue_count} | trung={summary.duplicate_count}"
)
```

- [ ] **Step 6: Run Qt UI structure tests**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_qt_ui_structure
```

Expected: PASS.

- [ ] **Step 7: Commit controller update**

Run:

```powershell
git add ui_qt/main_window.py tests/test_qt_ui_structure.py
git commit -m "wire Qt Excel audit results"
```

---

### Task 5: Final Verification

**Files:**
- No new implementation files.

- [ ] **Step 1: Run focused Excel and Qt tests**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit tests.test_web_list_service tests.test_qt_ui_structure
```

Expected: PASS.

- [ ] **Step 2: Run scan and upload regression tests touched by compatibility**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_scan_classification_service tests.test_upload_selection_service tests.test_playwright_uploader
```

Expected: PASS.

- [ ] **Step 3: Smoke-run real Excel audit against the user's sample**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -c "from ui.services.contract_book_audit import analyze_contract_book; a=analyze_contract_book(r'D:\upload_lab_repo\downloads\So_cong_chung_2026-01-01_2026-06-10.xlsx', from_date='01/01/2026', to_date='18/06/2026'); print(f'Excel={a.summary.excel_total} | hop_le={a.summary.valid_count} | thieu={a.summary.missing_count} | loi={a.summary.issue_count} | trung={a.summary.duplicate_count}'); print([i.contract_no for i in a.missing_numbers[:10]]); print([(i.kind.value, i.row_index, i.raw_contract_no, i.contract_no) for i in a.issue_rows[:10]])"
```

Expected: output must not include missing numbers for `2025` or `2006`; summary must print the new status fields.

- [ ] **Step 4: Run Qt smoke import**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -c "from ui_qt.main_window import UploadLabMainWindow; from PySide6.QtWidgets import QApplication; import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen'); app=QApplication.instance() or QApplication([]); w=UploadLabMainWindow(); print(w.excelSummaryLabel.text())"
```

Expected: output contains `Excel=0`.

- [ ] **Step 5: Run full known suite**

Run:

```powershell
D:\upload_lab_repo\.venv\Scripts\python.exe -m unittest tests.test_contract_book_audit tests.test_scan_classification_service tests.test_upload_selection_service tests.test_web_list_service tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_regex_review_samples tests.test_tkinter_ui_structure tests.test_qt_ui_structure
```

Expected: PASS.

- [ ] **Step 6: Check git status**

Run:

```powershell
git status --short --branch
```

Expected: clean branch on `codex/qt-workflow-redesign`.

---

## Self-Review

- Spec coverage:
  - Date-range-driven valid years: Task 1 and Task 4.
  - Strict `xxx/yyyy` and `xxx/yyyy/CCGD` parsing: Task 1.
  - Wrong year, bad format, duplicate, date sequence, same-day jump issues: Task 1.
  - Missing only from clean rows: Task 1.
  - Three Qt Excel regions and visible scrollbars: Task 3.
  - Status `Excel | hop_le | thieu | loi | trung`: Task 4.
  - Regression protection for scan/upload consumers: Task 2 and Task 5.
- Placeholder scan: no placeholder steps remain.
- Type consistency:
  - `display_rows`, `missing_numbers`, `issue_rows`, and `summary` are introduced in Task 1 and consumed in Task 4.
  - `valid_rows` stays as a property alias for compatibility with scan classification.
