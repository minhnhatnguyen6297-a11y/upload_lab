"""Log viewer widget with color-coded messages."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCursor, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
)
from ui.styles.stylesheets import get_log_color


class LogViewerWidget(QWidget):
    """Read-only log viewer with color-coded messages."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_text = None
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Log")
        title.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(title)
        
        # Text editor
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_text)
        
        # Button row
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear)
        btn_layout.addWidget(clear_btn)
        
        copy_btn = QPushButton("Copy Log")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        save_btn = QPushButton("Save Log to File")
        save_btn.clicked.connect(self.save_to_file)
        btn_layout.addWidget(save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def append_log(self, message: str) -> None:
        """Append a log message with color-coding."""
        # Extract tag from message (e.g., "[BATCH]" from "[BATCH] Some message")
        tag = ""
        if message.startswith("[") and "]" in message:
            tag = message[:message.index("]")+1]
        
        # Get color for tag
        color = get_log_color(tag)
        
        # Append to text
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
        # Format
        format_obj = cursor.charFormat()
        format_obj.setForeground(QColor(color))
        
        cursor.insertText(message.rstrip() + "\n", format_obj)
        
        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def clear(self) -> None:
        """Clear all log messages."""
        self.log_text.clear()
    
    def copy_to_clipboard(self) -> None:
        """Copy all log text to clipboard."""
        import subprocess
        text = self.log_text.toPlainText()
        try:
            # Use Windows clipboard
            process = subprocess.Popen(
                ["clip"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(text)
        except Exception:
            pass
    
    def save_to_file(self) -> None:
        """Save log to file."""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Log File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                Path(file_path).write_text(
                    self.log_text.toPlainText(),
                    encoding="utf-8"
                )
            except Exception as e:
                self.append_log(f"[ERROR] Failed to save log: {e}")
