# Upload Lab

Tool standalone de quet ho so hop dong, trich xuat thong tin va dry-run/upload len he thong cong chung Nam Dinh.

## Chay nhanh

```powershell
cd D:\upload_lab_repo
copy .env.example .env
.\run_ui.bat
```

UI PyQt6:

```powershell
cd D:\upload_lab_repo
.\run_ui_pyqt6.bat
```

## Cau truc

- `batch_scan.py`: quet folder, lap manifest, cap nhat `registry.sqlite3`
- `extract_contract.py`: trich xuat noi dung hop dong va map sang web form
- `playwright_uploader.py`: dry-run/upload Playwright
- `ui_runner.py`: UI Tkinter
- `ui_app_pyqt6.py`: UI PyQt6
- `tests/`: test hoi quy cho scan/extract/upload queue

## Test

```powershell
python -m unittest tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader
```

Repo nay da tach rieng, khong con phu thuoc vao `notary_v2`.
