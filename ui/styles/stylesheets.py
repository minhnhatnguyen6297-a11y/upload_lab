"""QSS stylesheets for PyQt6 UI."""

# Colors
COLOR_BG = "#F5F5F5"
COLOR_PRIMARY = "#0b5394"
COLOR_ERROR = "#a61c00"
COLOR_SUCCESS = "#38761d"
COLOR_WARNING = "#7f6000"
COLOR_TEXT = "#333333"
COLOR_TEXT_LIGHT = "#666666"

# Main stylesheet
MAIN_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}

QTabWidget::pane {{
    border: 1px solid #ddd;
}}

QTabBar::tab {{
    background-color: #e0e0e0;
    color: {COLOR_TEXT};
    padding: 6px 16px;
    margin-right: 2px;
    border: 1px solid #ccc;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: white;
    color: {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY};
}}

QGroupBox {{
    color: {COLOR_TEXT};
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: 500;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px 0 4px;
}}

QLineEdit {{
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 6px;
    background-color: white;
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_PRIMARY};
}}

QLineEdit:read-only {{
    background-color: #f9f9f9;
    color: {COLOR_TEXT_LIGHT};
}}

QLineEdit:focus {{
    border: 2px solid {COLOR_PRIMARY};
}}

QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: #0a4577;
}}

QPushButton:pressed {{
    background-color: #073555;
}}

QPushButton:disabled {{
    background-color: #ccc;
    color: #999;
}}

QCheckBox {{
    color: {COLOR_TEXT};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #ccc;
    border-radius: 3px;
    background-color: white;
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
}}

QSpinBox, QDoubleSpinBox {{
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px;
    background-color: white;
    color: {COLOR_TEXT};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {COLOR_PRIMARY};
}}

QTextEdit {{
    border: 1px solid #ccc;
    border-radius: 4px;
    background-color: white;
    color: {COLOR_TEXT};
    font-family: "Courier New";
    font-size: 9pt;
}}

QTableWidget {{
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: white;
    color: {COLOR_TEXT};
    gridline-color: #f0f0f0;
}}

QTableWidget::item {{
    padding: 4px;
}}

QTableWidget::item:selected {{
    background-color: {COLOR_PRIMARY};
    color: white;
}}

QHeaderView::section {{
    background-color: #e8e8e8;
    color: {COLOR_TEXT};
    padding: 6px;
    border: 1px solid #ddd;
    font-weight: 500;
}}

QProgressBar {{
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #f9f9f9;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_PRIMARY};
    border-radius: 3px;
}}

QLabel {{
    color: {COLOR_TEXT};
}}

QStatusBar {{
    background-color: #f0f0f0;
    border-top: 1px solid #ddd;
    color: {COLOR_TEXT};
}}

QMenuBar {{
    background-color: white;
    color: {COLOR_TEXT};
    border-bottom: 1px solid #ddd;
}}

QMenuBar::item:selected {{
    background-color: {COLOR_PRIMARY};
    color: white;
}}

QMenu {{
    background-color: white;
    color: {COLOR_TEXT};
    border: 1px solid #ddd;
}}

QMenu::item:selected {{
    background-color: {COLOR_PRIMARY};
    color: white;
}}
"""

# Color classes for log display
LOG_COLOR_BATCH = COLOR_PRIMARY
LOG_COLOR_EXTRACT = "#1565c0"
LOG_COLOR_UPLOAD = "#00796b"
LOG_COLOR_ERROR = COLOR_ERROR
LOG_COLOR_SUCCESS = COLOR_SUCCESS
LOG_COLOR_WARNING = COLOR_WARNING
LOG_COLOR_DEFAULT = COLOR_TEXT


def get_log_color(tag: str) -> str:
    """Get color for log message tag."""
    tag_upper = tag.upper()
    if "BATCH" in tag_upper:
        return LOG_COLOR_BATCH
    elif "EXTRACT" in tag_upper:
        return LOG_COLOR_EXTRACT
    elif "UPLOAD" in tag_upper:
        return LOG_COLOR_UPLOAD
    elif "ERROR" in tag_upper or "LOI" in tag_upper:
        return LOG_COLOR_ERROR
    elif "SUCCESS" in tag_upper or "XONG" in tag_upper:
        return LOG_COLOR_SUCCESS
    elif "WARNING" in tag_upper or "CANH" in tag_upper:
        return LOG_COLOR_WARNING
    return LOG_COLOR_DEFAULT
