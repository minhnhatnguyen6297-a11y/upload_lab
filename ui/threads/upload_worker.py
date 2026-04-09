"""Worker thread for upload operations."""

from pathlib import Path
from typing import Optional, Set

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from playwright_uploader import (
        NamDinhUploaderSession,
        load_uploader_settings,
        load_upload_queue,
    )
except ImportError:
    from ...playwright_uploader import (
        NamDinhUploaderSession,
        load_uploader_settings,
        load_upload_queue,
    )


class UploadWorker(QThread):
    """Worker thread for upload operations."""
    
    progress = pyqtSignal(dict)  # Emits progress info
    finished = pyqtSignal(dict)  # Emits summary
    error = pyqtSignal(str)  # Emits error message
    log = pyqtSignal(str)  # Emits log message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manifest_path: Optional[Path] = None
        self.exclude_contract_nos: Set[str] = set()
        self.working_dir: Path = Path.cwd()
        self._stop_requested = False
        self.session: Optional[NamDinhUploaderSession] = None
    
    def set_config(
        self,
        manifest_path: str,
        exclude_contract_nos: Optional[Set[str]] = None,
        working_dir: Optional[Path] = None,
    ) -> None:
        """Set upload configuration."""
        self.manifest_path = Path(manifest_path)
        self.exclude_contract_nos = exclude_contract_nos or set()
        if working_dir:
            self.working_dir = working_dir
    
    def run(self) -> None:
        """Run upload preparation."""
        try:
            if not self.manifest_path or not self.manifest_path.exists():
                raise ValueError("Manifest không tồn tại")
            
            self.log.emit(f"[UPLOAD] Bắt đầu từ manifest: {self.manifest_path}")
            
            # Load settings
            settings = load_uploader_settings(self.working_dir)
            
            # Create session
            self.session = NamDinhUploaderSession(
                settings,
                working_dir=self.working_dir,
                log_callback=lambda msg: self.log.emit(msg),
            )
            
            # Load queue
            manifest, records, total_pending = load_upload_queue(
                self.manifest_path,
                working_dir=self.working_dir,
            )
            
            self.log.emit(f"[UPLOAD] Tải queue: {len(records)} records")
            
            # Prepare manifest (dry-run)
            # Note: prepare_manifest expects a stop_event, we'll use _stop_requested instead
            from threading import Event
            stop_event = Event()

            def check_stop():
                if self._stop_requested:
                    stop_event.set()

            summary = self.session.prepare_manifest(
                self.manifest_path,
                stop_event,
                exclude_contract_nos=self.exclude_contract_nos,
            )
            
            if self._stop_requested:
                self.log.emit("[UPLOAD] Đã dừng")
                return
            
            self.log.emit("[UPLOAD] Hoàn tất chunk")
            self.finished.emit(summary)
        
        except Exception as e:
            error_msg = str(e)
            self.log.emit(f"[ERROR] Upload failed: {error_msg}")
            self.error.emit(error_msg)
        
        finally:
            if self.session:
                try:
                    self.session.close()
                except Exception:
                    pass
    
    def request_stop(self) -> None:
        """Request to stop upload."""
        self._stop_requested = True
