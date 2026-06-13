# Huong dan su dung Upload Tool

## Chay lan dau

Double-click `run_ui.bat`.

Launcher se tu dong tim Python 3.10+, tao `.venv`, cai dependency, cai `playwright chromium`, va mo UI.

## Tab Web & Danh sach

- Bam `Cau hinh` de nhap URL, tai khoan, mat khau uploader.
- Nhap khoang ngay va bam `Tai Excel` de tai danh sach so cong chung tu web.
- Co the bam `Chon file` de doc lai mot Excel da tai.
- Nhap so cong chung vao o `Tra so` de tim trong Excel web.
- Bang `So bi ho` hien cac so thieu trong khoang min-max cua tung nam trong Excel.

## Tab Folder dang chon

- Bam `Chon folder`, nhap `Modified` neu can, tick `Full rescan` neu muon quet lai toan bo, roi bam `Scan`.
- `Extract thu` dung de kiem tra nhanh 1 file Word rieng le.
- `Manifest` duoc tu dong gan sau khi scan xong, hoac co the chon file trong `runs/`.
- `Refresh queue` doc queue local va loc cac so da co tren web theo Excel o Tab 1.
- `Dry-run` mo Playwright va dung truoc nut `Luu`.
- Sau khi da bam `Luu` tren web, chon record trong bang queue va bam `Finalize`.

## Regex review

Dat file `.doc`/`.docx` can kiem vao:

```text
regex_review_samples/input/
```

Chay:

```powershell
.\.venv\Scripts\python.exe .\review_regex_samples.py
```

Doc report moi nhat trong `regex_review_samples/reports/` de kiem cac truong `nguoi_yeu_cau`, `duong_su`, `tai_san`, `missing_fields`. File mau that va report runtime khong duoc track git.

## Output va log

| Path | Noi dung |
|---|---|
| `output/<so_cong_chung>_<hash>.json` | Ket qua trich xuat tung hop dong |
| `runs/<timestamp>.json` | Manifest cua moi lan batch scan |
| `registry.sqlite3` | Registry toan bo records + trang thai upload |
| `logs/playwright_uploader.log` | Log Playwright uploader |
| `upload_runs/<timestamp_runid>/` | Artifact dry-run |

## Troubleshooting nhanh

| Trieu chung | Cach xu ly |
|---|---|
| Thieu Python/Playwright | Chay lai `run_ui.bat` |
| Thieu `openpyxl` | Chay lai `run_ui.bat` |
| Khong upload duoc, chua dang nhap | Tab `Web & Danh sach` -> `Cau hinh` -> `Luu va dang nhap` |
| Khong doi chieu duoc Excel | Kiem tra file Excel va cot A |
