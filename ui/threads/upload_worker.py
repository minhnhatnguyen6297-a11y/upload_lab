"""Worker thread for upload dry-run operations."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Optional, Set

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from playwright_uploader import NamDinhUploaderSession, load_uploader_settings
except ImportError:  # pragma: no cover
    from ...playwright_uploader import NamDinhUploaderSession, load_uploader_settings


class UploadWorker(QThread):
    """Run upload dry-run work off the main UI thread."""

    progress = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.manifest_path: Optional[Path] = None
        self.exclude_contract_nos: Set[str] = set()
        self.working_dir: Path = Path.cwd()
        self._stop_event = Event()
        self.session: Optional[NamDinhUploaderSession] = None

    def set_config(
        self,
        manifest_path: str,
        exclude_contract_nos: Optional[Set[str]] = None,
        working_dir: Optional[Path] = None,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.exclude_contract_nos = set(exclude_contract_nos or set())
        if working_dir is not None:
            self.working_dir = working_dir
        self._stop_event = Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            if not self.manifest_path or not self.manifest_path.exists():
                raise ValueError("Manifest không tồn tại.")

            settings = load_uploader_settings(self.working_dir)
            self.session = NamDinhUploaderSession(
                settings,
                working_dir=self.working_dir,
                log_callback=self.log.emit,
            )
            summary = self.session.prepare_manifest(
                self.manifest_path,
                self._stop_event,
                exclude_contract_nos=self.exclude_contract_nos,
                progress_callback=self.progress.emit,
            )
            self.finished.emit(summary)
        except Exception as exc:  # pragma: no cover - UI plumbing
            self.log.emit(f"[ERROR] Upload failed: {exc}")
            self.error.emit(str(exc))
        finally:
            if self.session is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
                self.session = None
