from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

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
