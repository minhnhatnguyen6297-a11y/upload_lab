"""Main application window."""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtGui import QIcon

from ui.styles.stylesheets import MAIN_STYLESHEET
from ui.tabs import BatchScanTab, UploadTab
from ui.widgets import LogViewerWidget
from ui.threads import BatchScanWorker, UploadWorker


class MainWindow(QMainWindow):
    """Main application window with 2 tabs."""
    
    def __init__(self, parent=None, working_dir: Path = None):
        super().__init__(parent)
        self.working_dir = working_dir or Path.cwd()
        self.setWindowTitle("Batch Scan & Upload Tool - Nam Định")
        self.setGeometry(100, 100, 1280, 900)
        self.setMinimumSize(1024, 700)
        
        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Create central widget
        self._create_ui()
        
        # Create workers
        self.batch_worker = BatchScanWorker(self)
        self.upload_worker = UploadWorker(self)
        self._connect_workers()
    
    def _create_ui(self) -> None:
        """Create UI elements."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Batch Scan
        self.batch_tab = BatchScanTab()
        self.tabs.addTab(self.batch_tab, "📋 Quét hồ sơ")
        
        # Tab 2: Upload
        self.upload_tab = UploadTab()
        self.tabs.addTab(self.upload_tab, "⬆️ Upload hồ sơ")
        
        layout.addWidget(self.tabs)
        
        # Log viewer
        self.log_viewer = LogViewerWidget()
        self.log_viewer.setMaximumHeight(150)
        layout.addWidget(self.log_viewer)
        
        # Status bar
        self.statusBar().showMessage("Sẵn sàng")
    
    def _connect_workers(self) -> None:
        """Connect worker signals to UI slots."""
        # Batch scan worker
        self.batch_tab.run_batch_scan.connect(self._on_batch_run_clicked)
        self.batch_worker.progress_updated.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_finished)
        self.batch_worker.error.connect(self._on_batch_error)
        self.batch_worker.log.connect(self.log_viewer.append_log)
        
        # Upload worker
        self.upload_tab.refresh_queue.connect(self._on_upload_refresh_queue)
        self.upload_tab.start_upload.connect(self._on_upload_start)
        self.upload_tab.stop_upload.connect(self._on_upload_stop)
        self.upload_tab.finalize_records.connect(self._on_upload_finalize)
        self.upload_tab.download_web_export.connect(self._on_download_web_export)
        
        self.upload_worker.progress.connect(self._on_upload_progress)
        self.upload_worker.finished.connect(self._on_upload_finished)
        self.upload_worker.error.connect(self._on_upload_error)
        self.upload_worker.log.connect(self.log_viewer.append_log)
    
    # ==================== Batch Scan Slots ====================
    
    @pyqtSlot(dict)
    def _on_batch_run_clicked(self, config: dict) -> None:
        """Handle batch scan run."""
        self.batch_worker.set_config(
            folder=config["folder"],
            modified_since=config.get("modified_since"),
            full_rescan=config.get("full_rescan", False),
            max_depth=config.get("max_depth", 3),
            working_dir=self.working_dir,
        )
        self.batch_worker.start()
        self.statusBar().showMessage("Đang quét hồ sơ...")
        self.log_viewer.append_log(f"[BATCH] Bắt đầu quét folder: {config['folder']}")
    
    @pyqtSlot(dict)
    def _on_batch_progress(self, snapshot: dict) -> None:
        """Handle batch scan progress update."""
        stage = snapshot.get("stage", "")
        step = snapshot.get("step", "")
        processed = int(snapshot.get("processed_files", 0))
        total = int(snapshot.get("total_files", 0))
        stats = dict(snapshot.get("stats", {}))
        current_file = str(snapshot.get("current_file", ""))
        last_outcome = str(snapshot.get("last_outcome", ""))
        last_contract_no = str(snapshot.get("last_contract_no", ""))
        rate = float(snapshot.get("files_per_second", 0.0))
        eta_seconds = snapshot.get("eta_seconds")
        elapsed_seconds = float(snapshot.get("elapsed_seconds", 0.0))
        
        # Calculate progress
        progress_value = (processed / total * 100.0) if total else 0.0
        if stage == "done" and total:
            progress_value = 100.0
        
        self.batch_tab.set_progress(int(progress_value))
        
        # Build status text
        if stage == "indexing":
            status = "📊 Đang đếm file và khởi tạo tiến độ..."
            detail = f"word_files={stats.get('total_docx_files', 0)} | supported={stats.get('total_supported_files', 0)}"
        else:
            status_parts = [
                f"processed={processed}/{total or 0}",
                f"candidates={stats.get('candidates_found', 0)}",
                f"success={stats.get('extract_success', 0)}",
                f"partial={stats.get('extract_partial', 0)}",
                f"failed={stats.get('extract_failed', 0)}",
                f"speed={rate:.2f} file/s" if rate > 0 else "speed=--",
            ]
            
            if stage == "done":
                status = "✅ Hoàn tất | " + " | ".join(status_parts)
            elif step == "extract":
                status = "🔄 Đang trích xuất | " + " | ".join(status_parts)
            else:
                status = "🔍 Đang quét | " + " | ".join(status_parts)
            
            # Build detail
            outcome_text = ""
            if last_outcome:
                outcome_text = last_outcome.replace("_", " ")
                if last_contract_no:
                    outcome_text += f" | số={last_contract_no}"
            detail = outcome_text or "Đang xử lý..."
        
        self.batch_tab.set_status(status)
        self.batch_tab.set_detail(detail)
        self.batch_tab.set_file(current_file)
    
    @pyqtSlot(dict)
    def _on_batch_finished(self, manifest: dict) -> None:
        """Handle batch scan finished."""
        manifest_path = manifest.get("manifest_path", "")
        output_folder = str(self.working_dir / "output")
        
        stats = manifest.get("stats", {})
        summary = (
            f"processed={stats.get('processed_files', 0)}/{stats.get('total_supported_files', 0)} | "
            f"candidates={stats.get('candidates_found', 0)} | "
            f"success={stats.get('extract_success', 0)} | "
            f"partial={stats.get('extract_partial', 0)} | "
            f"failed={stats.get('extract_failed', 0)}"
        )
        
        self.batch_tab.set_results(manifest_path, output_folder, summary)
        self.batch_tab.enable_run_button(True)
        self.statusBar().showMessage("Quét hồ sơ hoàn tất")
        
        QMessageBox.information(
            self,
            "Hoàn tát",
            f"Quét hồ sơ hoàn tất.\n\nManifest: {manifest_path}\n\nOutput: {output_folder}",
        )
    
    @pyqtSlot(str)
    def _on_batch_error(self, error_msg: str) -> None:
        """Handle batch scan error."""
        self.batch_tab.enable_run_button(True)
        self.statusBar().showMessage("Lỗi quét hồ sơ")
        QMessageBox.critical(self, "Lỗi", f"Quét hồ sơ thất bại:\n\n{error_msg}")
    
    # ==================== Upload Slots ====================
    
    @pyqtSlot()
    def _on_upload_refresh_queue(self) -> None:
        """Handle refresh queue."""
        # TODO: Implement queue loading
        pass
    
    @pyqtSlot(str)
    def _on_upload_start(self, manifest_path: str) -> None:
        """Handle upload start."""
        self.upload_worker.set_config(
            manifest_path=manifest_path,
            working_dir=self.working_dir,
        )
        self.upload_worker.start()
        self.statusBar().showMessage("Đang upload hồ sơ...")
    
    @pyqtSlot()
    def _on_upload_stop(self) -> None:
        """Handle upload stop."""
        self.upload_worker.request_stop()
        self.statusBar().showMessage("Đã dừng upload")
    
    @pyqtSlot(list)
    def _on_upload_finalize(self, record_ids: list) -> None:
        """Handle finalize records."""
        # TODO: Implement finalize
        QMessageBox.information(self, "Thông tin", f"Finalize {len(record_ids)} records")
    
    @pyqtSlot(tuple)
    def _on_download_web_export(self, dates: tuple) -> None:
        """Handle download web export."""
        from_date, to_date = dates
        self.log_viewer.append_log(f"[UPLOAD] Tải export từ web: {from_date} -> {to_date}")
        # TODO: Implement download
    
    @pyqtSlot(dict)
    def _on_upload_progress(self, info: dict) -> None:
        """Handle upload progress."""
        # TODO: Implement progress display
        pass
    
    @pyqtSlot(dict)
    def _on_upload_finished(self, summary: dict) -> None:
        """Handle upload finished."""
        self.statusBar().showMessage("Upload hoàn tất")
        QMessageBox.information(self, "Hoàn tất", "Upload hoàn tát")
    
    @pyqtSlot(str)
    def _on_upload_error(self, error_msg: str) -> None:
        """Handle upload error."""
        self.statusBar().showMessage("Lỗi upload")
        QMessageBox.critical(self, "Lỗi", f"Upload thất bại:\n\n{error_msg}")
