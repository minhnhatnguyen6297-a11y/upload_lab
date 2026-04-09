"""Progress panel widget for displaying batch operation status."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QLabel,
    QFrame,
)


class ProgressPanelWidget(QWidget):
    """Widget for displaying progress during batch operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setStyleSheet("color: #0b5394; font-weight: 500;")
        layout.addWidget(self.status_label)
        
        # Detail text
        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color: #333333;")
        layout.addWidget(self.detail_label)
        
        # File text
        self.file_label = QLabel("")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(self.file_label)
    
    def set_progress(self, value: int) -> None:
        """Set progress bar value (0-100)."""
        self.progress_bar.setValue(max(0, min(100, value)))
    
    def set_status(self, status: str) -> None:
        """Set status text."""
        self.status_label.setText(status)
    
    def set_detail(self, detail: str) -> None:
        """Set detail text."""
        self.detail_label.setText(detail)
    
    def set_file(self, file_path: str) -> None:
        """Set current file being processed."""
        if file_path:
            self.file_label.setText(f"📄 {file_path}")
        else:
            self.file_label.setText("")
    
    def reset(self) -> None:
        """Reset progress panel."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Sẵn sàng")
        self.detail_label.setText("")
        self.file_label.setText("")
