# CLAUDE.md — upload_lab

Tài liệu vận hành cho agent khi làm việc với repo `upload_lab`.
Cập nhật: 13/04/2026.

## Tổng quan

Tool standalone để:
1. **Quét hồ sơ** — batch scan folder Word (`.docx`/`.doc`), tìm số công chứng, trich xuất JSON, ghi manifest + registry SQLite.
2. **Upload hồ sơ** — dry-run/upload Playwright lên hệ thống công chứng Nam Định, đối chiếu Excel, tránh trùng số.

Repo này đã tách riêng khỏi `notary_v2`, **không còn phụ thuộc vào notary_v2**.

## Cấu trúc file cốt lõi

```
upload_lab/
├── batch_scan.py            # Quét folder, tạo manifest, cập nhật registry.sqlite3
├── extract_contract.py      # Trich xuất nội dung hợp đồng Word → JSON web form
├── playwright_uploader.py   # Dry-run / upload Playwright lên web công chứng
├── uploader_selectors.py    # CSS/role selectors + field order cho web form Nam Định
├── ui_runner.py             # UI Tkinter (legacy, giữ làm fallback)
├── ui_app_pyqt6.py          # UI PyQt6 (main entry point hiện tại)
├── ui/                      # Package UI PyQt6
│   ├── main_window.py
│   ├── tabs/                # batch_scan_tab.py, upload_tab.py
│   ├── widgets/             # file_browser, progress_panel, log_viewer, table_widget
│   ├── styles/              # stylesheets.py (QSS)
│   └── threads/             # batch_scan_worker, upload_worker
├── bootstrap_ui.py          # Bootstrap Tkinter (legacy)
├── bootstrap_ui_pyqt6.py    # Bootstrap PyQt6 — tạo .venv, cài dep, chạy UI
├── run_ui.bat               # Launcher Tkinter (legacy)
├── run_ui_pyqt6.bat         # Launcher PyQt6 (launcher chính)
├── build_standalone_release.ps1  # Tạo bản phát hành sạch vào _release/
├── requirements.txt         # python-docx, playwright, openpyxl, PyQt6>=6.4.0
├── tests/                   # Unit/integration tests
└── .env.example             # Mẫu cấu hình uploader
```

## Chạy dự án

```bat
REM Launcher chính (PyQt6) — double-click hoặc:
run_ui_pyqt6.bat

REM Launcher legacy Tkinter:
run_ui.bat
```

Bootstrap tự động:
- Tìm Python 3.10+ (venv sẵn → `py -3` → `python` → winget → installer python.org)
- Tạo `.venv` riêng trong thư mục tool
- Cài `requirements.txt` + `playwright install chromium`
- Mở giao diện

**Lần đầu cần Internet. Không cần Microsoft Office.**

## Hai tab chính trong UI

### Tab 1 — Quét hồ sơ (Batch Scan)

- Browse folder tổng
- Nhập `modified since` (YYYY-MM-DD hoặc DD/MM/YYYY)
- Tick `Full rescan` nếu cần quét lại toàn bộ
- Điều chỉnh độ sâu folder (mặc định 3)
- Kết quả ghi vào `output/`, `runs/`, `registry.sqlite3`

### Tab 2 — Upload hồ sơ (Upload Playwright)

1. Chọn file manifest trong `runs/`
2. Chọn file Excel đối chiếu hoặc bấm `Tải từ web`
3. Bấm `Refresh Queue` → `Start Dry-run`
4. Tool mở tab Playwright, dừng trước nút `Lưu`
5. Kiểm tra → bấm `Lưu` trên web → quay lại UI → `Finalize Selected`

## Cấu hình uploader lần đầu

1. Mở tab `Upload hồ sơ` → `Cấu hình uploader`
2. Điền Base URL, Login URL, Create URL, tài khoản, mật khẩu
3. Bấm `Lưu và đăng nhập` → tạo `nd_storage_state.json`

File `.env` được tạo tự động từ `.env.example` nếu thiếu.

## Biến môi trường (.env)

```env
ND_BASE_URL=https://congchung.namdinh.gov.vn
ND_LOGIN_URL=https://congchung.namdinh.gov.vn
ND_CREATE_URL=https://congchung.namdinh.gov.vn/ho-so-cong-chung/tao-moi-nhanh
ND_USERNAME=
ND_PASSWORD=
ND_STORAGE_STATE_PATH=nd_storage_state.json
ND_BROWSER_CHANNEL=chromium
ND_MAX_PREPARED_TABS=10
ND_POST_PREPARE_DELAY_MS=1500
```

## Output và log

| Path | Nội dung |
|---|---|
| `output/<so_cong_chung>_<hash>.json` | Kết quả trich xuất từng hợp đồng |
| `runs/<timestamp>.json` | Manifest của mỗi lần batch scan |
| `registry.sqlite3` | Registry toàn bộ records + trạng thái upload |
| `logs/playwright_uploader.log` | Log Playwright uploader |
| `upload_runs/<timestamp_runid>/` | Artifact dry-run (screenshot, debug JSON, trace) |

## Chạy tests

```powershell
python -m unittest tests.test_upload_lab_extract_contract tests.test_upload_batch_scan tests.test_playwright_uploader tests.test_pyqt6_ui
```

## Tạo bản phát hành standalone

```powershell
powershell -ExecutionPolicy Bypass -File .\build_standalone_release.ps1
```

Tạo thư mục `_release/upload_lab/` chỉ chứa file cần thiết (không có `.env`, `.venv`, `registry.sqlite3`, data runtime).

**File ship trong release:**
`batch_scan.py`, `bootstrap_ui.py`, `bootstrap_ui_pyqt6.py`, `build_standalone_release.ps1`, `extract_contract.py`, `install_python_windows.ps1`, `playwright_uploader.py`, `requirements.txt`, `run_ui.bat`, `run_ui_pyqt6.bat`, `ui_runner.py`, `ui_app_pyqt6.py`, `ui/`, `uploader_selectors.py`, `HUONG_DAN.md`, `README.md`, `.env.example`, `__init__.py`

**Không ship:** `.env`, `nd_storage_state.json`, `.venv/`, `registry.sqlite3`, `logs/`, `output/`, `runs/`, `downloads/`, `upload_runs/`, `__pycache__/`, file debug/screenshot, `CLAUDE.md`, `RULE_TONG_KET_3_LOAI_VAN_BAN.md`

## Checklist phát hành standalone

### Kiểm tra trước khi zip

- Chạy `build_standalone_release.ps1` → tạo thư mục `_release/upload_lab/` sạch
- `run_ui_pyqt6.bat` mở được bootstrap (launcher chính)
- `run_ui.bat` mở được bootstrap (legacy fallback)
- `.env.example` có `ND_STORAGE_STATE_PATH=nd_storage_state.json`
- `requirements.txt` không còn `pywin32`
- UI không còn nút `.doc → .docx`
- Tab upload có nút `Cấu hình uploader`
- `HUONG_DAN.md` đã cập nhật cho flow standalone với PyQt6

### Acceptance nhanh

| Kịch bản | Kết quả mong đợi |
|---|---|
| Máy có Python sẵn | `run_ui_pyqt6.bat` mở UI thành công |
| Máy chưa có Python | Launcher fallback cài Python tự động |
| Batch scan `.docx` + `.doc` | Đọc được cả 2 định dạng |
| Cấu hình uploader lần đầu | Đăng nhập tạo được `nd_storage_state.json` |
| Dry-run với Excel | Đối chiếu và lọc duplicate trước khi upload |

## Cấu hình extract_contract.py

Các hằng số mặc định ở đầu file — chỉnh khi đổi văn phòng:

```python
DEFAULT_CCV = "Phạm Minh Chi"      # Công chứng viên mặc định
DEFAULT_THU_KY = "Nguyễn Nhật Minh"
CONTRACT_YEAR = "2026"
```

## Rule trich xuất tài sản (3 loại văn bản)

Chi tiết đầy đủ: [RULE_TONG_KET_3_LOAI_VAN_BAN.md](RULE_TONG_KET_3_LOAI_VAN_BAN.md)

**Tóm tắt nguyên tắc chung:**
- Tài sản `quyền sử dụng đất` → dùng 1 rule chung cho cả 3 loại
- Start anchor: `quyền sử dụng đất ... có địa chỉ tại`
- End: hết block thông tin GCN/ngày cấp/cập nhật biến động; dừng trước marker chuyển ý (`Điều 2`, `Bằng hợp đồng này`, v.v.)
- Hợp đồng chuyển nhượng: block đầy đủ
- Cam kết tài sản riêng: gần như giống chuyển nhượng
- Hủy bỏ/sửa đổi/bổ sung: ngắn hơn, mang tính tham chiếu

## Rule hồ sơ thế chấp ngân hàng

- Hồ sơ thế chấp thường **không có bản Word đầy đủ của hợp đồng**, chỉ có 1 file tóm tắt/lời chứng do ngân hàng giữ bản chính.
- Không giả định cấu trúc `Bên A / Bên B`; ưu tiên nhận diện theo nhãn **`Bên thế chấp`** và **`Bên nhận thế chấp`**.
- `Bên nhận thế chấp` thường là **pháp nhân/ngân hàng**, cần giữ cả:
  - tên tổ chức
  - địa chỉ đăng ký
  - thông tin người đại diện ký
- Nếu file tóm tắt chỉ nêu loại tài sản ở tiêu đề như `Hợp đồng thế chấp quyền sử dụng đất` mà không có block tài sản chi tiết, cho phép fallback:
  - `quyền sử dụng đất`
  - hoặc `quyền sử dụng đất và tài sản gắn liền với đất`
- Với file `.docx` có bảng, phải giữ **đúng thứ tự paragraph/table** khi đọc để không làm lệch phần đương sự của hồ sơ thế chấp.

## Rule hồ sơ thừa kế

- `Văn bản phân chia di sản` không dùng `Bên A / Bên B`; `duong_su` là **nhóm người hưởng di sản ký ở phần mở đầu**, thường bắt đầu từ dòng `Chúng tôi là những người được hưởng di sản ...`.
- Với `Văn bản phân chia di sản`, block `tai_san` nên lấy từ mô tả tài sản thực tế như `quyền sử dụng đất ... có địa chỉ tại` và **dừng trước** các phần:
  - `Người thừa kế`
  - `Nội dung phân chia di sản`
  - `Bằng Văn bản này`
  - `Lời chứng`
- `Văn bản từ chối nhận di sản` thường có **một người lập văn bản**, mở đầu bằng `Tôi là:`; `duong_su` nên gắn nhãn dạng `NGƯỜI TỪ CHỐI NHẬN DI SẢN`, không ép sang `Bên A / Bên B`.
- Với `Văn bản từ chối nhận di sản`, `tai_san` có thể gồm **nhiều tài sản** (`Tài sản thứ nhất`, `Tài sản thứ hai`, ...), nên giữ trọn block tài sản và **dừng trước** phần tuyên bố từ chối/cam đoan/lời chứng.
- Số công chứng nhóm thừa kế có thể xuất hiện dạng:
  - `2433.2025/PCDS/CCGD`
  - `2233.2025/TCDS/CCGD`
  Khi điền vào web field `so_cong_chung`, chuẩn hóa về `2433/2025`, `2233/2025`.

## Quy ước khi sửa code

- **Không đổi tên các hàm public** trong `batch_scan.py` và `playwright_uploader.py` — UI và tests phụ thuộc trực tiếp.
- **Không thay đổi schema `registry.sqlite3`** nếu không bắt buộc; nếu thay đổi, cần migration script.
- **Selectors web form** nằm hoàn toàn trong `uploader_selectors.py` — chỉnh tại đây khi web Nam Định thay đổi giao diện.
- UI PyQt6 dùng **Qt signals** cho mọi cập nhật từ worker thread về main thread; không gọi widget trực tiếp từ thread.
- Log message phải có prefix `[TAG]` (ví dụ `[BATCH]`, `[UPLOAD]`, `[ERROR]`) để log viewer highlight đúng màu.

## Troubleshooting nhanh

| Triệu chứng | Cách xử lý |
|---|---|
| Thiếu Python/Playwright | Chạy lại `run_ui_pyqt6.bat` |
| Thiếu `openpyxl` | Chạy lại `run_ui_pyqt6.bat` |
| Không upload được, chưa đăng nhập | Mở `Cấu hình uploader` → `Lưu và đăng nhập` |
| Không đối chiếu được Excel | Kiểm tra file export và cột A |
| PyQt6 không hiển thị đúng DPI | Kiểm tra Windows Display Scale, thêm `QApplication.setHighDpiScaleFactorRoundingPolicy` nếu cần |
