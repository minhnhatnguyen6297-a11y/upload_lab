# Handoff — Đăng nhập thủ công và nhận diện Lưu hồ sơ

## Mục tiêu đã chốt

- App không lưu tên đăng nhập hoặc mật khẩu.
- Người dùng tự đăng nhập trong Chromium do app mở. App nhận ra đăng nhập khi web có `access_token` trong local storage và đã rời trang `/dang-nhap`.
- Một Chromium được dùng chung cho đăng nhập, tải Excel và chuẩn bị upload.
- Sau khi người dùng bấm **Lưu** trên một tab hồ sơ, app tự nhận biết và chuyển hồ sơ thành `uploaded_success`. Dòng đó tự biến khỏi bảng.
- Người dùng chọn số tab mở mỗi đợt ngay trên màn hình Folder Scan & Upload, từ 1 đến 30.

## Cách dùng

1. Bấm **Cấu hình**.
2. Nhập địa chỉ web nếu cần, rồi bấm **Mở trình duyệt đăng nhập**.
3. Đăng nhập trên Chromium. App tự báo đã đăng nhập; nút **Tôi đã đăng nhập** chỉ là cách kiểm tra ngay nếu cần.
4. Quét folder, chọn hồ sơ và bấm Upload.
5. Kiểm tra thông tin trong từng tab Chromium rồi tự bấm **Lưu** trên web.
6. App tự đóng tab đã Lưu và bỏ dòng hồ sơ đó khỏi bảng. Bấm **Tiếp tục N số tiếp theo** để mở đợt mới.

## Kiểm tra môi trường khi đăng nhập lần đầu

- Trước lần mở đăng nhập đầu tiên, app cần có nút **Kiểm tra môi trường và mở đăng nhập**. Bộ kiểm tra chạy nền, không được làm app tự thoát khi lỗi.
- Phải kiểm tra: quyền ghi thư mục app, dung lượng đĩa, thư viện Playwright, Chromium đi kèm, mạng/DNS, HTTPS đến trang đăng nhập và việc Chromium thật mở được URL.
- Chrome cài sẵn không phải điều kiện bắt buộc vì app dùng Chromium của Playwright. Chỉ ghi nhận phiên bản Chrome/Edge để chẩn đoán hoặc khi người dùng chủ động chọn dùng chúng.
- Windows 10 cần được ghi là **tương thích có kiểm tra**: Playwright hiện hỗ trợ chính thức Windows 11+; không tự nâng cấp Playwright/Chromium trên máy Windows 10.
- Kết quả phải chỉ rõ bước nào lỗi, có nút Thử lại/Sao chép chẩn đoán, và chỉ lưu log đã bỏ token, cookie, mật khẩu và URL có query.

Đặc tả đầy đủ, gồm mức chặn/cảnh báo và tiêu chí chấp nhận, nằm trong [Linear MIN-31](https://linear.app/minhnotary/issue/MIN-31/upload-lab-fluent-ui-redesign-specification-windows-11).

## Quy tắc kỹ thuật quan trọng

- URL mặc định là `https://congchungnamdinh.ninhbinh.gov.vn`.
- Route đăng nhập và tạo nhanh được tự suy ra từ địa chỉ web. Có thể đặt `ND_LOGIN_URL` hoặc `ND_CREATE_URL` trong `.env` nếu web đổi route.
- Token đăng nhập nằm trong local storage, không phải cookie. Playwright lưu lại storage state sau khi phát hiện đăng nhập thành công.
- App nhận biết Lưu bằng phản hồi `POST /api/hoso` thành công; đây là tín hiệu chính. Nếu web chuyển khỏi trang tạo nhanh sau khi Lưu, app cũng xem là đã Lưu.
- Mỗi tab chuẩn bị được gắn với một `record_id`. Một hồ sơ còn tab mở sẽ không bị mở trùng. Nếu tab bị đóng trước khi có tín hiệu Lưu, hồ sơ có thể chuẩn bị lại ở lần Tiếp tục.
- Log mạng chỉ ghi phương thức, URL không có query string và mã trạng thái; không ghi token, cookie hay nội dung request.

## Không làm trong phạm vi này

- Không nhúng Chrome vào giao diện app.
- Không gửi hồ sơ bằng REST API thay cho Playwright.
- Không tự bấm nút Lưu thay người dùng.
- Không tự mở ngay đợt kế tiếp sau khi phát hiện Lưu.
