from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal, Slot

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
        self.session: NamDinhUploaderSession | None = None
        self.stop_event: threading.Event | None = None
        self.browser_timer: QTimer | None = None
        self._last_login_status = ""

    def request_stop(self) -> None:
        """May be called from the GUI thread; threading.Event.set is thread-safe."""
        if self.stop_event is not None:
            self.stop_event.set()

    def _ensure_session(self) -> NamDinhUploaderSession:
        if self.session is None:
            self.session = NamDinhUploaderSession(
                load_uploader_settings(self.working_dir),
                working_dir=self.working_dir,
                log_callback=self.log.emit,
            )
        return self.session

    def _ensure_browser_timer(self) -> None:
        if self.browser_timer is None:
            self.browser_timer = QTimer(self)
            self.browser_timer.setInterval(500)
            self.browser_timer.timeout.connect(self.poll_browser)
        if not self.browser_timer.isActive():
            self.browser_timer.start()

    @Slot(object)
    def prepare(self, command: object) -> None:
        command = dict(command)
        self.stop_event = threading.Event()
        try:
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
        except Exception as exc:
            self.failed.emit("prepare", str(exc))
            return
        self.prepared.emit(summary)
        if summary.get("open_record_ids"):
            self._ensure_browser_timer()

    @Slot()
    def start_login(self) -> None:
        try:
            session = self._ensure_session()
            session.settings = load_uploader_settings(self.working_dir)
            result = session.open_manual_login()
        except Exception as exc:
            self.failed.emit("login", str(exc))
            return
        self._last_login_status = str(result.get("status") or "")
        self.loginStateChanged.emit(result)
        self._ensure_browser_timer()

    @Slot()
    def confirm_login(self) -> None:
        try:
            result = self._ensure_session().poll_manual_login(force=True)
        except Exception as exc:
            self.failed.emit("login", str(exc))
            return
        self._last_login_status = str(result.get("status") or "")
        self.loginStateChanged.emit(result)
        if result.get("status") == "authenticated":
            self.refresh_options()

    @Slot(object)
    def download_export(self, command: object) -> None:
        command = dict(command)
        try:
            path = self._ensure_session().download_contract_book_export(
                from_date=str(command.get("from_date") or ""),
                to_date=str(command.get("to_date") or ""),
            )
        except Exception as exc:
            self.failed.emit("download", str(exc))
            return
        self.exportDownloaded.emit(str(path))

    @Slot()
    def poll_browser(self) -> None:
        session = self.session
        if session is None:
            if self.browser_timer is not None:
                self.browser_timer.stop()
            return
        try:
            login_result = session.poll_manual_login()
            login_status = str(login_result.get("status") or "")
            if login_status not in {"", "idle", "waiting"} or login_status != self._last_login_status:
                self._last_login_status = login_status
                self.loginStateChanged.emit(login_result)
                if login_status == "authenticated":
                    self.refresh_options()

            page_result = session.poll_prepared_pages()
            if page_result["saved_record_ids"] or page_result["closed_record_ids"]:
                self.preparedPagesChanged.emit(page_result)

            has_login_wait = login_status == "waiting"
            if not has_login_wait and not page_result["open_record_ids"] and self.browser_timer is not None:
                self.browser_timer.stop()
        except Exception as exc:
            self.log.emit(f"[UPLOAD] Khong the kiem tra trang thai Chromium: {exc}")

    @Slot()
    def refresh_options(self) -> None:
        try:
            options = self._ensure_session().fetch_staff_options()
        except Exception as exc:
            self.failed.emit("refresh_options", str(exc))
            return
        self.optionsRefreshed.emit(options)

    @Slot()
    def reload_options(self) -> None:
        try:
            if self.session is not None:
                self.session.close()
                self.session = None
            options = self._ensure_session().fetch_staff_options()
        except Exception as exc:
            self.failed.emit("reload_options", str(exc))
            return
        self.optionsRefreshed.emit(options)

    @Slot()
    def close_session(self) -> None:
        self.request_stop()
        if self.browser_timer is not None:
            self.browser_timer.stop()
        if self.session is not None:
            self.session.close()
            self.session = None
        self.closed.emit()
