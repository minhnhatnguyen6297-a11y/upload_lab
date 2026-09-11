from __future__ import annotations

from pathlib import Path
from typing import Any

from ui_qt.workers import UploadWorker

from .bridge import UploadWorkerBridge
from .registry import CommandRegistry


def create_worker_backed_registry(working_dir: Path) -> tuple[CommandRegistry, UploadWorkerBridge]:
    """Wire the POC sidecar to public UploadWorker slots without the Qt UI.

    `scan_document` remains deliberately unavailable here: it needs a separately
    approved mapping to upload_lab's preparation inputs. The command reports a
    structured failed job rather than inventing that business mapping.
    """
    worker = UploadWorker(working_dir)
    holder: dict[str, UploadWorkerBridge] = {}
    registry = CommandRegistry(
        lambda command, payload, job_id: holder["bridge"].submit(command, payload, job_id)
    )

    def scan_unavailable(_payload: dict[str, Any]) -> None:
        raise RuntimeError("scan_document POC bridge is not configured")

    def update(job_id: str, status: str, result: dict[str, Any] | None, error: dict[str, str] | None) -> None:
        registry.update(job_id, status, result=result, error=error)

    holder["bridge"] = UploadWorkerBridge(worker, scan_callback=scan_unavailable, update_callback=update)
    return registry, holder["bridge"]
