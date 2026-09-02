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
