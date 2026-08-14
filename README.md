# Upload Lab — System Specification & Architecture

Hệ thống độc lập tự động hóa nghiệp vụ cho Văn phòng Công chứng: Đọc & phân tích hồ sơ Word (`.doc`/`.docx`) $\rightarrow$ Chuẩn hóa & trích xuất dữ liệu form công chứng $\rightarrow$ Đối chiếu sổ công chứng Excel từ web $\rightarrow$ Điền tự động & upload qua Playwright.

---

## 1. Kiến trúc luồng nghiệp vụ (End-to-End Workflow)

```mermaid
flowchart LR
    A[Hồ sơ Word .doc/.docx] -->|Stage 1: Scan & Extract| B[(output/ JSON & SQLite)]
    C[Web Sổ Công chứng] -->|Stage 2: Audit & Reconcile| D{So khớp Danh sách}
    B --> D
    D -->|Chưa có trên web| E[Stage 3: Playwright Uploader]
    E -->|Dry-run / Finalize| C
```

### Giai đoạn 1: Quét & Trích xuất (`batch_scan.py` + `extract_contract.py`)
1. **Đọc tệp tin**:
   - `.docx`: Đọc bằng `python-docx`, bảo toàn thứ tự đoạn văn và bảng biểu (`table`) để tránh trộn lẫn Bên A / Bên B.
   - `.doc`: Đọc bằng Windows IFilter (`query.dll`) không cần Microsoft Word.
2. **Phân loại văn bản (`_detect_document_kind_and_title`)**:
   - Phân loại theo tiêu đề/header thành các nhóm: `transfer_contract` (Chuyển nhượng), `asset_commitment` (Cam kết tài sản riêng), `mortgage_contract` (Thế chấp), `inheritance_partition` (Phân chia di sản), `inheritance_refusal` (Từ chối di sản), `generic`.
3. **Bóc tách trường dữ liệu**:
   - Đương sự (`duong_su`, `nguoi_yeu_cau`), Tài sản (`tai_san`, `loai_tai_san`), Số công chứng (`so_cong_chung`), Ngày công chứng, Công chứng viên, Nhóm hợp đồng.
4. **Lưu trữ**:
   - Ghi JSON chi tiết vào thư mục `output/<so_cc>_<hash>.json`.
   - Ghi bản ghi vào `registry.sqlite3` (trạng thái ban đầu: `SCANNED`).
   - Xuất file manifest chạy theo đợt vào `runs/<timestamp>.json`.

### Giai đoạn 2: Đối chiếu & Phân loại hàng đợi (`ui/services/`)
1. **Kiểm toán Sổ Excel (`contract_book_audit.py`)**:
   - Đọc danh sách số công chứng đã có trên web (tải qua Playwright hoặc nạp file Excel có sẵn).
   - Chuẩn hóa số công chứng về định dạng `xxx/yyyy`.
   - Tính toán dải số liên tục (min - max) và phát hiện các **số bị hở (thiếu)** theo từng năm.
2. **Phân loại hàng đợi Upload (`scan_classification_service.py`)**:
   - So khớp danh sách quét từ folder với danh sách Excel trên web:
     - `chua co trong Excel`: Tự động đánh dấu tick cần upload.
     - `da co trong Excel`: Bỏ chọn, tránh upload trùng.
     - `sai format` / `sai nam` / `khong co so`: Cảnh báo để người dùng kiểm tra lại file Word.

### Giai đoạn 3: Tự động hóa Upload (`playwright_uploader.py` + `uploader_selectors.py`)
1. **Điều khiển trình duyệt Chromium**:
   - Đăng nhập vào hệ thống phần mềm quản lý công chứng tỉnh Nam Định.
   - Lưu trữ/Tái sử dụng session bằng `nd_storage_state.json`.
2. **Điền biểu mẫu (Web Form Automation)**:
   - Điều hướng vào trang tạo mới hồ sơ công chứng.
   - Tự động điền: Tên hợp đồng, Số công chứng, Ngày công chứng, Nhóm HĐ (dropdown), Loại tài sản (radio/dropdown), Công chứng viên, Người yêu cầu, Đương sự (Textarea), Tài sản (Textarea).
3. **Chế độ thực thi**:
   - **Dry-run**: Tự động điền toàn bộ dữ liệu, dừng lại trước nút *Lưu* để người dùng kiểm tra trực quan trên trình duyệt.
   - **Finalize / Upload**: Xác nhận lưu thành công và cập nhật trạng thái `UPLOADED` vào `registry.sqlite3`.

---

## 2. Quy chuẩn Dữ liệu Web Form (Data Schema)

| Trường Web Form | Quy tắc & Nguồn trích xuất | Ví dụ giá trị |
|---|---|---|
| `ten_hop_dong` | Chuẩn hóa theo loại văn bản quy chuẩn | `Hợp đồng chuyển nhượng quyền sử dụng đất` |
| `so_cong_chung` | Chuẩn hóa rút gọn `xxx/yyyy` (bỏ hậu tố nghiệp vụ) | `428/2026` (từ `428/2026/CCGD`) |
| `ngay_cong_chung` | Ngày lập hợp đồng trong lời chứng hoặc tiêu đề | `15/04/2026` |
| `nhom_hop_dong` | Ánh xạ danh mục dropdown hệ thống web | `Chuyển nhượng - Mua bán`, `Cầm cố - Thế chấp - Vay` |
| `loai_tai_san` | Xác định dựa trên chi tiết tài sản đính kèm đất | `Đất đai có tài sản`, `Đất đai không có tài sản` |
| `cong_chung_vien` | Nhận diện tên CCV ký lời chứng (hoặc mặc định) | `Phạm Minh Chi` |
| `thu_ky` | Cán bộ soạn thảo mặc định | `Nguyễn Nhật Minh` |
| `nguoi_yeu_cau` | Ưu tiên Bên nhận / Bên cam kết / Đại diện NH | `1. Ông Nguyễn Văn B (CCCD: 0360...)` |
| `duong_su` | Bóc tách theo khối Bên A / Bên B hoặc Nhóm người | Gồm Họ tên, Ngày sinh, CCCD/CMND, Địa chỉ cư trú |
| `tai_san` | Đoạn mô tả thửa đất, diện tích, GCN, dừng trước cam đoan | `Quyền sử dụng đất tại xã A... Thửa số 10...` |

> [!NOTE]
> Chi tiết toàn bộ quy tắc regex nhận diện và điểm bắt đầu/kết thúc của từng loại văn bản xem tại: [`docs/regex-rules.md`](file:///D:/upload_lab_repo/docs/regex-rules.md).

---

## 3. Cấu trúc Codebase

```text
upload_lab/
|-- run.bat                         # 1-Click launcher cho người dùng
|-- run_ui.bat                      # Bootstrap shell: kiểm tra Python & gọi bootstrap_ui.py
|-- bootstrap_ui.py                 # Tự tạo .venv, cài dependencies & mở UI
|-- ui_runner.py                    # Entry point khởi chạy PySide6 UI
|-- extract_contract.py             # Trích xuất Word sang JSON web form
|-- batch_scan.py                   # Quét folder, xuất manifest, ghi SQLite
|-- playwright_uploader.py          # Script điều khiển trình duyệt Playwright
|-- uploader_selectors.py           # Selectors định vị phần tử web form
|-- build_standalone_release.ps1    # Script đóng gói bản phát hành độc lập
|-- docs/
|   `-- regex-rules.md              # Catalog quy tắc regex chuẩn cho các loại văn bản
|-- ui_qt/                          # Giao diện Qt/PySide6 (Window, Forms, Widgets, Workers)
|-- ui/services/                    # Nghiệp vụ kiểm toán Excel, phân loại scan & upload
|-- tests/                          # 92 unit tests bao phủ toàn bộ luồng
`-- regex_review_samples/           # Thư mục chứa sample test và báo cáo đánh giá regex
```

---

## 4. Vận hành & Kiểm thử

- **Khởi chạy ứng dụng**:
  ```cmd
  run.bat
  ```
- **Chạy toàn bộ Unit Tests**:
  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover -s tests
  ```
- **Đánh giá Regex với mẫu thực tế**:
  Đặt file Word vào `regex_review_samples/input/` và chạy:
  ```powershell
  .\.venv\Scripts\python.exe .\review_regex_samples.py
  ```
  *(Kết quả được ghi vào `regex_review_samples/reports/` dạng CSV, JSON và XLSX).*
