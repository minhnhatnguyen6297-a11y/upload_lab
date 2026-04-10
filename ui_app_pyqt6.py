"""Main PyQt6 application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow


def main() -> int:
    working_dir = Path(__file__).parent
    app = QApplication(sys.argv)
    app.setOrganizationName("UploadLab")
    app.setApplicationName("PyQt6UI")
    window = MainWindow(working_dir=working_dir)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
