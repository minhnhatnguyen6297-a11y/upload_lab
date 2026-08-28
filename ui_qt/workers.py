from __future__ import annotations

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
    prepared = Signal(dict)
    optionsRefreshed = Signal(dict)
    failed = Signal(str, str)
    progress = Signal(dict)
    log = Signal(str)
    closed = Signal()

    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.session: NamDinhUploaderSession | None = None
        self.stop_event: threading.Event | None = None

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
            )
        except Exception as exc:
            self.failed.emit("prepare", str(exc))
            return
        self.prepared.emit(summary)

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
        if self.session is not None:
            self.session.close()
            self.session = None
        self.closed.emit()
