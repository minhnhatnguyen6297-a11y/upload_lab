# CLAUDE.md - upload_lab

Tai lieu van hanh ngan cho repo `upload_lab`.
Cap nhat: 2026-06-05.

## Tong quan

Tool standalone de quet ho so Word, trich xuat JSON web form, va dry-run/upload len he thong cong chung Nam Dinh bang Playwright.

Backend tach rieng khoi UI. UI hien tai la Tkinter modular, khong dung PyQt/PySide.

## Cau truc cot loi

```text
upload_lab/
|-- batch_scan.py
|-- extract_contract.py
|-- playwright_uploader.py
|-- uploader_selectors.py
|-- ui_runner.py
|-- ui/
|   |-- app.py
|   |-- tabs/
|   |-- services/
|   `-- widgets.py
|-- review_regex_samples.py
|-- regex_review_samples/
|-- tests/
`-- .env.example
```

## UI

- `Web & Danh sach`: cau hinh uploader, tai/doc Excel web, tra cuu so cong chung, tim so bi ho.
- `Folder dang chon`: chon folder, scan, extract thu, queue upload, dry-run, finalize.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_web_list_service tests.test_regex_review_samples tests.test_tkinter_ui_structure
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
- UI Tkinter phai dua moi cap nhat tu worker thread ve main thread qua `after(...)` hoac `UploadLabApp.log`.
- Log message nen giu prefix dang `[TAG]`.
