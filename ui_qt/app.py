from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from batch_scan import BASE_DIR

from ui_qt.main_window import UploadLabMainWindow
from ui_qt.theme import apply_theme, apply_widget_metrics


def run_qt_app(*, working_dir: Path = BASE_DIR) -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    apply_theme(app)
    window = UploadLabMainWindow(working_dir=working_dir)
    apply_widget_metrics(window)
    window.show()
    return int(app.exec())

