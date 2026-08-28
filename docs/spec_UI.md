# Yêu Cầu Chỉnh Sửa Giao Diện (UI) & Trải Nghiệm Người Dùng

Tài liệu này ghi nhận các yêu cầu nghiệp vụ về việc cải thiện UI và logic hiển thị của ứng dụng Upload Lab, tập trung vào việc chuẩn hóa các bảng dữ liệu và nâng cao trải nghiệm sử dụng.

## 1. Đồng bộ và Tiêu chuẩn hóa Cấu trúc Bảng (Grid)
- **Tình trạng hiện tại:** 3 vùng chứa bảng dữ liệu (Danh sách Excel, Số còn thiếu, Số lỗi/trùng) có khung bảng lệch nhau, thứ tự và số lượng cột lộn xộn, gây khó chịu cho trải nghiệm người dùng.
- **Yêu cầu:** Đồng bộ hóa hoàn toàn cấu trúc của cả 3 bảng. Tất cả các bảng phải hiển thị chính xác 5 cột theo thứ tự sau:
  1. `STT` (Số thứ tự)
  2. `Số dòng`
  3. `Ngày`
  4. `Số công chứng`
  5. `Chú thích`

## 2. Tinh giản thông tin (Loại bỏ các cột dư thừa)
Dựa vào chuẩn 5 cột ở trên, các thông tin không cần thiết sau sẽ bị loại bỏ khỏi giao diện:
- **Vùng lỗi (Số lỗi, trùng):**
  - Bỏ cột "Loại lỗi". Người dùng sẽ trực tiếp đọc nguyên nhân cụ thể ở cột "Chú thích" (thay thế cho cột Lý do trước đây).
  - Bỏ cột "Số chuẩn" và "Số gốc", vì không mang lại nhiều giá trị thực tiễn trên UI.
- **Vùng số thiếu:**
  - Bỏ cột "Năm".

## 3. Cập nhật logic hiển thị vùng "Số còn thiếu"
- **Tình trạng hiện tại:** Các mô tả hiện tại như "Thiếu thật" xuất hiện quá nhiều nhưng không mang lại giá trị. Ngoài ra, có những ghi chú như "Co trong vung loi: trung_so" gây khó hiểu cho người đọc.
- **Yêu cầu xử lý:**
  - **Xóa bỏ các ghi chú vô nghĩa:** Xóa bỏ đoạn text "Thiếu thật" khỏi giao diện (để trống ở cột Chú thích).
  - **Lọc số lỗi:** Nếu một số bị thiếu là do bản thân nó đang bị lỗi/trùng và đã được bắt vào "Vùng lỗi", thì hệ thống không được hiển thị số đó ở "Vùng số thiếu" nữa. Nó chỉ nên tồn tại ở vùng lỗi.

## 4. Việt hóa Giao diện (Thêm dấu tiếng Việt)
- **Tình trạng hiện tại:** Đa số các nhãn (label), nút bấm (button), và thông báo trên UI đang sử dụng tiếng Việt không dấu.
- **Yêu cầu:** Chuyển đổi toàn bộ các text giao diện thành tiếng Việt có dấu đầy đủ và chuẩn xác.
  - *Ví dụ:*
    - `Tu ngay` -> `Từ ngày`, `Den ngay` -> `Đến ngày`
    - `Cau hinh` -> `Cấu hình`, `Tai Excel` -> `Tải Excel`
    - Các trạng thái thống kê: `hop_le` -> `hợp lệ`, `thieu` -> `thiếu`, `loi` -> `lỗi`, `trung` -> `trùng`
    - Tên các bảng: `Danh sach Excel` -> `Danh sách Excel`, `So con thieu` -> `Số còn thiếu`, `So loi, trung` -> `Số lỗi, trùng`
