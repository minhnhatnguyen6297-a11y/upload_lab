from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFileDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QTabWidget, QTableWidget, QWidget

from batch_scan import BASE_DIR
from ui.services.contract_book_audit import analyze_contract_book
from ui_qt.widgets import set_table_rows


class UploadLabMainWindow(QMainWindow):
    def __init__(self, *, working_dir: Path = BASE_DIR):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.contract_book_analysis = None
        self.ui: QWidget | None = None
        self.excelPathEdit: QLineEdit | None = None
        self.browseExcelButton: QPushButton | None = None
        self.loadExcelButton: QPushButton | None = None
        self.excelSummaryLabel: QLabel | None = None
        self.excelResultTabs: QTabWidget | None = None
        self.parsedExcelTable: QTableWidget | None = None
        self.missingExcelTable: QTableWidget | None = None
        self.excelWarningTable: QTableWidget | None = None
        self.excelParseErrorTable: QTableWidget | None = None
        self.setWindowTitle("Upload Lab")
        self.resize(1280, 860)
        self._load_ui()
        self._connect_excel_tab()

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

    def _connect_excel_tab(self) -> None:
        if self.ui is None:
            return

        self.excelPathEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "excelPathEdit"))
        self.browseExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "browseExcelButton"))
        self.loadExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "loadExcelButton"))
        self.excelSummaryLabel = cast(QLabel, self.ui.findChild(QLabel, "excelSummaryLabel"))
        self.excelResultTabs = cast(QTabWidget, self.ui.findChild(QTabWidget, "excelResultTabs"))
        self.parsedExcelTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "parsedExcelTable"))
        self.missingExcelTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "missingExcelTable"))
        self.excelWarningTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelWarningTable"))
        self.excelParseErrorTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelParseErrorTable"))

        if self.browseExcelButton is not None:
            self.browseExcelButton.clicked.connect(self.browse_excel)
        if self.loadExcelButton is not None:
            self.loadExcelButton.clicked.connect(self.load_excel)

    def browse_excel(self) -> None:
        if self.ui is None or self.excelPathEdit is None:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chon Excel so cong chung",
            str(self.working_dir),
            "Excel files (*.xlsx *.xlsm *.xls)",
        )
        if path:
            self.excelPathEdit.setText(path)
            self.load_excel()

    def load_excel(self) -> None:
        if self.ui is None or self.excelPathEdit is None:
            return

        path = self.excelPathEdit.text().strip()
        if not path:
            QMessageBox.warning(self, "Upload Lab", "Chua chon file Excel.")
            return

        try:
            self.contract_book_analysis = analyze_contract_book(path)
        except Exception as exc:
            QMessageBox.critical(self, "Upload Lab", str(exc))
            return

        analysis = self.contract_book_analysis
        if (
            self.parsedExcelTable is None
            or self.missingExcelTable is None
            or self.excelWarningTable is None
            or self.excelParseErrorTable is None
            or self.excelSummaryLabel is None
        ):
            QMessageBox.critical(self, "Upload Lab", "Khong tim thay widget Excel tren giao dien.")
            return

        set_table_rows(
            self.parsedExcelTable,
            ["Dong", "So", "Ngay", "Gia tri goc"],
            [[row.row_index, row.contract_no, row.raw_date, row.raw_contract_no] for row in analysis.valid_rows],
        )
        set_table_rows(
            self.missingExcelTable,
            ["So thieu", "Nam", "STT"],
            [[item.contract_no, item.year, item.ordinal] for item in analysis.missing_numbers],
        )
        set_table_rows(
            self.excelWarningTable,
            ["Dong", "Loai", "So goc", "Ngay", "Ly do"],
            [[warning.row_index, warning.kind.value, warning.raw_contract_no, warning.raw_date, warning.message] for warning in analysis.warning_rows],
        )
        set_table_rows(
            self.excelParseErrorTable,
            ["Dong", "So goc", "Ngay", "Ly do"],
            [[warning.row_index, warning.raw_contract_no, warning.raw_date, warning.message] for warning in analysis.parse_error_rows],
        )
        self.excelSummaryLabel.setText(
            f"Excel={len(analysis.valid_rows)} | thieu={len(analysis.missing_numbers)} | canh bao={len(analysis.warning_rows)} | loi={len(analysis.parse_error_rows)}"
        )
