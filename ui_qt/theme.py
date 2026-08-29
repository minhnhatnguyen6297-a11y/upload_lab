from __future__ import annotations

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


PRIMARY_COLOR = "#0078D4"
PRIMARY_HOVER_COLOR = "#106EBE"
PRIMARY_PRESSED_COLOR = "#005A9E"
SURFACE_COLOR = "#FFFFFF"
APP_BACKGROUND_COLOR = "#F4F7FA"
SUBTLE_SURFACE_COLOR = "#F7F9FB"
BORDER_COLOR = "#CBD4DE"
TEXT_COLOR = "#243447"
MUTED_TEXT_COLOR = "#5E6C7B"

FONT_POINT_SIZE = 9
OUTER_MARGIN = 12
PAGE_MARGIN = 16
PANEL_MARGIN = 6
LAYOUT_SPACING = 8
CONTROL_MIN_HEIGHT = 28
BUTTON_HORIZONTAL_PADDING = 11
BUTTON_VERTICAL_PADDING = 4
FIELD_HORIZONTAL_PADDING = 9
TABLE_ROW_HEIGHT = 30
TABLE_HEADER_HEIGHT = 28
CORNER_RADIUS = 5

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
    border: 1px solid {BORDER_COLOR};
    border-radius: {CORNER_RADIUS}px;
    background-color: {SURFACE_COLOR};
}}

QTabBar::tab {{
    min-height: 22px;
    padding: 6px 14px;
    margin-right: 2px;
    color: {MUTED_TEXT_COLOR};
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:hover {{
    color: {PRIMARY_COLOR};
    background-color: #EDF6FD;
}}

QTabBar::tab:selected {{
    color: {PRIMARY_COLOR};
    background-color: {SURFACE_COLOR};
    border-bottom: 2px solid {PRIMARY_COLOR};
    font-weight: 600;
}}

QPushButton {{
    min-height: {CONTROL_MIN_HEIGHT}px;
    padding: {BUTTON_VERTICAL_PADDING}px {BUTTON_HORIZONTAL_PADDING}px;
    color: {TEXT_COLOR};
    background-color: #F8FAFC;
    border: 1px solid #B8C3CE;
    border-radius: {CORNER_RADIUS}px;
}}

QPushButton:hover {{
    color: #0B5FA5;
    background-color: #EDF6FD;
    border-color: #7CB7E5;
}}

QPushButton:pressed {{
    background-color: #DCEEFE;
    border-color: {PRIMARY_COLOR};
}}

QPushButton:disabled {{
    color: #9AA6B2;
    background-color: #F1F3F5;
    border-color: #D9DEE3;
}}

{PRIMARY_BUTTON_SELECTOR} {{
    color: white;
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
    font-weight: 600;
}}

{PRIMARY_BUTTON_HOVER_SELECTOR} {{
    color: white;
    background-color: {PRIMARY_HOVER_COLOR};
    border-color: {PRIMARY_HOVER_COLOR};
}}

{PRIMARY_BUTTON_PRESSED_SELECTOR} {{
    color: white;
    background-color: {PRIMARY_PRESSED_COLOR};
    border-color: {PRIMARY_PRESSED_COLOR};
}}

{PRIMARY_BUTTON_DISABLED_SELECTOR} {{
    color: #8B98A5;
    background-color: #E5E9ED;
    border-color: #D5DBE1;
}}

QLineEdit,
QComboBox {{
    min-height: {CONTROL_MIN_HEIGHT}px;
    padding-left: {FIELD_HORIZONTAL_PADDING}px;
    padding-right: {FIELD_HORIZONTAL_PADDING}px;
    color: {TEXT_COLOR};
    background-color: {SURFACE_COLOR};
    border: 1px solid #B8C3CE;
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
    gridline-color: #E1E7ED;
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    selection-color: white;
    selection-background-color: {PRIMARY_COLOR};
}}

QTableWidget::item {{
    padding: 5px 8px;
}}

QTableWidget QHeaderView::section {{
    min-height: {TABLE_HEADER_HEIGHT}px;
    padding: 4px 8px;
    color: #33465B;
    background-color: #EAF0F5;
    border: none;
    border-right: 1px solid #D2DAE2;
    border-bottom: 1px solid #C7D1DA;
    font-weight: 600;
}}

QLabel#excelDisplayLabel,
QLabel#excelMissingLabel,
QLabel#excelIssueLabel {{
    color: #33465B;
    font-weight: 600;
}}

QLabel#excelSummaryLabel,
QLabel#scanSummaryLabel {{
    padding: 6px 9px;
    color: #24577C;
    background-color: #EAF5FC;
    border: 1px solid #C9E5F8;
    border-radius: 4px;
}}

QLabel#regexPlaceholder {{
    padding: 12px 14px;
    color: {MUTED_TEXT_COLOR};
    background-color: {SUBTLE_SURFACE_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: {CORNER_RADIUS}px;
}}

QProgressBar {{
    min-height: 18px;
    color: #33465B;
    background-color: #E8EDF2;
    border: 1px solid #D2DAE2;
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {PRIMARY_COLOR};
    border-radius: 3px;
}}

QPlainTextEdit#logText {{
    padding: 8px;
    color: #314158;
    background-color: #FAFBFC;
    border: 1px solid {BORDER_COLOR};
    border-radius: {CORNER_RADIUS}px;
}}

QSplitter::handle {{
    background-color: #E3E9EF;
}}

QSplitter::handle:vertical {{
    height: 5px;
}}
"""


def _application_font() -> QFont:
    families = set(QFontDatabase.families())
    preferred_families = ("Segoe UI", "Inter", "Arial", "Noto Sans", "DejaVu Sans")
    family = next((name for name in preferred_families if name in families), None)
    if family is None:
        family = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    return QFont(family, FONT_POINT_SIZE)


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
