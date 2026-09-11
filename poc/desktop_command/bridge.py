from __future__ import annotations

from collections.abc import Callable
from typing import Any


class UploadWorkerBridge:
    """Queue-only adapter around UploadWorker's public slots and Qt signals.

    This class deliberately has no Playwright/session reference. It is only a
    POC boundary; the existing PySide6 application does not instantiate it.
    """

    def __init__(
        self,
        worker: Any,
        *,
        scan_callback: Callable[[dict[str, Any]], None],
        update_callback: Callable[[str, str, dict[str, Any] | None, dict[str, str] | None], None] | None = None,
    ) -> None:
        self._worker = worker
        self._scan_callback = scan_callback
        self._update_callback = update_callback
        self._active_upload_job_id: str | None = None
        self._subscribe_public_signals()

    def _subscribe_public_signals(self) -> None:
        for name, handler in (
            ("loginStateChanged", self._on_login_state),
            ("failed", self._on_failed),
        ):
            signal = getattr(self._worker, name, None)
            if signal is not None and hasattr(signal, "connect"):
                signal.connect(handler)

    def _update(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: dict[str, str] | None = None,
    ) -> None:
        if self._update_callback is None:
            return
        self._update_callback(job_id, status, result, error)

    def submit(self, command: str, payload: dict[str, Any], job_id: str) -> None:
        if command == "start_upload":
            if self._active_upload_job_id is not None:
                self._update(job_id, "failed", error={"code": "upload_already_active", "message": "An upload login is already active"})
                return
            self._active_upload_job_id = job_id
            self._worker.start_login()
            self._update(job_id, "waiting_user")
        elif command == "cancel_upload":
            # Public slot: queues a close on the browser thread, unlike
            # request_stop() alone which has no stop_event during manual login.
            self._worker.close_session()
            if self._active_upload_job_id is not None:
                self._update(self._active_upload_job_id, "canceled")
                self._active_upload_job_id = None
            self._update(job_id, "completed", result={"canceled": True})
        elif command == "scan_document":
            try:
                self._scan_callback(dict(payload))
            except Exception as exc:
                self._update(job_id, "failed", error={"code": "scan_unavailable", "message": str(exc)})
            else:
                self._update(job_id, "completed")

    def _on_login_state(self, result: dict[str, Any]) -> None:
        state = str(result.get("status") or "")
        if state == "authenticated":
            if self._active_upload_job_id is not None:
                self._update(self._active_upload_job_id, "running", result)
        elif state in {"waiting", "idle", ""}:
            if self._active_upload_job_id is not None:
                self._update(self._active_upload_job_id, "waiting_user", result)
        else:
            if self._active_upload_job_id is not None:
                self._update(self._active_upload_job_id, "failed", result, {"code": "login_failed", "message": state})
                self._active_upload_job_id = None

    def _on_failed(self, operation: str, message: str) -> None:
        if operation in {"start_login", "preflight"} and self._active_upload_job_id is not None:
            self._update(self._active_upload_job_id, "failed", error={"code": "browser_error", "message": message})
            self._active_upload_job_id = None
