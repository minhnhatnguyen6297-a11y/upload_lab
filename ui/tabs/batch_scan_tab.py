"""Batch Scan Folder tab."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QMessageBox,
)
from pathlib import Path
from ui.widgets import FolderBrowserWidget, ProgressPanelWidget


class BatchScanTab(QWidget):
    """Tab for batch scanning a folder."""
    
    run_batch_scan = pyqtSignal(dict)  # Emits config dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Group 1: Folder Selection
        group1 = QGroupBox("Thư mục quét hồ sơ")
        group1_layout = QVBoxLayout(group1)
        self.folder_browser = FolderBrowserWidget(label_text="Chọn thư mục tổng hồ sơ")
        group1_layout.addWidget(self.folder_browser)
        layout.addWidget(group1)
        
        # Group 2: Options
        group2 = QGroupBox("Tùy chọn")
        group2_layout = QVBoxLayout(group2)
        
        # Modified since date
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Modified since (YYYY-MM-DD):"))
        self.modified_since_input = QLineEdit()
        self.modified_since_input.setPlaceholderText("Để trống để bỏ qua")
        self.modified_since_input.setMaximumWidth(200)
        date_row.addWidget(self.modified_since_input)
        date_row.addStretch()
        group2_layout.addLayout(date_row)
        
        # Full rescan checkbox
        self.full_rescan_check = QCheckBox("Full rescan (bỏ qua mốc ngày)")
        group2_layout.addWidget(self.full_rescan_check)
        
        # Max depth
        depth_row = QHBoxLayout()
        depth_row.addWidget(QLabel("Độ sâu quét tối đa:"))
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setMinimum(1)
        self.max_depth_spin.setMaximum(10)
        self.max_depth_spin.setValue(3)
        self.max_depth_spin.setMaximumWidth(80)
        depth_row.addWidget(self.max_depth_spin)
        depth_row.addStretch()
        group2_layout.addLayout(depth_row)
        
        layout.addWidget(group2)
        
        # Group 3: Actions
        group3 = QGroupBox("Thao tác")
        group3_layout = QHBoxLayout(group3)
        
        self.run_btn = QPushButton("▶️ Chạy Batch Scan")
        self.run_btn.clicked.connect(self._on_run_clicked)
        group3_layout.addWidget(self.run_btn)
        
        group3_layout.addStretch()
        layout.addWidget(group3)
        
        # Group 4: Progress
        group4 = QGroupBox("Tiến độ")
        group4_layout = QVBoxLayout(group4)
        self.progress_panel = ProgressPanelWidget()
        group4_layout.addWidget(self.progress_panel)
        layout.addWidget(group4)
        
        # Group 5: Results
        group5 = QGroupBox("Kết quả")
        group5_layout = QVBoxLayout(group5)
        
        manifest_row = QHBoxLayout()
        manifest_row.addWidget(QLabel("Manifest:"))
        self.manifest_display = QLineEdit()
        self.manifest_display.setReadOnly(True)
        manifest_row.addWidget(self.manifest_display)
        group5_layout.addLayout(manifest_row)
        
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.output_display = QLineEdit()
        self.output_display.setReadOnly(True)
        output_row.addWidget(self.output_display)
        group5_layout.addLayout(output_row)
        
        stats_row = QHBoxLayout()
        stats_row.addWidget(QLabel("Summary:"))
        self.stats_display = QLineEdit()
        self.stats_display.setReadOnly(True)
        stats_row.addWidget(self.stats_display)
        group5_layout.addLayout(stats_row)
        
        layout.addWidget(group5)
        
        layout.addStretch()
    
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        folder = self.folder_browser.get_folder_path()
        if not folder:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục quét.")
            return
        
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(self, "Lỗi", "Thư mục không hợp lệ.")
            return
        
        config = {
            "folder": str(folder_path),
            "modified_since": self.modified_since_input.text().strip() or None,
            "full_rescan": self.full_rescan_check.isChecked(),
            "max_depth": self.max_depth_spin.value(),
        }
        
        self.run_btn.setEnabled(False)
        self.progress_panel.reset()
        self.run_batch_scan.emit(config)
    
    def set_progress(self, progress: int) -> None:
        """Update progress bar."""
        self.progress_panel.set_progress(progress)
    
    def set_status(self, status: str) -> None:
        """Update status text."""
        self.progress_panel.set_status(status)
    
    def set_detail(self, detail: str) -> None:
        """Update detail text."""
        self.progress_panel.set_detail(detail)
    
    def set_file(self, file_path: str) -> None:
        """Update current file being processed."""
        self.progress_panel.set_file(file_path)
    
    def set_results(self, manifest_path: str, output_folder: str, stats: str) -> None:
        """Set results after scan completes."""
        self.manifest_display.setText(manifest_path)
        self.output_display.setText(output_folder)
        self.stats_display.setText(stats)
    
    def enable_run_button(self, enabled: bool = True) -> None:
        """Enable/disable run button."""
        self.run_btn.setEnabled(enabled)
