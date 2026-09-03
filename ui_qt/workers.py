from __future__ import annotations

import queue
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from playwright_uploader import NamDinhUploaderSession, load_uploader_settings
from ui.services.folder_workflow_service import run_folder_scan


class FolderScanWorker(QObject):
    finished = Signal(dict, str)
    failed = Signal(str)
    progress = Signal(dict)

    def __init__(self, folder_path: str, working_dir: Path):
        super().__init__()
        self.folder_path = str(folder_path)
        self.working_dir = Path(working_dir)

    def run(self) -> None:
        try:
            manifest, manifest_path = run_folder_scan(
                self.folder_path,
                modified_since=None,
                full_rescan=False,
                progress_callback=lambda snapshot: self.progress.emit(dict(snapshot)),
                working_dir=self.working_dir,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(manifest, str(manifest_path))


class UploadWorker(QObject):
    """Run every Playwright call on one normal Python thread.

    Playwright's synchronous API and a Qt QThread can terminate the Windows
    process on some office PCs. A standard Python thread keeps the browser
    session isolated while Qt signals safely send results back to the UI.
    """

    prepared = Signal(dict)
    optionsRefreshed = Signal(dict)
    loginStateChanged = Signal(dict)
    exportDownloaded = Signal(str)
    preparedPagesChanged = Signal(dict)
    failed = Signal(str, str)
    progress = Signal(dict)
    log = Signal(str)
    closed = Signal()

    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.stop_event: threading.Event | None = None
        self._commands: queue.Queue[tuple[str, object]] = queue.Queue()
        self._shutdown = threading.Event()
        self._browser_thread: threading.Thread | None = None
        self._session: NamDinhUploaderSession | None = None
        self._last_login_status = ""

    def request_stop(self) -> None:
        """Safe to call directly from the GUI thread."""
        if self.stop_event is not None:
            self.stop_event.set()

    def _ensure_browser_thread(self) -> None:
        if self._browser_thread is not None and self._browser_thread.is_alive():
            return
        self._shutdown.clear()
        self._browser_thread = threading.Thread(
            target=self._browser_loop,
            name="upload-lab-playwright",
            daemon=True,
        )
        self._browser_thread.start()

    def _enqueue(self, operation: str, payload: object = None) -> None:
        self._ensure_browser_thread()
        self._commands.put((operation, payload))

    def _ensure_session(self) -> NamDinhUploaderSession:
        """Called only by the dedicated Playwright thread."""
        if self._session is None:
            self._session = NamDinhUploaderSession(
                load_uploader_settings(self.working_dir),
                working_dir=self.working_dir,
                log_callback=self.log.emit,
            )
        return self._session

    def _close_session_in_browser_thread(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    def _emit_login_result(self, result: dict) -> None:
        self._last_login_status = str(result.get("status") or "")
        self.loginStateChanged.emit(result)

    def _poll_browser_in_browser_thread(self) -> None:
        session = self._session
        if session is None:
            return
        try:
            login_result = session.poll_manual_login()
            login_status = str(login_result.get("status") or "")
            if login_status not in {"", "idle", "waiting"} or login_status != self._last_login_status:
                self._emit_login_result(login_result)
                if login_status == "authenticated":
                    self.optionsRefreshed.emit(session.fetch_staff_options())

            page_result = session.poll_prepared_pages()
            if page_result["saved_record_ids"] or page_result["closed_record_ids"]:
                self.preparedPagesChanged.emit(page_result)
        except Exception as exc:
            self.log.emit(f"[UPLOAD] Khong the kiem tra trang thai Chromium: {exc}")

    def _browser_loop(self) -> None:
        try:
            while not self._shutdown.is_set():
                try:
                    operation, payload = self._commands.get(timeout=0.5)
                except queue.Empty:
                    self._poll_browser_in_browser_thread()
                    continue

                if operation == "close":
                    self._shutdown.set()
                    break

                try:
                    if operation == "prepare":
                        command = dict(payload or {})
                        self.stop_event = threading.Event()
                        summary = self._ensure_session().prepare_manifest(
                            command["manifest_path"],
                            self.stop_event,
                            selected_record_ids=set(command["selected_record_ids"]),
                            exclude_contract_nos=set(command.get("exclude_contract_nos") or set()),
                            progress_callback=lambda snapshot: self.progress.emit(dict(snapshot)),
                            cong_chung_vien=command.get("cong_chung_vien"),
                            thu_ky=command.get("thu_ky"),
                            chunk_size=command.get("chunk_size"),
                        )
                        self.prepared.emit(summary)
                    elif operation == "start_login":
                        session = self._ensure_session()
                        session.settings = load_uploader_settings(self.working_dir)
                        self._emit_login_result(session.open_manual_login())
                    elif operation == "confirm_login":
                        result = self._ensure_session().poll_manual_login(force=True)
                        self._emit_login_result(result)
                        if result.get("status") == "authenticated":
                            self.optionsRefreshed.emit(self._ensure_session().fetch_staff_options())
                    elif operation == "download":
                        command = dict(payload or {})
                        path = self._ensure_session().download_contract_book_export(
                            from_date=str(command.get("from_date") or ""),
                            to_date=str(command.get("to_date") or ""),
                        )
                        self.exportDownloaded.emit(str(path))
                    elif operation == "refresh_options":
                        self.optionsRefreshed.emit(self._ensure_session().fetch_staff_options())
                    elif operation == "reload_options":
                        self._close_session_in_browser_thread()
                        self.optionsRefreshed.emit(self._ensure_session().fetch_staff_options())
                except Exception as exc:
                    self.failed.emit(operation, str(exc))

                self._poll_browser_in_browser_thread()
        finally:
            self._close_session_in_browser_thread()
            self.closed.emit()

    @Slot(object)
    def prepare(self, command: object) -> None:
        self._enqueue("prepare", command)

    @Slot()
    def start_login(self) -> None:
        self._enqueue("start_login")

    @Slot()
    def confirm_login(self) -> None:
        self._enqueue("confirm_login")

    @Slot(object)
    def download_export(self, command: object) -> None:
        self._enqueue("download", command)

    @Slot()
    def refresh_options(self) -> None:
        self._enqueue("refresh_options")

    @Slot()
    def reload_options(self) -> None:
        self._enqueue("reload_options")

    @Slot()
    def close_session(self) -> None:
        self.request_stop()
        self._enqueue("close")
