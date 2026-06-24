# Ghi chú chuyển giao cuộc trao đổi của project

Ngày tạo ban đầu: 2026-06-13  
Cập nhật gần nhất: 2026-06-16

## Bối cảnh yêu cầu hiện tại

Người dùng muốn thiết kế lại UI và flow sử dụng của app. Repo hiện tại là tool desktop để tự động hóa/quét/upload hồ sơ, cần thao tác nhiều với folder local, nên hướng phù hợp vẫn là **desktop app**, không phải web UI chạy trong trình duyệt.

## Kết quả kiểm tra nhanh repo

- Code UI hiện tại là Python desktop UI trong thư mục `ui/`.
- UI đang được quan sát trong trao đổi là Tkinter/ttk:
  - `ui/app.py`
  - `ui/widgets.py`
  - `ui/tabs/web_list_tab.py`
  - `ui/tabs/folder_workflow_tab.py`
- File chạy UI chính là `ui_runner.py`.
- Logic xử lý chính nên được giữ tách khỏi UI, gồm:
  - `batch_scan.py`
  - `extract_contract.py`
  - `playwright_uploader.py`
  - các service trong `ui/services/`

## Hướng thiết kế đã trao đổi

Figma có thể dùng làm bản tham khảo thiết kế, nhưng không phù hợp để round-trip đáng tin cậy theo kiểu: code Tkinter -> Figma kéo thả -> xuất ngược thành code Tkinter dễ bảo trì.

Hướng desktop hợp lý hơn:

1. Chuyển UI layer sang PySide6/Qt.
2. Dùng Qt Designer và file `.ui` để kéo thả, chỉnh layout/khoảng cách.
3. Giữ lại business logic và service hiện có nếu có thể.
4. Nhân dịp migrate thì thiết kế lại flow sử dụng, không chỉ port cơ học từ Tkinter sang Qt.

## Sở thích/yêu cầu người dùng đã chốt

- Cần desktop app vì tool phải thao tác nhiều với folder local.
- Muốn thiết kế lại flow sử dụng, không chỉ đổi toolkit UI.
- Muốn gom các câu hỏi cốt lõi thành spec để thiết kế không bị lạc hướng.
- Đồng ý dùng visual companion/mockup khi cần so sánh layout hoặc flow bằng hình.

## Bước tiếp theo

Tiếp tục brainstorm trước khi implementation. Hỏi từng câu cốt lõi, ghi lại câu trả lời, rồi gom thành spec chính thức.

Câu hỏi đầu tiên đã hỏi:

> Một phiên làm việc chuẩn của bạn với app này bắt đầu từ đâu và kết thúc khi nào?

Các chủ đề nên tiếp tục làm rõ khi viết spec:

- Công việc chính app phải làm nhanh nhất và ít lỗi nhất là gì.
- Input: folder, file Word, file Excel/danh sách web, thông tin đăng nhập, config, danh sách số hợp đồng đã có.
- Output: hồ sơ đã upload, log, report, export, danh sách lỗi để retry.
- Hình dạng flow chính: wizard theo bước, dashboard, hay workspace có navigation bên trái.
- Điểm user cần kiểm tra trước khi upload.
- Cách phục hồi lỗi: upload lỗi, thiếu file, hết phiên login, số trùng, thành công một phần.
- Tác vụ chạy nền: tác vụ nào cần progress, cancel, retry, log.
- Thao tác folder local: browse, recent folders, drag/drop, validate, mở file xem lại.
- Settings: tài khoản uploader, trạng thái Playwright/browser, storage state, option nâng cao.
- Ràng buộc migrate: giữ logic hiện tại, tránh rewrite upload/extraction nếu không có lý do cụ thể.

## Yêu cầu flow đã thu thập ngày 2026-06-15

Flow người dùng mục tiêu:

1. Mở app.
2. Cấu hình web/upload một lần.
3. Tải/chọn file Excel chứa danh sách số công chứng/hợp đồng.
4. Parse cột A (`SỐ CÔNG CHỨNG`) và cột B (ngày hợp đồng/ngày công chứng).
5. Hiển thị số nào đã có, số nào thiếu, dòng nào bất thường.
6. Chọn một folder local.
7. Quét file Word chỉ trong folder đã chọn.
8. Upload các hợp đồng tìm thấy và hợp lệ.
9. Người dùng tự xem lại số còn thiếu và có thể chọn/quét folder khác sau.

Quy tắc parse Excel:

- Cột A có thể chứa các dạng như `01/2026`, `09/2026/CCGD`, `123`, hoặc các biến thể lỗi.
- App trích ra số thứ tự `xxx` từ các giá trị hợp lệ.
- Dải số cần kiểm tra lấy từ số nhỏ nhất parse được đến số lớn nhất parse được trong cột A.
- App không dùng nguồn khác để đoán số cuối năm.
- File Excel được giả định là đã sắp xếp tăng dần theo ngày.
- Nếu một dòng làm vỡ thứ tự ngày hoặc thứ tự số, coi đó là cảnh báo dữ liệu.
- Nếu giá trị giống `xxx.2025` nhưng cột B là ngày năm 2026, không tự sửa. Cảnh báo user vì có thể sai năm hoặc nhập nhầm ngày.
- Các trường hợp nghi ngờ nhầm định dạng `dd/mm` và `mm/dd` cần được cảnh báo nếu làm chuỗi ngày bất thường.
- App không được âm thầm suy diễn hoặc sửa dữ liệu Excel lỗi.

Quy tắc quét folder:

- Hợp đồng có thể nằm rải rác trong nhiều folder.
- Mỗi lần chạy app chỉ quét folder người dùng chọn.
- Người dùng tự quyết định sau đó cần tìm tiếp ở folder nào.
- Ưu tiên UI: số đã có, số thiếu, file tìm thấy, cảnh báo phải thật dễ nhìn.
- UI giai đoạn đầu nên đưa đầy đủ các nhóm kết quả hữu ích, chưa tối giản quá sớm. Người dùng sẽ dùng thực tế rồi tinh chỉnh sau.

Các nhóm kết quả ban đầu nên hiển thị:

- Số hợp đồng parse được từ Excel.
- Số thiếu trong chuỗi Excel.
- Dòng Excel lỗi parse.
- Dòng Excel có thứ tự ngày/số đáng nghi.
- File Word tìm thấy trong folder đã chọn.
- File Word có số hợp đồng khớp danh sách Excel.
- File Word có số hợp đồng không nằm trong danh sách Excel.
- Số trong Excel chưa tìm thấy file trong folder đã chọn.
- File Word không đọc được.
- File Word đọc được nhưng không nhận diện là hợp đồng.
- File Word nhận diện là hợp đồng nhưng thiếu field bắt buộc.
- Số hợp đồng trùng trong folder đã chọn.
- Hợp đồng bị bỏ qua vì đã có trong danh sách web/export đã nạp, nếu có danh sách đó.
- Hàng chờ upload.
- Upload thành công.
- Upload lỗi kèm thông tin retry.
- Log runtime và artifact/report sinh ra.
- Sau upload, app không move, rename, delete hoặc sửa file Word nguồn.
- Sau upload, người dùng sẽ download/check lại danh sách hợp đồng trên web bằng workflow Excel/web-list check đã có.

Quy tắc chọn file để upload:

- Sau khi quét folder, file hợp lệ xuất hiện trong bảng/hàng chờ upload.
- Mỗi dòng file có thể upload phải có checkbox.
- Có ô/nút “chọn tất cả file hợp lệ”.
- Upload chỉ chạy với các dòng đang được tick.
- Các dòng lỗi, chỉ-cảnh-báo, trùng, không đọc được, hoặc thiếu dữ liệu không được chọn bởi thao tác “chọn tất cả file hợp lệ”, trừ khi sau này UI có override rõ ràng.
- File hợp lệ được tick sẵn sau khi scan.
- Người dùng vẫn có thể bỏ tick từng dòng hoặc bỏ chọn/chọn lại toàn bộ file hợp lệ trước khi upload.

Quy tắc xem lại file:

- Flow chính không cần màn hình review toàn bộ dữ liệu trích xuất trước khi upload từng hợp đồng.
- User bình thường không cần thấy hoặc hiểu regex/code trong UI upload.
- User có thể click vào dòng file để mở trực tiếp file Word gốc khi muốn tự xem văn bản.
- Mở file Word bằng ứng dụng mặc định của Windows, giống hành vi double-click file trong File Explorer.
- UI cần hiển thị đường dẫn file nguồn đủ rõ để debug/truy vết.

## Yêu cầu về đọc Word và tài liệu regex

Người dùng đã yêu cầu ghi lại rõ để các phiên sau không phải hỏi lại:

1. Cách đọc dữ liệu:
   - Dữ liệu hợp đồng nằm trong file Word.
   - Code hiện tại đã có công nghệ đọc nội dung `.doc` và `.docx` mà không cần người dùng mở file thủ công.
   - Các code path liên quan hiện tại gồm `extract_contract.py`, `batch_scan.py`, và `review_regex_samples.py`.
   - Giữ năng lực đọc Word hiện có; không thiết kế lại từ đầu nếu chưa có lỗi cụ thể.

2. Cách nhận diện dữ liệu trong Word:
   - Nhận diện dữ liệu dựa trên regex/rule.
   - Mỗi loại văn bản khác nhau có thể cần chiến lược regex/rule khác nhau.
   - Project cần có tài liệu hệ thống mô tả từng regex/rule lấy dữ liệu thế nào.
   - Tài liệu phải dễ cập nhật khi có mẫu hợp đồng mới.

Cấu trúc tài liệu được khuyến nghị cho spec/implementation tiếp theo:

- Giữ hoặc mở rộng `RULE_TONG_KET_3_LOAI_VAN_BAN.md` làm bản tóm tắt rule dễ đọc.
- Thêm catalog rule regex có cấu trúc, ví dụ `docs/regex-rules.md`, mỗi loại văn bản một section.
- Mỗi section theo loại văn bản nên ghi:
  - tên loại văn bản và marker tiêu đề chuẩn;
  - các field cần trích xuất, ví dụ `so_cong_chung`, `ten_hop_dong`, `duong_su`, `tai_san`;
  - anchor bắt đầu;
  - anchor kết thúc;
  - anchor fallback;
  - các biến thể lỗi đã biết;
  - ví dụ phải match;
  - ví dụ không được match;
  - test hoặc case review sample liên quan.
- Tiếp tục dùng `regex_review_samples/input/` cho file mẫu thật ở máy local và `review_regex_samples.py` để sinh report.
- Không commit hợp đồng mẫu thật hoặc report runtime sinh ra.

Workflow phát triển regex:

- Kiểm tra regex là workflow riêng cho maintainer/developer, không nằm trong flow upload bình thường.
- Regex mới cần được viết và test với file Word mẫu cho đến khi hành vi trích xuất đạt yêu cầu.
- Chỉ sau khi regex đã được validate mới áp vào code extract/upload thật.
- User bình thường không cần biết regex hoạt động thế nào.
- Project cần giữ một nơi riêng cho regex experiment, review report, và regression test để xử lý mẫu văn bản mới có hệ thống.

## Chưa bắt đầu implementation

Chưa có implementation plan Qt/PySide6 nào được approve. Không bắt đầu code cho đến khi spec workflow được review và approve.
