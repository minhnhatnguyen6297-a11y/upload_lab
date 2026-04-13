# Hướng dẫn sử dụng Upload Tool

## Chạy lần đầu

Double-click `run_ui_pyqt6.bat` (launcher chính).

Launcher sẽ tự động:
- Tìm Python 3.10+ sẵn có
- Nếu chưa có thì thử cài qua `winget`, nếu thất bại sẽ tải installer Python từ `python.org`
- Tạo `.venv` riêng trong thư mục tool
- Cài dependency từ `requirements.txt`
- Cài `playwright chromium`
- Mở giao diện

Lưu ý:
- Lần đầu cần Internet
- Không cần Microsoft Word/Office
- Mọi dữ liệu runtime được tạo ngay trong thư mục tool: `output`, `runs`, `logs`, `downloads`, `upload_runs`, `registry.sqlite3`

> Nếu máy đang dùng UI Tkinter cũ: double-click `run_ui.bat` (fallback legacy).

Nếu cần tạo bộ phát hành sạch:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_standalone_release.ps1
```

## Cấu hình uploader lần đầu

Tab `Upload hồ sơ` sẽ tự nhắc cấu hình nếu:
- Chưa có `.env`
- Thiếu `ND_USERNAME` hoặc `ND_PASSWORD`
- Chưa có `nd_storage_state.json`

Flow dùng:
1. Mở tab `Upload hồ sơ`
2. Bấm `Cấu hình uploader`
3. Điền `Base URL`, `Login URL`, `Create URL`, tài khoản, mật khẩu
4. Bấm `Lưu và đăng nhập`
5. Tool sẽ tự đăng nhập và tạo `nd_storage_state.json`

File `.env` được tạo từ `.env.example` nếu thiếu.

## Quét hồ sơ (Tab 1)

Tab `Quét hồ sơ`:
- Browse folder tổng
- Nhập `modified since` nếu cần (`YYYY-MM-DD` hoặc `DD/MM/YYYY`)
- Tick `Full rescan` nếu muốn quét lại toàn bộ
- Điều chỉnh độ sâu folder (mặc định 3)
- Bấm `Chạy Batch Scan`

Batch scan:
- Hỗ trợ cả `.docx` và `.doc`
- Bỏ qua `~$*.docx` và `~$*.doc`
- Tìm số công chứng trong nội dung file Word
- Trích xuất JSON
- Ghi output vào `output/`
- Ghi manifest vào `runs/`
- Ghi registry vào `registry.sqlite3`

## Upload hồ sơ (Tab 2)

Luồng dùng:
1. Chạy batch scan trước để tạo `manifest`
2. Mở tab `Upload hồ sơ`
3. Chọn file manifest trong `runs/`
4. Chọn file Excel đối chiếu hoặc bấm `Tải từ web`
5. Bấm `Refresh Queue`
6. Bấm `Start Dry-run`

Tool sẽ:
- Đọc queue theo `run_id` trong manifest
- Đối chiếu cột A của file Excel số công chứng
- Loại các hồ sơ trùng số đã tồn tại trên web
- Mở từng tab Playwright và dừng trước nút `Lưu`

Sau khi đã tự kiểm tra và bấm `Lưu` trên web:
- Quay lại UI
- Chọn các record đã xong
- Bấm `Finalize Selected`

Nếu vẫn còn record chưa xử lý:
- Bấm `Start Dry-run` lại trên cùng manifest
- Tool sẽ lấy chunk tiếp theo (tối đa 10 hồ sơ mỗi lần)

## File cấu hình

Mẫu `.env.example`:

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
| `output/<so_cong_chung>_<hash>.json` | Kết quả trích xuất từng hợp đồng |
| `runs/<timestamp>.json` | Manifest của mỗi lần batch scan |
| `registry.sqlite3` | Registry toàn bộ records + trạng thái upload |
| `logs/playwright_uploader.log` | Log Playwright uploader |
| `upload_runs/<timestamp_runid>/` | Artifact dry-run (screenshot, debug JSON, trace) |

## Troubleshooting nhanh

| Triệu chứng | Cách xử lý |
|---|---|
| Thiếu Python/Playwright | Chạy lại `run_ui_pyqt6.bat` |
| Thiếu `openpyxl` | Chạy lại `run_ui_pyqt6.bat` |
| Không upload được, chưa đăng nhập | Mở `Cấu hình uploader` → `Lưu và đăng nhập` |
| Không đối chiếu được Excel | Kiểm tra file export và cột A |
| UI hiển thị sai DPI trên màn hình HiDPI | Kiểm tra Windows Display Scale |
