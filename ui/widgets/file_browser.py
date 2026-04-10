"""File and folder browser widgets."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FileBrowserWidget(QWidget):
    """Widget for choosing a file with a read-only path display."""

    file_changed = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        *,
        label_text: str = "Tệp",
        button_text: str = "Chọn tệp",
        dialog_title: str = "Chọn tệp",
        file_filter: str = "All Files (*)",
        placeholder_text: str = "",
    ) -> None:
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._file_filter = file_filter
        self._file_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(label_text)
        layout.addWidget(self.label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        layout.addLayout(row)

        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText(placeholder_text)
        self.path_input.setMinimumWidth(320)
        row.addWidget(self.path_input, 1)

        self.browse_btn = QPushButton(button_text)
        self.browse_btn.setFixedWidth(150)
        self.browse_btn.clicked.connect(self._browse_file)
        row.addWidget(self.browse_btn)

    def _browse_file(self) -> None:
        start_dir = ""
        current_path = self.get_file_path()
        if current_path:
            current = Path(current_path)
            start_dir = str(current.parent if current.exists() else current.parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._dialog_title,
            start_dir,
            self._file_filter,
        )
        if file_path:
            self.set_file_path(file_path)

    def set_file_path(self, path: str) -> None:
        candidate = Path(path) if path else None
        resolved = str(candidate) if candidate and candidate.exists() else ""
        self._file_path = resolved
        self.path_input.setText(resolved)
        self.path_input.setCursorPosition(0)
        self.file_changed.emit(resolved)

    def get_file_path(self) -> str:
        return self._file_path

    def clear(self) -> None:
        self.set_file_path("")


class FolderBrowserWidget(QWidget):
    """Widget for choosing a folder with a read-only path display."""

    folder_changed = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        *,
        label_text: str = "Thư mục",
        button_text: str = "Chọn thư mục",
        dialog_title: str = "Chọn thư mục",
        placeholder_text: str = "",
    ) -> None:
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._folder_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(label_text)
        layout.addWidget(self.label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        layout.addLayout(row)

        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText(placeholder_text)
        self.path_input.setMinimumWidth(320)
        row.addWidget(self.path_input, 1)

        self.browse_btn = QPushButton(button_text)
        self.browse_btn.setFixedWidth(150)
        self.browse_btn.clicked.connect(self._browse_folder)
        row.addWidget(self.browse_btn)

    def _browse_folder(self) -> None:
        start_dir = self.get_folder_path()
        if start_dir and not Path(start_dir).exists():
            start_dir = ""

        folder_path = QFileDialog.getExistingDirectory(
            self,
            self._dialog_title,
            start_dir,
        )
        if folder_path:
            self.set_folder_path(folder_path)

    def set_folder_path(self, path: str) -> None:
        candidate = Path(path) if path else None
        resolved = str(candidate) if candidate and candidate.exists() else ""
        self._folder_path = resolved
        self.path_input.setText(resolved)
        self.path_input.setCursorPosition(0)
        self.folder_changed.emit(resolved)

    def get_folder_path(self) -> str:
        return self._folder_path

    def clear(self) -> None:
        self.set_folder_path("")
