# Brief Giao Diện Tool Upload

## Mục tiêu

Thiết kế một giao diện điều khiển chỉ tập trung vào UI cho quy trình `Upload Playwright` dùng bởi nhân sự nội bộ để chuẩn bị và chốt các hồ sơ upload.

Phạm vi handoff này chỉ giới hạn ở giao diện của upload tool. Đây không phải là yêu cầu làm lại toàn bộ repo.

## Bối cảnh sản phẩm

- Công cụ hiện tại là một ứng dụng desktop chạy local trên Windows.
- Công cụ hiện tại có 3 tab, nhưng bản redesign này chỉ làm tab `Upload Playwright`.
- Logic backend đã có sẵn bằng Python và Playwright.
- Giao diện mới nên được hiểu là một frontend/control panel dùng dữ liệu mock.

## Tool này làm gì

1. Người vận hành chọn một file `manifest` của batch.
2. Tool đọc queue item từ registry local dựa trên `run_id`.
3. Người vận hành bấm làm mới queue.
4. Người vận hành bắt đầu dry-run.
5. Automation mở tab browser và điền form đến ngay trước nút `Lưu`.
6. Người vận hành tự rà soát các tab đã chuẩn bị.
7. Người vận hành quay lại control panel và finalize các record đã hoàn tất.

## Ràng buộc quan trọng

- Không thiết kế theo kiểu ứng dụng cho khách hàng cuối.
- Đây là màn hình vận hành cho công việc lặp lại, nhiều record, cần thao tác nhanh.
- Workflow phải rõ ràng, có tính vận hành, không mơ hồ.
- Không tự nghĩ thêm luật nghiệp vụ hoặc quy tắc pháp lý.
- Không triển khai browser automation thật.
- Không triển khai upload file thật.
- Chỉ dùng dữ liệu mock từ các file JSON được upload kèm.
- Toàn bộ copy hiển thị cho người dùng phải bằng tiếng Việt.

## Người dùng

- Nhân sự nội bộ
- Dùng chủ yếu trên desktop
- Xử lý khối lượng hồ sơ lớn
- Cần nhìn nhanh, lọc nhanh, thao tác hàng loạt rõ ràng

## Thực thể chính

### Manifest

Manifest đại diện cho một lần batch scan.

Các field chính:

- `run_id`
- `started_at`
- `finished_at`
- `folder_root`
- `modified_since`
- `full_rescan`
- `stats`

### Upload Record

Mỗi record trong upload queue cần hỗ trợ:

- `record_id`
- `contract_no`
- `status`
- `source_file`
- `missing_fields`
- `reason`
- `last_error`
- `prepared_at`
- `uploaded_success_at`
- `artifact_dir`
- `screenshot`
- `debug_json`
- `verify`
- `upload_form`

## Các trạng thái cần hỗ trợ

- `extracted`
- `upload_failed`
- `prepared_dry_run`
- `prepared_partial`
- `uploaded_success`

Ý nghĩa trạng thái:

- `extracted`: đã trích xuất xong, sẵn sàng để chuẩn bị dry-run
- `upload_failed`: dry-run trước đó lỗi, cần retry
- `prepared_dry_run`: browser tab đã được chuẩn bị, đang chờ người dùng rà soát
- `prepared_partial`: đã chuẩn bị nhưng còn thiếu field quan trọng hoặc cần kiểm tra kỹ hơn
- `uploaded_success`: người dùng đã xác nhận thành công và finalize record

## Phạm vi giao diện

Hãy thiết kế một màn hình vận hành tập trung, gồm các khu vực sau:

### 1. Tóm tắt batch

Hiển thị:

- tên manifest
- run id
- tổng số record pending
- số record vừa được chuẩn bị trong chunk gần nhất
- số record còn lại
- số lượng theo từng trạng thái
- artifact directory mới nhất

### 2. Khu chọn manifest

Bao gồm:

- input đường dẫn manifest hoặc file picker
- thẻ metadata của manifest
- hành động làm mới queue

### 3. Thanh tìm kiếm và bộ lọc

Hỗ trợ:

- tìm theo số công chứng
- lọc theo trạng thái
- chỉ hiện record partial
- chỉ hiện record đang được chọn

### 4. Bảng queue

Phải tối ưu cho việc rà nhiều record nhanh.

Cột gợi ý:

- checkbox
- record id
- số công chứng
- badge trạng thái
- nhóm badge các field còn thiếu
- file gốc
- thời điểm prepared
- lỗi gần nhất

### 5. Drawer chi tiết record

Khi click vào một row, mở panel bên hông để hiển thị:

- metadata tổng quan của record
- khu đối chiếu các field quan trọng
- preview dữ liệu `upload_form`
- cảnh báo / field còn thiếu
- link hoặc placeholder cho screenshot và debug JSON
- vùng ghi chú của người vận hành

### 6. Thanh hành động cố định

Các action:

- `Làm mới queue`
- `Bắt đầu dry-run`
- `Dừng`
- `Finalize mục đã chọn`

### 7. Panel log hoạt động

Hiển thị log theo thời gian cho các sự kiện như:

- đã load manifest
- đã làm mới queue
- bắt đầu dry-run
- record được chuẩn bị thành công
- record bị lỗi
- finalize hoàn tất

## Các trạng thái giao diện bắt buộc

- Chưa chọn manifest
- Đã chọn manifest nhưng chưa refresh queue
- Đang tải queue
- Queue rỗng
- Queue đã tải xong
- Dry-run đang chạy
- Dry-run đã dừng
- Có record partial
- Có lỗi
- Finalize thành công

## Kỳ vọng tương tác

- Click row để mở drawer chi tiết
- Double-click có thể được biểu diễn thành hành động `Mở file gốc`
- Chọn nhiều record phải rõ ràng và dễ thao tác
- Record partial phải nổi bật rõ
- Record failed phải hiện lỗi cả trong table lẫn drawer
- Nút `Finalize mục đã chọn` phải cho biết rõ sẽ finalize bao nhiêu record
- Giao diện phải giúp người vận hành phân biệt rõ record nào còn pending, record nào đã an toàn

## Định hướng thị giác

- Giao diện admin desktop, không phải landing page
- Dày thông tin nhưng sạch
- Nghiêm túc, thiên về vận hành
- Phân cấp thông tin rõ
- Màu trạng thái phải mạnh và dễ phân biệt
- Bảng phải rất dễ quét mắt
- Các nút hành động quan trọng nên luôn nhìn thấy
- Chữ phải dễ đọc, ưu tiên tốc độ xử lý hơn trang trí

Hướng layout gợi ý:

- dải tóm tắt ở trên
- khu queue chính ở trái hoặc giữa
- drawer chi tiết record ở bên phải
- panel log ở cạnh dưới hoặc bên cạnh

## Ghi chú thiết kế

- Ưu tiên độ rõ ràng hơn phần trang trí
- Tránh card quá to, khoảng trắng quá nhiều
- Không lấy mobile-first stacking làm trải nghiệm mặc định trên desktop
- Nên có cảm giác giống data grid/control console
- Record partial và failed phải cực kỳ dễ nhận ra

## Gợi ý copy tiếng Việt

- Chọn manifest
- Làm mới queue
- Bắt đầu dry-run
- Dừng
- Finalize đã chọn
- Hồ sơ chờ xử lý
- Đang chờ rà soát
- Thiếu trường quan trọng
- Lỗi dry-run
- Đã finalize

## Kết quả mong muốn

Tạo một prototype giao diện dùng dữ liệu mock từ:

- `sample_manifest.json`
- `sample_queue.json`

Không làm toàn bộ repo.
Không triển khai automation thật.
Hãy bắt đầu bằng plan, sau đó mới triển khai giao diện.
