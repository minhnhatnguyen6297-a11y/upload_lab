"""File and folder browser widgets."""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QLabel,
)


class FileBrowserWidget(QWidget):
    """Widget for selecting a single file."""
    
    file_changed = pyqtSignal(str)  # Emits selected file path
    
    def __init__(self, parent=None, label_text: str = "File path"):
        super().__init__(parent)
        self.file_path = ""
        self._init_ui(label_text)
    
    def _init_ui(self, label_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(label_text)
        layout.addWidget(self.label)
        
        # Input row
        input_row = QHBoxLayout()
        
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        input_row.addWidget(self.path_input)
        
        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.clicked.connect(self._browse_file)
        input_row.addWidget(self.browse_btn)
        
        layout.addLayout(input_row)
    
    def _browse_file(self) -> None:
        """Open file dialog and update path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Files (*);;Doc Files (*.doc);;Docx Files (*.docx)"
        )
        if file_path:
            self.set_file_path(file_path)
    
    def set_file_path(self, path: str) -> None:
        """Set the file path."""
        self.file_path = path
        self.path_input.setText(path)
        self.file_changed.emit(path)
    
    def get_file_path(self) -> str:
        """Get the selected file path."""
        return self.file_path
    
    def clear(self) -> None:
        """Clear the selected file."""
        self.set_file_path("")


class FolderBrowserWidget(QWidget):
    """Widget for selecting a folder."""
    
    folder_changed = pyqtSignal(str)  # Emits selected folder path
    
    def __init__(self, parent=None, label_text: str = "Folder path"):
        super().__init__(parent)
        self.folder_path = ""
        self._init_ui(label_text)
    
    def _init_ui(self, label_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(label_text)
        layout.addWidget(self.label)
        
        # Input row
        input_row = QHBoxLayout()
        
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        input_row.addWidget(self.path_input)
        
        self.browse_btn = QPushButton("Browse Folder")
        self.browse_btn.clicked.connect(self._browse_folder)
        input_row.addWidget(self.browse_btn)
        
        layout.addLayout(input_row)
    
    def _browse_folder(self) -> None:
        """Open folder dialog and update path."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            ""
        )
        if folder_path:
            self.set_folder_path(folder_path)
    
    def set_folder_path(self, path: str) -> None:
        """Set the folder path."""
        self.folder_path = path
        self.path_input.setText(path)
        self.folder_changed.emit(path)
    
    def get_folder_path(self) -> str:
        """Get the selected folder path."""
        return self.folder_path
    
    def clear(self) -> None:
        """Clear the selected folder."""
        self.set_folder_path("")
