# Upload Lab

Tool standalone de quet ho so hop dong, trich xuat thong tin va dry-run/upload len he thong cong chung Nam Dinh.

## Chay nhanh

```powershell
cd D:\upload_lab_repo
copy .env.example .env
.\run_ui.bat
```

## UI

- Tab `Web & Danh sach`: cau hinh uploader, tai/doc Excel tu web, tra cuu so cong chung, tim so bi ho theo min-max trong Excel.
- Tab `Folder dang chon`: chon folder, batch scan, extract thu 1 file, refresh queue, dry-run upload, finalize record da luu tren web.

## Cau truc

- `batch_scan.py`: quet folder, lap manifest, cap nhat `registry.sqlite3`
- `extract_contract.py`: trich xuat noi dung hop dong va map sang web form
- `playwright_uploader.py`: dry-run/upload Playwright
- `ui_runner.py`: entrypoint Tkinter mong
- `ui/`: UI Tkinter modular va service phuc vu UI
- `review_regex_samples.py`: chay review regex tren van ban mau trong `regex_review_samples/input/`
- `tests/`: test hoi quy cho scan/extract/upload/UI service

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_web_list_service tests.test_regex_review_samples tests.test_tkinter_ui_structure
```

## Regex review

Dat file `.doc`/`.docx` that vao `regex_review_samples/input/`, roi chay:

```powershell
.\.venv\Scripts\python.exe .\review_regex_samples.py
```

Report JSON/CSV duoc ghi vao `regex_review_samples/reports/`. File mau that va report runtime duoc ignore boi git.

Rule trich xuat duoc ghi co he thong tai `docs/regex-rules.md`; khi them mau hop dong moi, cap nhat file nay cung voi test/review sample.

Repo nay da tach rieng, khong con phu thuoc vao `notary_v2`.
