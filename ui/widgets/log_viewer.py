"""Log viewer widget with color-coded messages and collapsible content."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.styles.stylesheets import get_log_color


class LogViewerWidget(QWidget):
    """Read-only log viewer shared by the whole application."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._collapsed = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        self.title_label = QLabel("Nhật ký hoạt động")
        self.title_label.setStyleSheet("font-weight: 700;")
        header_row.addWidget(self.title_label)
        header_row.addStretch(1)
        self.toggle_btn = QPushButton("Hiện log")
        self.toggle_btn.clicked.connect(self.toggle_collapsed)
        header_row.addWidget(self.toggle_btn)
        layout.addLayout(header_row)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        content_layout.addWidget(self.log_text)

        button_row = QHBoxLayout()
        self.clear_btn = QPushButton("Xóa log")
        self.clear_btn.clicked.connect(self.clear)
        button_row.addWidget(self.clear_btn)

        self.copy_btn = QPushButton("Sao chép log")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        button_row.addWidget(self.copy_btn)

        self.save_btn = QPushButton("Lưu log ra tệp")
        self.save_btn.clicked.connect(self.save_to_file)
        button_row.addWidget(self.save_btn)
        button_row.addStretch(1)
        content_layout.addLayout(button_row)
        layout.addWidget(self.content_widget)
        self.set_collapsed(True)

    def append_log(self, message: str) -> None:
        tag = ""
        if message.startswith("[") and "]" in message:
            tag = message[: message.index("]") + 1]
        color = QColor(get_log_color(tag))
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        fmt = cursor.charFormat()
        fmt.setForeground(color)
        cursor.insertText(message.rstrip() + "\n", fmt)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def clear(self) -> None:
        self.log_text.clear()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = bool(collapsed)
        self.content_widget.setVisible(not self._collapsed)
        self.toggle_btn.setText("Hiện log" if self._collapsed else "Ẩn log")

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.log_text.toPlainText())

    def save_to_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu log",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(self.log_text.toPlainText(), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - UI feedback
            self.append_log(f"[ERROR] Không lưu được log: {exc}")
