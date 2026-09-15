from __future__ import annotations

import hashlib
import importlib.metadata
import mimetypes
from pathlib import Path
from typing import Callable

import fitz

try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None  # type: ignore[assignment,misc]


def _route(path: Path, data: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix in {".docx", ".xlsx"} and data.startswith(b"PK\x03\x04"):
        return "local"
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        try:
            document = fitz.open(stream=data, filetype="pdf")
            try:
                return "local" if any(page.get_text("text").strip() for page in document) else "ocr_candidate"
            finally:
                document.close()
        except Exception:
            return "unsupported"
    if suffix == ".doc" and data.startswith(b"\xd0\xcf\x11\xe0"):
        return "legacy_doc_external"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "ocr_candidate"
    return "unsupported"


def _markitdown(path: Path) -> str:
    if MarkItDown is None:
        raise RuntimeError("markitdown is not installed; install requirements-poc-conversion-benchmark.txt")
    return MarkItDown(enable_plugins=False).convert(str(path)).markdown


def _pdf_page_segments(data: bytes) -> list[dict]:
    """Return page-addressable plain text without changing converter Markdown."""
    document = fitz.open(stream=data, filetype="pdf")
    try:
        return [
            {"text": page.get_text("text"), "source_ref": {"page": page_number}}
            for page_number, page in enumerate(document, start=1)
        ]
    finally:
        document.close()


def convert_path(path: Path, *, converter: Callable[[Path], str] = _markitdown) -> dict:
    """Convert only locally permitted inputs; cloud OCR is intentionally unavailable."""
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    media_type, _ = mimetypes.guess_type(str(path))
    route = _route(path, data)
    envelope = {
        "contract_version": "v0.experimental",
        "source": {"path": str(path), "sha256": digest, "mime": media_type, "size_bytes": len(data)},
        "route": route,
        "converter": {
            "name": "markitdown" if converter is _markitdown else "injected-test-converter",
            "version": _converter_version(converter),
            "config": "plugins-disabled",
        },
        "content": {"format": "markdown", "value": ""},
        "segments": [],
        "ocr_calls": [],
        "warnings": [],
        "errors": [],
    }
    if route == "local":
        try:
            text = converter(path)
        except Exception as exc:
            envelope["errors"].append({"code": "local_conversion_failed", "message": str(exc)})
            return envelope
        envelope["content"]["value"] = text
        if path.suffix.lower() == ".pdf":
            try:
                segments = _pdf_page_segments(data)
            except Exception:
                segments = []
            if segments:
                envelope["segments"].extend(segments)
                return envelope
        envelope["segments"].append({"text": text, "source_ref": None})
        envelope["warnings"].append("provenance_not_asserted_by_markitdown")
    elif route == "legacy_doc_external":
        envelope["warnings"].append("legacy_doc_requires_upload_lab_ifilter")
    elif route == "ocr_candidate":
        envelope["warnings"].append("cloud_ocr_not_authorized")
    else:
        envelope["errors"].append({"code": "unsupported_input", "message": "Input is unsupported by the local POC"})
    return envelope


def _converter_version(converter: Callable[[Path], str]) -> str:
    if converter is not _markitdown:
        return "injected-test"
    try:
        return importlib.metadata.version("markitdown")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"
