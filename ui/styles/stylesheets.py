"""QSS stylesheets for the PyQt6 UI."""

COLOR_BG = "#f5f5f5"
COLOR_SURFACE = "#ffffff"
COLOR_SURFACE_ALT = "#eef3f8"
COLOR_BORDER = "#d6dde6"
COLOR_PRIMARY = "#0b5394"
COLOR_PRIMARY_DARK = "#083b69"
COLOR_ERROR = "#a61c00"
COLOR_SUCCESS = "#38761d"
COLOR_WARNING = "#7f6000"
COLOR_TEXT = "#243447"
COLOR_TEXT_MUTED = "#5d6b79"

MAIN_STYLESHEET = f"""
QMainWindow {{
    background: {COLOR_BG};
    color: {COLOR_TEXT};
}}

QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background: {COLOR_SURFACE};
}}

QTabBar::tab {{
    background: #dde6ef;
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background: {COLOR_SURFACE};
    color: {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY};
}}

QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: 600;
    background: {COLOR_SURFACE};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}

QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    background: {COLOR_SURFACE};
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_PRIMARY};
}}

QLineEdit:read-only, QTextEdit:read-only {{
    background: #fafcfe;
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QPushButton {{
    background: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    min-height: 30px;
    font-weight: 600;
}}

QPushButton:hover {{
    background: {COLOR_PRIMARY_DARK};
}}

QPushButton:disabled {{
    background: #c7d2de;
    color: #7b8a9a;
}}

QCheckBox {{
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
}}

QToolButton {{
    background: transparent;
    color: {COLOR_PRIMARY};
    border: none;
    font-weight: 600;
}}

QFrame[summaryCard="true"] {{
    background: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}

QLabel[summaryTitle="true"] {{
    color: {COLOR_TEXT_MUTED};
    font-size: 9pt;
    font-weight: 600;
}}

QLabel[summaryValue="true"] {{
    color: {COLOR_TEXT};
    font-size: 11pt;
    font-weight: 700;
}}

QFrame#actionBar {{
    background: {COLOR_SURFACE_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

QFrame#summaryStrip {{
    background: #f8fbfe;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

QLabel#stateBanner {{
    padding: 8px 12px;
    border-radius: 8px;
    background: #eaf2fb;
    color: {COLOR_PRIMARY};
    border: 1px solid #c7d8ea;
    font-weight: 600;
}}

QLabel#stateBanner[uiState="error"] {{
    background: #fdecea;
    color: {COLOR_ERROR};
    border: 1px solid #f2c4bc;
}}

QLabel#stateBanner[uiState="has_partial"],
QLabel#stateBanner[uiState="dry_run_stopped"] {{
    background: #fff5df;
    color: {COLOR_WARNING};
    border: 1px solid #f0ddb0;
}}

QLabel#stateBanner[uiState="finalize_success"],
QLabel#stateBanner[uiState="queue_ready"] {{
    background: #ecf7ea;
    color: {COLOR_SUCCESS};
    border: 1px solid #cfe5c8;
}}

QLabel#inlineNotice {{
    padding: 4px 8px;
    border-radius: 8px;
    background: #eef4fa;
    color: {COLOR_TEXT};
    border: 1px solid #d9e3ef;
    font-weight: 500;
}}

QLabel#inlineNotice[noticeLevel="success"] {{
    background: #ecf7ea;
    color: {COLOR_SUCCESS};
    border: 1px solid #cfe5c8;
}}

QLabel#inlineNotice[noticeLevel="warning"] {{
    background: #fff5df;
    color: {COLOR_WARNING};
    border: 1px solid #f0ddb0;
}}

QLabel#inlineNotice[noticeLevel="error"] {{
    background: #fdecea;
    color: {COLOR_ERROR};
    border: 1px solid #f2c4bc;
}}

QLabel[state="success"] {{
    color: {COLOR_SUCCESS};
    font-weight: 600;
}}

QLabel[state="warning"] {{
    color: {COLOR_WARNING};
    font-weight: 600;
}}

QLabel[state="error"] {{
    color: {COLOR_ERROR};
    font-weight: 600;
}}

QTableView {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    background: {COLOR_SURFACE};
    alternate-background-color: #f7fafc;
    gridline-color: #edf1f5;
}}

QTableView::item {{
    padding: 4px 6px;
}}

QTableView::item:selected {{
    background: #d8e8f8;
    color: {COLOR_TEXT};
}}

QHeaderView::section {{
    background: #e9eff5;
    color: {COLOR_TEXT};
    border: none;
    border-right: 1px solid {COLOR_BORDER};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px 6px;
    font-weight: 700;
}}

QScrollArea {{
    border: none;
}}

QSplitter::handle {{
    background: #dfe7ef;
    width: 6px;
}}

QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    background: #f7fafc;
    text-align: center;
    min-height: 20px;
}}

QProgressBar::chunk {{
    background: {COLOR_PRIMARY};
    border-radius: 5px;
}}

QStatusBar {{
    background: {COLOR_SURFACE};
    border-top: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT};
}}
"""

LOG_COLOR_BATCH = COLOR_PRIMARY
LOG_COLOR_EXTRACT = "#1565c0"
LOG_COLOR_UPLOAD = "#00796b"
LOG_COLOR_ERROR = COLOR_ERROR
LOG_COLOR_SUCCESS = COLOR_SUCCESS
LOG_COLOR_WARNING = COLOR_WARNING
LOG_COLOR_DEFAULT = COLOR_TEXT


def get_log_color(tag: str) -> str:
    """Return a display color for the given log tag."""

    tag_upper = tag.upper()
    if "BATCH" in tag_upper:
        return LOG_COLOR_BATCH
    if "EXTRACT" in tag_upper:
        return LOG_COLOR_EXTRACT
    if "UPLOAD" in tag_upper:
        return LOG_COLOR_UPLOAD
    if "ERROR" in tag_upper or "LOI" in tag_upper:
        return LOG_COLOR_ERROR
    if "SUCCESS" in tag_upper or "XONG" in tag_upper:
        return LOG_COLOR_SUCCESS
    if "WARNING" in tag_upper or "CANH" in tag_upper:
        return LOG_COLOR_WARNING
    return LOG_COLOR_DEFAULT
