from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import re
import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QTabWidget


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui_qt.main_window import UploadLabMainWindow
from ui_qt.theme import apply_theme, apply_widget_metrics


def load_offscreen_fonts() -> None:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf"):
        font_path = windows_fonts / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def sanitize_filename_part(value: str, *, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return sanitized or fallback


def render_ui_preview(label: str = "current") -> list[Path]:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    load_offscreen_fonts()
    apply_theme(app)

    output_dir = REPO_ROOT / "design_preview"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = sanitize_filename_part(label, fallback="current")
    saved_paths: list[Path] = []

    with tempfile.TemporaryDirectory() as temporary_dir:
        window = UploadLabMainWindow(working_dir=Path(temporary_dir))
        apply_widget_metrics(window)
        window.resize(1280, 860)
        window.show()
        app.processEvents()

        if window.ui is None:
            raise RuntimeError("UploadLabMainWindow did not load its UI.")
        main_tabs = window.ui.findChild(QTabWidget, "mainTabs")
        if main_tabs is None:
            raise RuntimeError("Could not find QTabWidget named 'mainTabs'.")

        for tab_index in range(main_tabs.count()):
            main_tabs.setCurrentIndex(tab_index)
            app.processEvents()
            tab_name = sanitize_filename_part(
                main_tabs.tabText(tab_index),
                fallback=f"tab{tab_index}",
            )
            output_path = (
                output_dir / f"{safe_label}_tab{tab_index}_{tab_name}.png"
            ).resolve()
            if not window.grab().save(str(output_path), "PNG"):
                raise RuntimeError(f"Could not save UI preview: {output_path}")
            saved_paths.append(output_path)
            print(output_path)

        window.close()
        app.processEvents()

    return saved_paths


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "current"
    render_ui_preview(label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
