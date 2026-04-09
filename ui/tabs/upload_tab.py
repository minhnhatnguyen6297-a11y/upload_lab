"""Upload Playwright tab."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QScrollArea,
)
from ui.widgets import FileBrowserWidget, RecordsTableWidget


class UploadTab(QWidget):
    """Tab for uploading records via Playwright."""
    
    refresh_queue = pyqtSignal()
    start_upload = pyqtSignal(str)  # Emits manifest path
    stop_upload = pyqtSignal()
    finalize_records = pyqtSignal(list)  # Emits list of record_ids
    download_web_export = pyqtSignal(tuple)  # Emits (from_date, to_date)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Group 1: Manifest Selection
        group1 = QGroupBox("Manifest từ Batch Scan")
        group1_layout = QVBoxLayout(group1)
        self.manifest_browser = FileBrowserWidget(label_text="Chọn file manifest (*.json)")
        group1_layout.addWidget(self.manifest_browser)
        layout.addWidget(group1)
        
        # Group 2: Web Contract Comparison
        group2 = QGroupBox("So sánh với dữ liệu trên web")
        group2_layout = QVBoxLayout(group2)
        
        # Excel file
        self.export_browser = FileBrowserWidget(label_text="Chọn file Excel export sổ công chứng")
        group2_layout.addWidget(self.export_browser)
        
        # Date range
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Từ ngày:"))
        self.from_date_input = QLineEdit()
        self.from_date_input.setMaximumWidth(120)
        self.from_date_input.setPlaceholderText("YYYY-MM-DD")
        date_row.addWidget(self.from_date_input)
        
        date_row.addWidget(QLabel("Đến ngày:"))
        self.to_date_input = QLineEdit()
        self.to_date_input.setMaximumWidth(120)
        self.to_date_input.setPlaceholderText("YYYY-MM-DD")
        date_row.addWidget(self.to_date_input)
        
        self.download_btn = QPushButton("⬇️ Tải từ web")
        self.download_btn.clicked.connect(self._on_download_clicked)
        date_row.addWidget(self.download_btn)
        
        date_row.addStretch()
        group2_layout.addLayout(date_row)
        
        layout.addWidget(group2)
        
        # Group 3: Actions
        group3 = QGroupBox("Thao tác")
        group3_layout = QHBoxLayout(group3)
        
        self.refresh_btn = QPushButton("🔄 Refresh Queue")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        group3_layout.addWidget(self.refresh_btn)
        
        self.start_btn = QPushButton("▶️ Start Dry-run")
        self.start_btn.clicked.connect(self._on_start_clicked)
        group3_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        group3_layout.addWidget(self.stop_btn)
        
        self.finalize_btn = QPushButton("✅ Finalize Selected")
        self.finalize_btn.clicked.connect(self._on_finalize_clicked)
        group3_layout.addWidget(self.finalize_btn)
        
        group3_layout.addStretch()
        layout.addWidget(group3)
        
        # Group 4: Status
        group4 = QGroupBox("Trạng thái")
        group4_layout = QVBoxLayout(group4)
        
        self.upload_status = QLineEdit()
        self.upload_status.setReadOnly(True)
        self.upload_status.setText("Chưa chọn manifest")
        group4_layout.addWidget(self.upload_status)
        
        self.capability_status = QLineEdit()
        self.capability_status.setReadOnly(True)
        group4_layout.addWidget(self.capability_status)
        
        self.compare_status = QLineEdit()
        self.compare_status.setReadOnly(True)
        group4_layout.addWidget(self.compare_status)
        
        layout.addWidget(group4)
        
        # Group 5: Queue Table
        group5 = QGroupBox("Hàng chờ đợi")
        group5_layout = QVBoxLayout(group5)
        
        self.queue_table = RecordsTableWidget()
        group5_layout.addWidget(self.queue_table)
        
        layout.addWidget(group5, 2)
        
        # Group 6: Duplicate Records
        group6 = QGroupBox("Hồ sơ đã tồn tại trên web")
        group6_layout = QVBoxLayout(group6)
        
        self.duplicate_table = RecordsTableWidget()
        group6_layout.addWidget(self.duplicate_table)
        
        layout.addWidget(group6, 1)
    
    def _on_refresh_clicked(self) -> None:
        """Handle refresh queue button click."""
        self.refresh_queue.emit()
    
    def _on_start_clicked(self) -> None:
        """Handle start upload button click."""
        manifest = self.manifest_browser.get_file_path()
        if not manifest:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn manifest.")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)
        self.start_upload.emit(manifest)
    
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_upload.emit()
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
    
    def _on_finalize_clicked(self) -> None:
        """Handle finalize selected button click."""
        record_ids = self.queue_table.get_selected_record_ids()
        if not record_ids:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất 1 record.")
            return
        
        self.finalize_records.emit(record_ids)
    
    def _on_download_clicked(self) -> None:
        """Handle download from web button click."""
        from_date = self.from_date_input.text().strip()
        to_date = self.to_date_input.text().strip()
        
        if not from_date or not to_date:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập cả hai ngày.")
            return
        
        self.download_web_export.emit((from_date, to_date))
    
    def set_upload_status(self, status: str) -> None:
        """Set upload status text."""
        self.upload_status.setText(status)
    
    def set_capability_status(self, status: str, ready: bool = True) -> None:
        """Set Playwright capability status."""
        color = "#38761d" if ready else "#a61c00"
        self.capability_status.setText(status)
        self.capability_status.setStyleSheet(f"color: {color};")
        if not ready:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def set_compare_status(self, status: str) -> None:
        """Set web comparison status."""
        self.compare_status.setText(status)
    
    def load_queue_records(self, records: list) -> None:
        """Load queue records into table."""
        self.queue_table.load_records(records)
    
    def load_duplicate_records(self, records: list) -> None:
        """Load duplicate records into table."""
        self.duplicate_table.load_records(records)
    
    def enable_upload_buttons(self, enabled: bool = True) -> None:
        """Enable/disable upload action buttons."""
        if enabled:
            self.start_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
