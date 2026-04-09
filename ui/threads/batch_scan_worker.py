"""Worker thread for batch scanning."""

from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from batch_scan import run_batch_scan, finalize_manifest
except ImportError:
    from ...batch_scan import run_batch_scan, finalize_manifest


class BatchScanWorker(QThread):
    """Worker thread for batch scanning folder."""
    
    progress_updated = pyqtSignal(dict)  # Emits progress snapshot
    finished = pyqtSignal(dict)  # Emits manifest dict
    error = pyqtSignal(str)  # Emits error message
    log = pyqtSignal(str)  # Emits log message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_path: Optional[Path] = None
        self.modified_since: Optional[str] = None
        self.full_rescan: bool = False
        self.max_depth: int = 3
        self.working_dir: Path = Path.cwd()
        self._stop_requested = False
    
    def set_config(
        self,
        folder: str,
        modified_since: Optional[str] = None,
        full_rescan: bool = False,
        max_depth: int = 3,
        working_dir: Optional[Path] = None,
    ) -> None:
        """Set batch scan configuration."""
        self.folder_path = Path(folder)
        self.modified_since = modified_since
        self.full_rescan = full_rescan
        self.max_depth = max_depth
        if working_dir:
            self.working_dir = working_dir
    
    def run(self) -> None:
        """Run batch scan."""
        try:
            if not self.folder_path or not self.folder_path.exists():
                raise ValueError("Folder không hợp lệ")
            
            self.log.emit(f"[BATCH] Bắt đầu quét: {self.folder_path}")
            
            # Run batch scan with progress callback
            manifest = run_batch_scan(
                self.folder_path,
                modified_since=self.modified_since,
                full_rescan=self.full_rescan,
                working_dir=self.working_dir,
                progress_callback=self._on_progress,
            )
            
            if self._stop_requested:
                self.log.emit("[BATCH] Đã hủy")
                return
            
            # Finalize manifest
            manifest_path = finalize_manifest(manifest, self.working_dir / "runs")
            manifest["manifest_path"] = str(manifest_path)
            
            self.log.emit(f"[BATCH] Hoàn tất. Manifest: {manifest_path}")
            self.finished.emit(manifest)
        
        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"[ERROR] Batch scan failed: {error_msg}")
            self.error.emit(error_msg)
    
    def _on_progress(self, snapshot: dict) -> None:
        """Handle progress update."""
        if self._stop_requested:
            return
        
        self.progress_updated.emit(snapshot)
    
    def request_stop(self) -> None:
        """Request to stop scanning."""
        self._stop_requested = True
