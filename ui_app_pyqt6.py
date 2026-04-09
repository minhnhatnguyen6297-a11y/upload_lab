"""Main PyQt6 application entry point."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow


def main() -> int:
    """Run the application."""
    # Get working directory
    working_dir = Path(__file__).parent
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow(working_dir=working_dir)
    window.show()
    
    # Run
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
