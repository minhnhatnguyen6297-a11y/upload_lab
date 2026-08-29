from __future__ import annotations

import os
from pathlib import Path
import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QLabel,
    QLayout,
    QTableWidget,
    QWidget,
)


PRIMARY_COLOR = "#0067C0"
PRIMARY_HOVER_COLOR = "#1873D3"
PRIMARY_PRESSED_COLOR = "#005A9E"
SURFACE_COLOR = "#FFFFFF"
APP_BACKGROUND_COLOR = "#F4F6F9"
SUBTLE_SURFACE_COLOR = "#F8FAFC"
BORDER_COLOR = "#D1D5DB"
BORDER_LIGHT_COLOR = "#E2E8F0"
TEXT_COLOR = "#1E293B"
MUTED_TEXT_COLOR = "#64748B"
DANGER_COLOR = "#DC2626"
DANGER_HOVER_COLOR = "#B91C1C"

FONT_POINT_SIZE = 9
OUTER_MARGIN = 12
PAGE_MARGIN = 14
PANEL_MARGIN = 6
LAYOUT_SPACING = 8
CONTROL_MIN_HEIGHT = 30
BUTTON_HORIZONTAL_PADDING = 12
BUTTON_VERTICAL_PADDING = 5
FIELD_HORIZONTAL_PADDING = 10
TABLE_ROW_HEIGHT = 32
TABLE_HEADER_HEIGHT = 30
CORNER_RADIUS = 6

PRIMARY_BUTTON_NAMES = (
    "downloadExcelButton",
    "scanFolderButton",
    "uploadSelectedButton",
    "continueUploadButton",
)
PRIMARY_BUTTON_SELECTOR = ",\n".join(
    f"QPushButton#{object_name}" for object_name in PRIMARY_BUTTON_NAMES
)
PRIMARY_BUTTON_HOVER_SELECTOR = ",\n".join(
    f"QPushButton#{object_name}:hover" for object_name in PRIMARY_BUTTON_NAMES
)
PRIMARY_BUTTON_PRESSED_SELECTOR = ",\n".join(
    f"QPushButton#{object_name}:pressed" for object_name in PRIMARY_BUTTON_NAMES
)
PRIMARY_BUTTON_DISABLED_SELECTOR = ",\n".join(
    f"QPushButton#{object_name}:disabled" for object_name in PRIMARY_BUTTON_NAMES
)

LAYOUT_MARGINS = {
    "mainLayout": (OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN),
    "excelLayout": (PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN),
    "folderLayout": (PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN),
    "regexLayout": (PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN),
    "excelDisplayLayout": (PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN),
    "excelMissingLayout": (PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN),
    "excelIssueLayout": (PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN),
    "folderNumbersLayout": (PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN),
}

CUSTOM_QSS = f"""
QWidget#centralWidget {{
    background-color: {APP_BACKGROUND_COLOR};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER_LIGHT_COLOR};
    border-radius: {CORNER_RADIUS}px;
    background-color: {SURFACE_COLOR};
}}

QTabBar::tab {{
    min-height: 26px;
    padding: 7px 18px;
    margin-right: 3px;
    color: {MUTED_TEXT_COLOR};
    background-color: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    color: {PRIMARY_COLOR};
    background-color: #EFF6FF;
    border-radius: 4px 4px 0 0;
}}

QTabBar::tab:selected {{
    color: {PRIMARY_COLOR};
    background-color: {SURFACE_COLOR};
    border-bottom: 3px solid {PRIMARY_COLOR};
    font-weight: 600;
}}

QPushButton {{
    min-height: {CONTROL_MIN_HEIGHT}px;
    padding: {BUTTON_VERTICAL_PADDING}px {BUTTON_HORIZONTAL_PADDING}px;
    color: {TEXT_COLOR};
    background-color: #FFFFFF;
    border: 1px solid {BORDER_COLOR};
    border-radius: {CORNER_RADIUS}px;
    font-weight: 500;
}}

QPushButton:hover {{
    color: #0369A1;
    background-color: #F8FAFC;
    border-color: #94A3B8;
}}

QPushButton:pressed {{
    background-color: #E2E8F0;
    border-color: {PRIMARY_COLOR};
}}

QPushButton:disabled {{
    color: #94A3B8;
    background-color: #F1F5F9;
    border-color: #E2E8F0;
}}

{PRIMARY_BUTTON_SELECTOR} {{
    color: #FFFFFF;
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
    font-weight: 600;
}}

{PRIMARY_BUTTON_HOVER_SELECTOR} {{
    color: #FFFFFF;
    background-color: {PRIMARY_HOVER_COLOR};
    border-color: {PRIMARY_HOVER_COLOR};
}}

{PRIMARY_BUTTON_PRESSED_SELECTOR} {{
    color: #FFFFFF;
    background-color: {PRIMARY_PRESSED_COLOR};
    border-color: {PRIMARY_PRESSED_COLOR};
}}

{PRIMARY_BUTTON_DISABLED_SELECTOR} {{
    color: #94A3B8;
    background-color: #E2E8F0;
    border-color: #CBD5E1;
}}

QPushButton#stopUploadButton:enabled {{
    color: #FFFFFF;
    background-color: {DANGER_COLOR};
    border-color: {DANGER_COLOR};
    font-weight: 600;
}}

QPushButton#stopUploadButton:enabled:hover {{
    background-color: {DANGER_HOVER_COLOR};
    border-color: {DANGER_HOVER_COLOR};
}}

QLineEdit,
QComboBox {{
    min-height: {CONTROL_MIN_HEIGHT}px;
    padding-left: {FIELD_HORIZONTAL_PADDING}px;
    padding-right: {FIELD_HORIZONTAL_PADDING}px;
    color: {TEXT_COLOR};
    background-color: {SURFACE_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: {CORNER_RADIUS}px;
    selection-color: white;
    selection-background-color: {PRIMARY_COLOR};
}}

QLineEdit:focus,
QComboBox:focus {{
    border: 2px solid {PRIMARY_COLOR};
}}

QComboBox {{
    padding-right: 28px;
}}

QTableWidget {{
    color: {TEXT_COLOR};
    background-color: {SURFACE_COLOR};
    alternate-background-color: {SUBTLE_SURFACE_COLOR};
    gridline-color: {BORDER_LIGHT_COLOR};
    border: 1px solid {BORDER_LIGHT_COLOR};
    border-radius: {CORNER_RADIUS}px;
    selection-color: #0F172A;
    selection-background-color: #E0EFFF;
}}

QTableWidget::item {{
    padding: 5px 8px;
}}

QTableWidget QHeaderView::section {{
    min-height: {TABLE_HEADER_HEIGHT}px;
    padding: 5px 8px;
    color: #334155;
    background-color: #F8FAFC;
    border: none;
    border-right: 1px solid #E2E8F0;
    border-bottom: 2px solid #CBD5E1;
    font-weight: 600;
}}

QLabel#excelDisplayLabel,
QLabel#excelMissingLabel,
QLabel#excelIssueLabel {{
    color: #334155;
    font-weight: 600;
    font-size: 9.5pt;
}}

QLabel#excelSummaryLabel,
QLabel#scanSummaryLabel {{
    padding: 8px 12px;
    color: #0369A1;
    background-color: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-radius: {CORNER_RADIUS}px;
    font-weight: 600;
}}

QLabel#regexPlaceholder {{
    padding: 14px 16px;
    color: {MUTED_TEXT_COLOR};
    background-color: {SUBTLE_SURFACE_COLOR};
    border: 1px solid {BORDER_LIGHT_COLOR};
    border-radius: {CORNER_RADIUS}px;
}}

QProgressBar {{
    min-height: 16px;
    color: #1E293B;
    background-color: #E2E8F0;
    border: none;
    border-radius: 4px;
    text-align: center;
    font-weight: 600;
    font-size: 8.5pt;
}}

QProgressBar::chunk {{
    background-color: {PRIMARY_COLOR};
    border-radius: 4px;
}}

QPlainTextEdit#logText {{
    padding: 10px;
    color: #E2E8F0;
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: {CORNER_RADIUS}px;
    font-family: "Cascadia Code", "Consolas", "Courier New", "Tahoma", monospace;
    font-size: 9pt;
}}

QSplitter::handle {{
    background-color: #E2E8F0;
}}

QSplitter::handle:vertical {{
    height: 6px;
}}
"""


def _application_font() -> QFont:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "tahoma.ttf", "arial.ttf"):
        font_path = windows_fonts / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))

    families = set(QFontDatabase.families())
    preferred_families = (
        "Segoe UI Variable Text",
        "Segoe UI",
        "Tahoma",
        "Arial",
        "Calibri",
        "Noto Sans",
        "DejaVu Sans",
        ".VnTime",
        "VNI-Times",
    )
    family = next((name for name in preferred_families if name in families), None)
    if family is None:
        family = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    
    font = QFont(family, FONT_POINT_SIZE)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


def apply_theme(app: QApplication) -> None:
    qdarktheme.setup_theme("light", custom_colors={"primary": PRIMARY_COLOR})
    app.setFont(_application_font())
    app.setStyleSheet(f"{app.styleSheet()}\n{CUSTOM_QSS}")


def apply_widget_metrics(root: QWidget) -> None:
    for layout in root.findChildren(QLayout):
        layout.setSpacing(LAYOUT_SPACING)

    for object_name, margins in LAYOUT_MARGINS.items():
        layout = root.findChild(QLayout, object_name)
        if layout is not None:
            layout.setContentsMargins(*margins)

    for table in root.findChildren(QTableWidget):
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        table.verticalHeader().setMinimumSectionSize(TABLE_ROW_HEIGHT)
        table.horizontalHeader().setMinimumHeight(TABLE_HEADER_HEIGHT)
        table.horizontalHeader().setStretchLastSection(False)

    excel_display_table = root.findChild(QTableWidget, "excelDisplayTable")
    if excel_display_table is not None:
        excel_display_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    for object_name in (
        "excelMissingTable",
        "excelIssueTable",
        "folderNumbersTable",
    ):
        table = root.findChild(QTableWidget, object_name)
        if table is not None:
            table.horizontalHeader().setStretchLastSection(True)

    regex_layout = root.findChild(QLayout, "regexLayout")
    regex_placeholder = root.findChild(QLabel, "regexPlaceholder")
    if regex_layout is not None and regex_placeholder is not None:
        regex_layout.setAlignment(
            regex_placeholder,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
