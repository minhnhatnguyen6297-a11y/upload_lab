from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
)


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


def color_hex(color) -> str:
    return color.name().upper()


def dump_widget(label: str, widget) -> None:
    if widget is None:
        print(f"{label}: MISSING")
        return
    geometry = widget.geometry()
    font = widget.font()
    palette = widget.palette()
    print(
        f"{label}: type={type(widget).__name__} "
        f"geo={geometry.x()},{geometry.y()} {geometry.width()}x{geometry.height()} "
        f"font={font.family()} {font.pointSize()}pt w={font.weight()} "
        f"fg={color_hex(palette.color(palette.ColorRole.WindowText))} "
        f"bg={color_hex(palette.color(palette.ColorRole.Window))}"
    )


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    load_offscreen_fonts()
    apply_theme(app)

    print(f"app.font={app.font().family()} {app.font().pointSize()}pt")
    print(f"stylesheet_chars={len(app.styleSheet())}")
    print(f"stylesheet_has_0078D4={'#0078D4' in app.styleSheet()}")
    print(f"stylesheet_has_primary_scan={'QPushButton#scanFolderButton' in app.styleSheet()}")

    with tempfile.TemporaryDirectory() as temporary_dir:
        window = UploadLabMainWindow(working_dir=Path(temporary_dir))
        apply_widget_metrics(window)
        window.resize(1280, 860)
        window.show()
        app.processEvents()

        print(f"window={window.width()}x{window.height()} title={window.windowTitle()!r}")
        dump_widget("centralWidget", window.centralWidget())

        main_tabs = window.ui.findChild(QTabWidget, "mainTabs")
        dump_widget("mainTabs", main_tabs)
        if main_tabs is not None:
            print(f"tabs={main_tabs.count()} current={main_tabs.currentIndex()}")
            for index in range(main_tabs.count()):
                print(f"  tab[{index}]={main_tabs.tabText(index)!r}")

        for name in (
            "fromDateEdit",
            "toDateEdit",
            "excelPathEdit",
            "folderPathEdit",
        ):
            dump_widget(name, window.ui.findChild(QLineEdit, name))

        for name in (
            "configureUploaderButton",
            "downloadExcelButton",
            "browseExcelButton",
            "loadExcelButton",
            "scanFolderButton",
            "uploadSelectedButton",
            "continueUploadButton",
            "stopUploadButton",
        ):
            dump_widget(name, window.ui.findChild(QPushButton, name))

        for name in ("notaryComboBox",):
            dump_widget(name, window.ui.findChild(QComboBox, name))

        for name in (
            "excelSummaryLabel",
            "scanSummaryLabel",
            "excelDisplayLabel",
            "regexPlaceholder",
        ):
            dump_widget(name, window.ui.findChild(QLabel, name))

        for name in (
            "excelDisplayTable",
            "excelMissingTable",
            "excelIssueTable",
            "folderNumbersTable",
        ):
            table = window.ui.findChild(QTableWidget, name)
            dump_widget(name, table)
            if table is not None:
                print(
                    f"  {name}.rowHeightDefault={table.verticalHeader().defaultSectionSize()} "
                    f"headerMin={table.horizontalHeader().minimumHeight()} "
                    f"altRows={table.alternatingRowColors()} "
                    f"stretchLast={table.horizontalHeader().stretchLastSection()}"
                )

        for name in (
            "mainLayout",
            "excelLayout",
            "folderLayout",
            "regexLayout",
            "excelDisplayLayout",
        ):
            layout = window.ui.findChild(QLayout, name)
            if layout is None:
                print(f"{name}: MISSING")
                continue
            margins = layout.contentsMargins()
            print(
                f"{name}: spacing={layout.spacing()} "
                f"margins={margins.left()},{margins.top()},{margins.right()},{margins.bottom()}"
            )

        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
