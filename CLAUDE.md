# CLAUDE.md - upload_lab

Tai lieu van hanh ngan cho repo `upload_lab`.
Cap nhat: 2026-06-24.

## Tong quan

Tool standalone de quet ho so Word, trich xuat JSON web form, va dry-run/upload len he thong cong chung Nam Dinh bang Playwright.

Backend tach rieng khoi UI. UI hien tai la Qt/PySide6 trong `ui_qt/`; UI cu da duoc loai bo khoi main.

## Cau truc cot loi

```text
upload_lab/
|-- batch_scan.py
|-- extract_contract.py
|-- playwright_uploader.py
|-- uploader_selectors.py
|-- ui_runner.py
|-- ui_qt/
|-- ui/
|   `-- services/
|-- review_regex_samples.py
|-- regex_review_samples/
|-- tests/
`-- .env.example
```

## UI

- `Excel Audit`: cau hinh uploader, tai/doc Excel web, thong ke so hop le/thieu/loi/trung.
- `Folder Scan Upload`: scan folder, loc/tick so can upload, upload theo chunk tren web.
- `Regex Review`: review regex voi sample neu can.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_web_list_service tests.test_regex_review_samples tests.test_qt_ui_structure tests.test_scan_classification_service tests.test_upload_selection_service
```

## Regex review

Dat file that vao `regex_review_samples/input/`, chay:

```powershell
.\.venv\Scripts\python.exe .\review_regex_samples.py
```

Doc report JSON/CSV trong `regex_review_samples/reports/`. Khong commit file mau that hoac report runtime.

## Quy uoc khi sua code

- Khong doi ten cac ham public trong `batch_scan.py` va `playwright_uploader.py` neu khong thuc su can thiet.
- Khong doi schema `registry.sqlite3` neu chua co migration.
- Selectors web form nam trong `uploader_selectors.py`.
- UI Qt phai dua cap nhat tu worker thread qua signal/slot hoac helper worker hien co trong `ui_qt/workers.py`.
- Log message nen giu prefix dang `[TAG]`.
