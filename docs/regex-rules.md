# Regex Rule Catalog — Quy chuẩn Trích xuất Văn bản Công chứng

Catalog này tập hợp và chuẩn hóa toàn bộ quy tắc trích xuất dữ liệu từ file Word (`.doc`, `.docx`) sang JSON web form trong `extract_contract.py`.

---

## 1. Nguyên tắc chung

### 1.1. Đọc dữ liệu
- Nguồn dữ liệu là file Word `.doc` và `.docx`.
- `.docx` đọc có cấu trúc (bảo toàn thứ tự đoạn văn và bảng biểu table để tránh trộn lẫn Bên A / Bên B).
- `.doc` đọc qua Windows IFilter dạng plain text.
- Tầng regex tập trung nhận diện tiêu đề, phân tách đương sự, bóc tách tài sản và chuẩn hóa trường sau khi đã đọc text.

### 1.2. Chuẩn hóa Số công chứng
- Dạng raw thường gặp:
  - `428/2026/CCGD` hoặc `428.2026/CCGD` $\rightarrow$ Chuẩn hóa web: `428/2026`
  - `2433.2025/PCDS/CCGD` $\rightarrow$ Chuẩn hóa web: `2433/2025`
  - `2233.2025/TCDS/CCGD` $\rightarrow$ Chuẩn hóa web: `2233/2025`
- Nguyên tắc: Giữ số thứ tự và năm `xxx/yyyy`, loại bỏ hậu tố mã nghiệp vụ khi so khớp và điền web form.

### 1.3. Nhận diện Loại tài sản (`loai_tai_san`)
- Nếu có `quyền sử dụng đất`:
  - Có chi tiết nhà ở / công trình xây dựng (diện tích sàn, kết cấu, số tầng, cấp công trình...): **`Đất đai có tài sản`**
  - Chỉ có thông tin thửa đất / tờ bản đồ / diện tích đất: **`Đất đai không có tài sản`**
  - *Lưu ý*: Loại bỏ nhiễu tiêu đề chuẩn của phôi sổ ("Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất") trước khi kiểm tra chi tiết tài sản gắn liền.
- Ô tô / Xe máy: **`Ô tô - Xe máy`**
- Không có tài sản: **`Không có tài sản`**

---

## 2. Quy tắc chi tiết theo từng loại văn bản

### 2.1. Hợp đồng chuyển nhượng (`DOC_KIND_TRANSFER`)
- **Nhóm HĐ**: `Chuyển nhượng - Mua bán`
- **Tiêu đề canonical**: `Hợp đồng chuyển nhượng quyền sử dụng đất` (hoặc kèm tài sản gắn liền với đất)
- **Đương sự**:
  - `Bên A`: Bên chuyển nhượng
  - `Bên B`: Bên nhận chuyển nhượng
  - Người yêu cầu công chứng: Ưu tiên Bên B (Bên nhận chuyển nhượng).
- **Tài sản**:
  - *Điểm bắt đầu*: `quyền sử dụng đất ... có địa chỉ tại:` hoặc `Đối tượng của Hợp đồng này là...`
  - *Điểm kết thúc*: Dừng trước `1.2`, `Điều 2`, `Giá chuyển nhượng`, `Phương thức thanh toán`, `Bằng Hợp đồng này`.

### 2.2. Văn bản cam kết tài sản riêng (`DOC_KIND_ASSET_COMMITMENT`)
- **Nhóm HĐ**: `Thoả thuận - Cam kết`
- **Tiêu đề canonical**: `Văn bản cam kết tài sản riêng`
- **Đương sự**:
  - Gồm cả 2 vợ chồng (Người chồng - Ông ... / Người vợ - Bà ...).
  - Người yêu cầu công chứng: Người đứng tên cam kết tài sản riêng.
- **Tài sản**:
  - *Điểm bắt đầu*: `quyền sử dụng đất ... có địa chỉ tại:` hoặc `hiện đang sở hữu Tài Sản là` / `Tài Sản là`.
  - *Điểm kết thúc*: Dừng trước `Bằng văn bản này chúng tôi xác định`, `Hai vợ chồng chúng tôi cam kết`, `Chúng tôi công nhận`.

### 2.3. Văn bản thỏa thuận hủy bỏ / sửa đổi / bổ sung (`DOC_KIND_TRANSFER_CANCELLATION`)
- **Nhóm HĐ**: `Thoả thuận - Cam kết` (hoặc `Phụ lục hợp đồng - văn bản sửa đổi`)
- **Tiêu đề canonical**: `Văn bản thỏa thuận về việc hủy bỏ hợp đồng chuyển nhượng quyền sử dụng đất`
- **Đương sự**: 2 bên tham gia thỏa thuận hủy bỏ.
- **Tài sản**: Đoạn trích tham chiếu thông tin thửa đất/GCN từ hợp đồng gốc, dừng trước `và được Công chứng viên chứng nhận`, `số công chứng`.

### 2.4. Hợp đồng thế chấp (`DOC_KIND_MORTGAGE`)
- **Nhóm HĐ**: `Cầm cố - Thế chấp - Vay`
- **Tiêu đề canonical**: `Hợp đồng thế chấp quyền sử dụng đất` (hoặc kèm tài sản gắn liền với đất)
- **Đương sự**:
  - `Bên A`: Bên thế chấp (cá nhân/hộ gia đình).
  - `Bên B`: Bên nhận thế chấp (thường là Ngân hàng / Pháp nhân / Chi nhánh + Người đại diện ký).
  - Người yêu cầu công chứng: Người đại diện ngân hàng (Bên B).
- **Tài sản**:
  - Trích xuất thông tin thửa đất / GCN từ phần mô tả tài sản hoặc trích xuất tối thiểu `Quyền sử dụng đất`.

### 2.5. Văn bản phân chia di sản (`DOC_KIND_INHERITANCE_PARTITION`)
- **Nhóm HĐ**: `Thừa kế (khai nhận - phân chia di sản thừa kế )`
- **Tiêu đề canonical**: `Văn bản phân chia di sản`
- **Đương sự**:
  - Nhóm người ký ở phần mở đầu: `NHỮNG NGƯỜI HƯỞNG DI SẢN` (bắt đầu từ `Chúng tôi là những người được hưởng di sản...`).
  - Dừng trước `Người để lại di sản:`, `Chúng tôi tự nguyện lập Văn bản này`.
  - *Không đưa người để lại di sản hoặc giải trình phả hệ vào danh sách đương sự*.
- **Tài sản**:
  - *Điểm bắt đầu*: Sau heading `Di sản:` / `Di sản của ... để lại là:` hoặc dòng `quyền sử dụng đất ... có địa chỉ tại:`.
  - *Điểm kết thúc*: Dừng trước `Người thừa kế:`, `Những người thừa kế`, `Nội dung phân chia di sản`, `Bằng Văn bản này`, `Lời chứng`.

### 2.6. Văn bản từ chối nhận di sản (`DOC_KIND_INHERITANCE_REFUSAL`)
- **Nhóm HĐ**: `Từ chối nhận di sản thừa kế`
- **Tiêu đề canonical**: `Văn bản từ chối nhận di sản`
- **Đương sự**:
  - Đơn phương 1 người: `NGƯỜI TỪ CHỐI NHẬN DI SẢN` (bắt đầu sau `Tôi là:`).
  - Dừng trước `Nay, tôi tự nguyện lập Văn bản này`, `Theo quy định của pháp luật`.
- **Tài sản**:
  - Hỗ trợ đơn tài sản hoặc đa tài sản (`1. Tài sản thứ nhất:`, `2. Tài sản thứ hai:`...).
  - *Điểm kết thúc*: Dừng trước `Bằng Văn bản này, tôi ... từ chối nhận kỷ phần thừa kế`, `Tôi xin cam đoan`, `Người từ chối hưởng di sản`, `Lời chứng`.

---

## 3. Quy trình thêm loại văn bản mới

Khi cần bổ sung thêm một loại văn bản mới vào hệ thống:
1. **Cập nhật catalog**: Thêm tên loại văn bản, marker tiêu đề, nhóm HĐ, quy tắc đương sự và tài sản vào file này.
2. **Khai báo `DOC_KIND_*`**: Khai báo hằng số trong `extract_contract.py`.
3. **Cập nhật hàm nhận diện**: Thêm rule vào `_detect_document_kind_and_title()`.
4. **Cập nhật hàm trích xuất**:
   - Nếu đương sự có cấu trúc mới $\rightarrow$ Bổ sung hàm parse đương sự và cập nhật `_fmt_duong_su_by_kind()`.
   - Nếu tài sản có marker đặc thù $\rightarrow$ Bổ sung `_find_tai_san_<kind>()` và tích hợp vào `_find_tai_san_by_kind()`.
5. **Thêm Unit Test**: Bổ sung test case vào `tests/test_upload_lab_extract_contract.py`.
6. **Chạy đối chiếu mẫu thực tế**: Đặt file vào `regex_review_samples/input/` và chạy `review_regex_samples.py`.

## Future runtime LLM

Có thể nghiên cứu chế độ `regex` / `hybrid` / `llm` trả về span offsets có cấu trúc, không nhận free text. Mặc định phải tắt; khi timeout hoặc lỗi phải fallback về regex. Dữ liệu có PII nên chỉ được xử lý trong ranh giới bảo mật đã phê duyệt. Đây chỉ là ý tưởng, chưa triển khai runtime.
