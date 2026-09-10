# AGENTS.md — upload_lab

## Sources of truth
- `README.md` — pipeline 3 giai đoạn, sơ đồ codebase, lệnh chạy/test
- `docs/regex-rules.md` — quy chuẩn trích xuất theo từng loại văn bản
- `docs/spec_UI.md` — UI

## Rules
- Không tự chuyển chế độ Finalize thành mặc định. Dry-run là mặc định.
- Đổi selector web tỉnh: sửa ở `uploader_selectors.py`, không rải trong code.
- Thêm loại văn bản mới: cập nhật `docs/regex-rules.md` cùng lúc với code.
- Chạy test trước khi báo xong.

## Cross-product context (read only when needed)
`D:\systemdocs` — tài liệu cấp cha cho họ sản phẩm công chứng.
Task thường ngày **không cần** đọc. Chỉ đọc khi task chạm ranh giới sản phẩm,
khóa định danh dùng chung, hoặc tích hợp: `PROJECTS.md`,
`contracts/entities.md`, `OPEN_DECISIONS.md`. Repo này thắng về hành vi nội bộ.

**Bắt buộc đọc `TECH_STACK.md` trước khi** thêm/đổi công nghệ (thư viện đọc
file, OCR, DB, queue, framework UI) hoặc ra quyết định kiến trúc. Ba repo sẽ
gộp về một database dùng chung, chọn lệch nhau là viết lại sau.
