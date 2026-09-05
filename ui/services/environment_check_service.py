"""Pre-login environment diagnostics for the desktop uploader.

The service deliberately keeps browser probing out of this module.  The
Playwright probe must run on the uploader's existing browser thread so a
successful check can reuse the same Chromium session for manual login.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import tempfile
import urllib.parse
import urllib.request
from typing import Any, Callable


PASSED = "passed"
WARNING = "warning"
BLOCKED = "blocked"
NETWORK_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class EnvironmentCheckStep:
    key: str
    label: str
    status: str
    message: str
    guidance: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "message": self.message,
            "guidance": self.guidance,
            "details": dict(self.details),
        }


def safe_url(value: str) -> str:
    """Return an URL suitable for diagnostics, without query or fragment."""

    parsed = urllib.parse.urlsplit(str(value or "").strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return ""
    if not hostname:
        return ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), netloc, parsed.path or "/", "", "")
    )


def redact_text(value: object) -> str:
    """Remove URL query/fragment and common secret-shaped values from text."""

    text = str(value or "")
    text = re.sub(
        r"https?://[^\s)]+",
        lambda match: safe_url(match.group(0).rstrip(".,;")) or "<invalid-url>",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?i)(password|passwd|token|access_token|cookie|authorization)\s*[:=]\s*[^\s,;]+",
        r"\1=<redacted>",
        text,
    )
    return text[:500]


def _overall_status(steps: list[EnvironmentCheckStep]) -> str:
    if any(step.status == BLOCKED for step in steps):
        return BLOCKED
    if any(step.status == WARNING for step in steps):
        return WARNING
    return PASSED


def _step(
    key: str,
    label: str,
    status: str,
    message: str,
    guidance: str = "",
    **details: Any,
) -> EnvironmentCheckStep:
    return EnvironmentCheckStep(
        key=key,
        label=label,
        status=status,
        message=redact_text(message),
        guidance=redact_text(guidance),
        details=details,
    )


def _memory_gib() -> float | None:
    """Read total RAM without adding psutil as a runtime dependency."""

    try:
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        kernel32 = getattr(ctypes, "windll", None)
        if kernel32 is None or not kernel32.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return float(status.ullTotalPhys) / (1024**3)
    except Exception:
        return None


def _check_operating_system() -> EnvironmentCheckStep:
    system = platform.system()
    machine = platform.machine().lower()
    if system != "Windows":
        return _step(
            "operating_system",
            "Hệ điều hành",
            BLOCKED,
            f"Upload Lab cần Windows; hệ thống hiện tại là {system or 'không xác định'}.",
            "Chạy ứng dụng trên máy Windows được hỗ trợ.",
            system=system,
            machine=machine,
        )
    if machine not in {"amd64", "x86_64", "arm64", "aarch64"}:
        return _step(
            "operating_system",
            "Hệ điều hành",
            BLOCKED,
            f"Windows không chạy ở kiến trúc 64-bit được hỗ trợ: {machine or 'không xác định'}.",
            "Dùng bản Windows 64-bit.",
            system=system,
            machine=machine,
        )

    release = str(platform.release() or "")
    memory = _memory_gib()
    warnings: list[str] = []
    if release == "10":
        warnings.append("Windows 10 là chế độ tương thích có kiểm tra.")
    if memory is not None and memory < 4:
        warnings.append("RAM dưới 4 GB có thể làm upload chậm.")
    if warnings:
        return _step(
            "operating_system",
            "Hệ điều hành",
            WARNING,
            " ".join(warnings),
            "Đóng bớt ứng dụng trước khi upload.",
            system=system,
            release=release,
            machine=machine,
            memory_gib=round(memory, 2) if memory is not None else None,
        )
    return _step(
        "operating_system",
        "Hệ điều hành",
        PASSED,
        f"Windows {release or 'không xác định'} 64-bit sẵn sàng.",
        system=system,
        release=release,
        machine=machine,
        memory_gib=round(memory, 2) if memory is not None else None,
    )


def _check_workspace(working_dir: Path) -> EnvironmentCheckStep:
    try:
        working_dir.mkdir(parents=True, exist_ok=True)
        (working_dir / "logs").mkdir(parents=True, exist_ok=True)
        (working_dir / "downloads").mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".environment-check-",
            dir=working_dir,
            delete=False,
        ) as handle:
            probe_path = Path(handle.name)
            handle.write(b"upload-lab-environment-check")
        probe_path.unlink(missing_ok=True)
        return _step(
            "workspace",
            "Thư mục làm việc",
            PASSED,
            "Có thể tạo và xóa dữ liệu kiểm tra trong thư mục ứng dụng.",
            logs_dir="logs",
            downloads_dir="downloads",
        )
    except Exception as exc:
        try:
            if "probe_path" in locals():
                probe_path.unlink(missing_ok=True)
        except Exception:
            pass
        return _step(
            "workspace",
            "Thư mục làm việc",
            BLOCKED,
            f"Không thể ghi thư mục ứng dụng: {redact_text(exc)}",
            "Chuyển app sang thư mục có quyền ghi, ví dụ Documents.",
        )


def _check_disk_space(working_dir: Path) -> EnvironmentCheckStep:
    try:
        free_bytes = int(shutil.disk_usage(working_dir).free)
    except Exception as exc:
        return _step(
            "disk_space",
            "Dung lượng đĩa",
            WARNING,
            f"Không đọc được dung lượng đĩa: {redact_text(exc)}",
            "Kiểm tra thủ công dung lượng ổ đĩa trước khi upload.",
        )
    free_gib = free_bytes / (1024**3)
    if free_bytes < 500 * 1024**2:
        status = BLOCKED
        message = f"Ổ đĩa chỉ còn {free_gib:.2f} GB, dưới mức tối thiểu 500 MB."
        guidance = "Dọn thêm dung lượng trước khi tải Excel hoặc mở browser."
    elif free_bytes < 1024**3:
        status = WARNING
        message = f"Ổ đĩa còn {free_gib:.2f} GB, dưới mức khuyến nghị 1 GB."
        guidance = "Nên dọn thêm dung lượng trước khi chạy batch lớn."
    else:
        status = PASSED
        message = f"Ổ đĩa còn {free_gib:.2f} GB."
        guidance = ""
    return _step("disk_space", "Dung lượng đĩa", status, message, guidance, free_gib=round(free_gib, 2))


def _check_dependencies(
    finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> EnvironmentCheckStep:
    required = {
        "PySide6": "PySide6",
        "playwright": "Playwright",
        "openpyxl": "openpyxl",
        "docx": "python-docx",
        "qfluentwidgets": "PySide6-Fluent-Widgets",
    }
    missing: list[str] = []
    for module, label in required.items():
        try:
            if finder(module) is None:
                missing.append(label)
        except Exception:
            missing.append(label)
    if missing:
        return _step(
            "python_dependencies",
            "Python và thư viện",
            BLOCKED,
            f"Thiếu thư viện: {', '.join(missing)}.",
            "Chạy công cụ sửa cài đặt hoặc pip install -r requirements.txt.",
            missing=missing,
        )
    return _step(
        "python_dependencies",
        "Python và thư viện",
        PASSED,
        "Các thư viện bắt buộc đã có thể được tìm thấy.",
        modules=sorted(required),
    )


def _check_network(
    base_url: str,
    *,
    resolver: Callable[..., object] = socket.getaddrinfo,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> EnvironmentCheckStep:
    clean_url = safe_url(base_url)
    if not clean_url:
        return _step(
            "network",
            "Mạng và DNS",
            BLOCKED,
            "Địa chỉ web chưa hợp lệ hoặc thiếu scheme HTTP/HTTPS.",
            "Nhập địa chỉ web hợp lệ trong Cấu hình.",
        )
    parsed = urllib.parse.urlsplit(clean_url)
    host = parsed.hostname or ""
    try:
        resolver(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except Exception as exc:
        return _step(
            "network",
            "Mạng và DNS",
            BLOCKED,
            f"Không phân giải được tên miền: {redact_text(exc)}",
            "Kiểm tra mạng, VPN hoặc firewall/proxy của công ty.",
            host=host,
        )
    response = None
    try:
        response = opener(clean_url, timeout=NETWORK_TIMEOUT_SECONDS)
        status = int(getattr(response, "status", 200) or 200)
        if status >= 500:
            return _step(
                "network",
                "Mạng và DNS",
                WARNING,
                f"Website phản hồi HTTP {status}.",
                "Thử lại sau hoặc kiểm tra trạng thái website.",
                host=host,
                http_status=status,
            )
        return _step(
            "network",
            "Mạng và DNS",
            PASSED,
            f"Kết nối HTTPS tới {host} thành công.",
            host=host,
            http_status=status,
        )
    except Exception as exc:
        return _step(
            "network",
            "Mạng và DNS",
            BLOCKED,
            f"Không kết nối được website: {redact_text(exc)}",
            "Kiểm tra mạng, VPN hoặc firewall/proxy của công ty.",
            host=host,
        )
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def _check_proxy() -> EnvironmentCheckStep:
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    configured = sorted({key.upper() for key in keys if os.environ.get(key)})
    if configured:
        return _step(
            "proxy_policy",
            "Proxy và chính sách công ty",
            WARNING,
            "Phát hiện proxy từ môi trường; kết quả browser là quyết định cuối cùng.",
            "Nếu website bị chặn, gửi báo cáo chẩn đoán cho IT.",
            configured=configured,
        )
    return _step(
        "proxy_policy",
        "Proxy và chính sách công ty",
        PASSED,
        "Không phát hiện proxy môi trường.",
        configured=[],
    )


def run_environment_checks(
    working_dir: Path,
    base_url: str,
    *,
    resolver: Callable[..., object] = socket.getaddrinfo,
    opener: Callable[..., object] = urllib.request.urlopen,
    finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> dict[str, Any]:
    """Run all non-browser checks and return a JSON-safe report."""

    steps = [
        _check_operating_system(),
        _check_workspace(Path(working_dir)),
        _check_disk_space(Path(working_dir)),
        _check_dependencies(finder),
        _check_network(base_url, resolver=resolver, opener=opener),
        _check_proxy(),
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": safe_url(base_url),
        "overall": _overall_status(steps),
        "steps": [step.to_dict() for step in steps],
        "diagnostics_path": "",
    }


def finalize_report(
    report: dict[str, Any],
    browser_result: dict[str, Any],
    working_dir: Path,
) -> dict[str, Any]:
    """Merge the same-session browser probe and persist redacted diagnostics."""

    result_status = str(browser_result.get("status") or BLOCKED)
    if result_status not in {PASSED, WARNING, BLOCKED}:
        result_status = BLOCKED
    browser_step = _step(
        "playwright_browser",
        "Website bằng đúng browser",
        result_status,
        str(browser_result.get("message") or "Không kiểm tra được Chromium."),
        str(browser_result.get("guidance") or ""),
        browser_channel=str(browser_result.get("browser_channel") or ""),
        reused_browser=bool(browser_result.get("reused_browser")),
        url=safe_url(str(browser_result.get("url") or "")),
        error_code=str(browser_result.get("error_code") or ""),
    )
    steps = [
        EnvironmentCheckStep(
            key=str(item.get("key") or "unknown"),
            label=str(item.get("label") or item.get("key") or "Kiểm tra"),
            status=str(item.get("status") or BLOCKED),
            message=redact_text(item.get("message")),
            guidance=redact_text(item.get("guidance")),
            details=dict(item.get("details") or {}),
        )
        for item in report.get("steps") or []
    ]
    steps.append(browser_step)
    final = dict(report)
    final["overall"] = _overall_status(steps)
    final["steps"] = [step.to_dict() for step in steps]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = Path(working_dir) / "logs" / f"environment-check-{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    final["diagnostics_path"] = str(path)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(json.dumps(final, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return final


def format_report(report: dict[str, Any]) -> str:
    """Create compact UI text without exposing diagnostic internals."""

    lines = [f"Tổng trạng thái: {str(report.get('overall') or BLOCKED).upper()}"]
    for item in report.get("steps") or []:
        status = str(item.get("status") or BLOCKED).upper()
        label = str(item.get("label") or item.get("key") or "Kiểm tra")
        message = redact_text(item.get("message"))
        lines.append(f"[{status}] {label}: {message}")
        guidance = redact_text(item.get("guidance"))
        if guidance:
            lines.append(f"  Hướng dẫn: {guidance}")
    path = str(report.get("diagnostics_path") or "").strip()
    if path:
        lines.append(f"Báo cáo: {Path(path).name}")
    return "\n".join(lines)
