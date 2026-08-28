# LLM Regex Lab

Lab agent-driven để rà soát kết quả `extract_contract.py`, không gọi API LLM và không cần API key. Đặt mẫu `.doc`/`.docx` trong `input/`; file tạm Word `~$*` được bỏ qua.

```powershell
.\.venv\Scripts\python.exe .\regex_lab.py ingest
.\.venv\Scripts\python.exe .\regex_lab.py review
# Agent đọc packets/<timestamp>/index.md, sau đó chỉ mở packet cần thiết.
.\.venv\Scripts\python.exe .\regex_lab.py approve --cluster <cluster-id>
# Hoặc duyệt toàn bộ sau khi con người đã kiểm tra:
.\.venv\Scripts\python.exe .\regex_lab.py approve --all
.\.venv\Scripts\python.exe .\regex_lab.py verify
```

`verify` trả mã lỗi 1 chỉ khi mẫu đã duyệt bị `CHANGED`; mẫu `NEW` không làm fail. `cache/`, `golden/` và `packets/` đều được gitignore.

Mẫu và packet có thể chứa PII (họ tên, CCCD, địa chỉ, tài sản). Không commit, không tải lên dịch vụ ngoài và chỉ chia sẻ phần bằng chứng tối thiểu cần thiết.
