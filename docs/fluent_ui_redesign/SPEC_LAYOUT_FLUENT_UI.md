# Upload Lab — Fluent UI Redesign Specification (Windows 11)

Tài liệu đặc tả thiết kế lại toàn diện giao diện (UI/UX) cho ứng dụng desktop **Upload Lab**, áp dụng ngôn ngữ thiết kế **Microsoft Fluent Design System 2.0 (WinUI 3)** chuẩn Windows 11.

---

## 1. So sánh & Khuyến nghị Model: Gemini 3.7 Flash vs Gemini 3.1 Pro

| Tiêu chí | Gemini 3.7 Flash (Thinking / Hybrid Reasoning) | Gemini 3.1 Pro (Deep Heavy Reasoning) |
|---|---|---|
| **Tốc độ phản hồi (Latency & Throughput)** | **Rất nhanh (Real-time iteration)** | Chậm hơn đáng kể (Thời gian chờ lâu) |
| **Khả năng thiết kế UI & Styling (QSS / PySide6)** | **Xuất sắc**, tạo mã giao diện sạch, đúng chuẩn design token | Rất tốt, nhưng có xu hướng viết dài dòng |
| **Quy trình Pair-Programming / Refactoring** | **Tối ưu nhất**: Thử nghiệm, tinh chỉnh layout, sửa lỗi CSS/QSS và chạy test liên tục không ngắt quãng | Phù hợp hơn cho các bài toán phân tích kiến trúc trừu tượng quy mô lớn |
| **Tool Calling & Tương tác tệp tin** | Độ chính xác cao, tự điều chỉnh suy nghĩ (thinking) linh hoạt | Rất chính xác |

> [!TIP]
> **Khuyến nghị chính thức**: Sử dụng **Gemini 3.7 Flash** cho toàn bộ dự án từ đầu. Với khả năng suy luận kết hợp (thinking capability) cùng tốc độ xử lý nhanh, Gemini 3.7 Flash giúp quá trình thiết kế, xuất mã giao diện, preview và tinh chỉnh giao diện diễn ra liền mạch, không bị trễ thời gian chờ đợi.

---

## 2. Hình ảnh Thiết kế Mẫu (Rendered UI Mockups)

Dưới đây là các bản vẽ giao diện mẫu đã được render theo chuẩn Microsoft Fluent UI:

````carousel
![Giao diện Quản lý & Audit Sổ Công Chứng (Light Theme)](./mockup_1_excel_audit.jpg)
<!-- slide -->
![Giao diện Quét Folder & Hàng Đợi Upload Tự Động (Light Theme)](./mockup_2_folder_upload.jpg)
<!-- slide -->
![Giao diện Cấu hình Hệ thống & Trình duyệt Upload (Dark Mode)](./mockup_3_dark_mode.jpg)
````

---

## 3. Đánh giá hiện trạng & Giải pháp khắc phục

```mermaid
graph TD
    subgraph Hiện Trạng (Cũ)
        A1[Thanh Tab ngang kiểu cũ, cứng nhắc]
        A2[Nút bấm to nhỏ lộn xộn, rải rác trên nhiều dòng]
        A3[3 Bảng chèn ép trong 1 thanh cuộn dọc chật hẹp]
        A4[Khung Log chiếm diện tích cố định làm mất không gian làm việc]
    end
    subgraph Giải Pháp Fluent UI 2.0
        B1[Sidebar Navigation Rail chuẩn Windows 11 với Icon & Acrylic]
        B2[CommandBar & Card Action có phân cấp: Primary Accent, Secondary, Badge]
        B3[KPI Stat Cards + DataGrid hiện đại với Tag phân loại trực quan]
        B4[Collapsible Log Drawer thu gọn thông minh hoặc Tab chuyên biệt]
    end
    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
```

| Thành phần | Hiện trạng (Cũ) | Cải tiến theo Fluent UI 2.0 |
|---|---|---|
| **Điều hướng (Navigation)** | Dùng `QTabWidget` ngang cổ điển, thiếu không gian cho tính năng mở rộng | **Navigation Rail (Sidebar)** bên trái với icon Fluent, hiệu ứng hover mượt mà |
| **Bố cục Action (Buttons)** | Nút bấm đặt tràn lan thành các cụm dài, không rõ nút chính (Primary) / phụ (Secondary) | Chuẩn hóa **Command Bar** & **Card Layout**, nhóm thao tác theo ngữ cảnh |
| **Hiển thị Thống kê** | 1 dòng text đơn điệu (`Excel=0 \| hop_le=0 \| thieu=0...`) | **4 Thẻ KPI Stat Cards** nổi bật với số liệu lớn và màu chỉ báo (Xanh lá, Vàng, Đỏ) |
| **Bảng dữ liệu (Tables)** | 3 bảng xếp chồng dọc bằng `QSplitter`, tạo nhiều thanh cuộn gây rối mắt | Gộp thành **Fluent DataGrid** duy nhất với bộ lọc nhanh theo Tag/Tab |
| **Khu vực Log** | Khung log cố định ở chân trang chiếm 30% màn hình mọi lúc | **Collapsible Log Drawer** (có thể gập/mở bằng 1 click) hoặc trang Log riêng |

---

## 4. Kiến trúc Thông tin & Bố cục mới (Information Architecture)

```mermaid
flowchart LR
    Main[Cửa sổ chính Upload Lab - Fluent UI] --> Nav[Navigation Rail bên trái]
    Nav --> Page1[1. Audit Sổ Công Chứng]
    Nav --> Page2[2. Quét & Upload Hồ Sơ]
    Nav --> Page3[3. Cấu hình & Trình duyệt]
    Nav --> Page4[4. Nhật ký Hệ thống]

    Page1 --> P1_Filter[Card Lọc ngày & Nạp Excel]
    Page1 --> P1_KPI[4 Thẻ KPI: Tổng / Hợp lệ / Thiếu / Lỗi]
    Page1 --> P1_Table[Fluent DataGrid danh sách số]

    Page2 --> P2_Scan[Card Chọn Thư Mục & Phân Công CCV/Thư Ký]
    Page2 --> P2_Bar[Fluent Progress Bar + Trạng thái]
    Page2 --> P2_Cmd[Command Bar: Chọn thiếu / Lọc lỗi / Upload]
    Page2 --> P2_Queue[Bảng Hàng Đợi Upload Checkbox]

    Page3 --> P3_Acc[Card Tài khoản & URL Web]
    Page3 --> P3_Eng[Card Trạng thái Playwright & Tùy chọn]
```

### Chi tiết các phân hệ màn hình

#### Màn hình 1: Audit Sổ Công Chứng (Excel Audit)
- **Top Card — Điều khiển**:
  - Dải chọn ngày (Từ ngày — Đến ngày) dạng `Fluent DatePicker`.
  - Nút chính `Tải Excel từ Web` (Primary Accent Button - Xanh dương Fluent).
  - Nút phụ `Chọn tệp Excel` (Secondary Outlined Button kèm đường dẫn tệp rút gọn).
- **Metric Cards (KPI Banner)**:
  - Card 1: **Tổng số** (Total) — Xanh lam nhạt.
  - Card 2: **Hợp lệ** (Valid) — Xanh lá cây (Badge `Success`).
  - Card 3: **Thiếu số** (Missing gaps) — Màu hổ phách/cam (Badge `Warning`).
  - Card 4: **Lỗi / Trùng** (Issues) — Đỏ thẫm (Badge `Error`).
- **Data Table**:
  - Bảng Fluent Table với các cột: `Số Công Chứng`, `Ngày Ký`, `Tên Hợp Đồng / Đương sự`, `Trạng Thái`.
  - Hỗ trợ click vào từng Card KPI để tự động lọc nhanh dữ liệu trong bảng.

#### Màn hình 2: Quét & Upload Hồ Sơ (Folder Scan & Upload)
- **Top Card — Cấu hình quét & Nhân sự**:
  - Thanh chọn thư mục chứa file Word `.doc`/`.docx` + Nút `Duyệt Thư Mục` + Nút `Bắt đầu Quét`.
  - Nhóm chọn nhân sự: `Công chứng viên` (Dropdown) và `Thư ký` (Dropdown) có nút làm mới danh sách.
- **Progress Section**:
  - Thanh tiến trình Fluent bo góc 4px, hiển thị phần trăm mượt mà và text trạng thái động.
- **Command Bar thao tác hàng loạt**:
  - Nút lọc: `Chọn tất cả`, `Bỏ chọn`, `Chỉ chọn số thiếu trên Excel`, `Lọc hồ sơ lỗi`.
  - Nút hành động chính: `Bắt đầu Upload (N hồ sơ đã chọn)` (Primary Button to, nổi bật).
  - Nút `Dừng` (Danger Button màu đỏ khi đang chạy).
- **Hàng đợi Upload (Upload Queue Grid)**:
  - Cột 1: Checkbox chọn từng dòng.
  - Cột 2: Số công chứng chuẩn hóa (`xxx/yyyy`).
  - Cột 3: Loại hợp đồng & Loại tài sản.
  - Cột 4: Đương sự chính (Bên A / Bên B).
  - Cột 5: Trạng thái đối chiếu (Pill tags: `Chưa có trên Web`, `Đã có`, `Lỗi format`).
  - Cột 6: Thao tác nhanh (Xem JSON, Mở file Word gốc).

#### Màn hình 3: Cấu hình Hệ thống & Trình duyệt (Settings)
- Quản lý tài khoản đăng nhập web quản lý công chứng (`.env`).
- Kiểm tra trạng thái Playwright Browser Engine (`Sẵn sàng` / `Cần cài đặt`).
- Tùy chọn nâng cao: Kích thước batch upload (slider), Chế độ Headless, Tự động mở lại trình duyệt khi ngắt kết nối.

#### Màn hình 4: Nhật ký Hệ thống (Logs & Diagnostics)
- Cửa sổ Console phong cách Terminal Windows 11 với cú pháp phân loại màu (`INFO` xanh, `WARN` vàng, `ERROR` đỏ, `SUCCESS` xanh lá).
- Nút `Xóa Log`, `Xuất File Log`, `Mở Thư Mục Chứa Log`.

---

## 5. Hệ thống Design Tokens (Fluent Design 2)

```css
/* Color Tokens */
--fluent-bg-canvas: #F3F3F3;         /* Màu nền tổng thể Windows 11 (Mica base) */
--fluent-bg-card: #FFFFFF;           /* Nền Card container */
--fluent-bg-card-subtle: #FAFAFA;    /* Nền phụ */
--fluent-accent: #0078D4;            /* Primary Windows Blue */
--fluent-accent-hover: #106EBE;
--fluent-accent-pressed: #005A9E;
--fluent-text-primary: #1C1C1C;      /* Chữ chính */
--fluent-text-secondary: #5C5C5C;    /* Chữ phụ / nhãn */
--fluent-border: #E5E5E5;            /* Đường viền mỏng */
--fluent-border-focus: #0078D4;      /* Viền focus 2px */

/* Status Colors */
--status-success: #107C41;           /* Xanh lá chuẩn MS */
--status-warning: #D83B01;           /* Cam cảnh báo */
--status-error: #A80000;             /* Đỏ lỗi */
--status-info: #0078D4;              /* Xanh thông tin */

/* Typography & Geometry */
--font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
--radius-card: 8px;                  /* Bo góc Card */
--radius-control: 5px;               /* Bo góc Button, Input */
--radius-pill: 12px;                 /* Bo góc Badge/Tag */
```

---

## 6. Lựa chọn Công nghệ Triển khai (Tech Stack Options)

| Phương án | Chi tiết công nghệ | Ưu điểm | Nhược điểm |
|---|---|---|---|
| **Phương án 1 (Khuyến nghị)** | **PySide6 + PySide6-Fluent-Widgets (`qfluentwidgets`)** | - Chuẩn 100% Microsoft Fluent Design 2 (Mica, Acrylic, Navigation, InfoBar, Flyout).<br>- Tương thích hoàn toàn với kiến trúc Python, QThread, Playwright hiện có.<br>- Không cần viết lại backend. | Cần thêm 1 dependency (`PySide6-Fluent-Widgets`). |
| **Phương án 2** | **PySide6 + Custom Pure Fluent QSS / Custom Widgets** | - Hoàn toàn độc lập, không thêm dependency ngoài PySide6.<br>- Tùy biến tự do 100%. | Cần nhiều code tùy biến QSS hơn. |

---

## 7. Kế hoạch Thực hiện Tiếp theo (Action Plan)

1. **Bước 1**: Nhận phản hồi và phê duyệt từ Người dùng về Spec và các ảnh mẫu Render trên.
2. **Bước 2**: Xác nhận lựa chọn phương án công nghệ (Phương án 1 dùng `PySide6-Fluent-Widgets` hay Phương án 2 dùng `Pure PySide6 Custom Fluent`).
3. **Bước 3**: Triển khai mã nguồn cấu trúc UI mới (`ui_qt/`), xây dựng Navigation Sidebar, các Card & Table theo layout chuẩn.
4. **Bước 4**: Kết nối đầy đủ các Worker, Signal, Threading và kiểm thử toàn bộ 92 unit tests đảm bảo ổn định 100%.
