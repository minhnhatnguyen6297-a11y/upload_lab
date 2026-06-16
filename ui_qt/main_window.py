from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QWidget

from batch_scan import BASE_DIR


class UploadLabMainWindow(QMainWindow):
    def __init__(self, *, working_dir: Path = BASE_DIR):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.ui: QWidget | None = None
        self.setWindowTitle("Upload Lab")
        self.resize(1280, 860)
        self._load_ui()

    def _load_ui(self) -> None:
        ui_path = Path(__file__).resolve().parent / "forms" / "main_window.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Unable to open Qt UI file: {ui_path}")

        try:
            widget = QUiLoader().load(ui_file, self)
        finally:
            ui_file.close()

        if widget is None:
            raise RuntimeError(f"Qt UI file did not load: {ui_path}")
        if not isinstance(widget, QWidget):
            raise RuntimeError(f"Qt UI file did not produce a QWidget: {ui_path}")

        self.ui = widget
        self.setCentralWidget(widget)

