from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import QFile, QThread, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QWidget,
)

from batch_scan import BASE_DIR
from playwright_uploader import default_export_from_date, default_export_to_date, load_upload_queue
from ui.services.contract_book_audit import analyze_contract_book
from ui.services.scan_classification_service import classify_scan_records
from ui.services.upload_selection_service import UploadSelection
from ui_qt.widgets import (
    checked_record_ids,
    configure_audit_table_scrollbars,
    open_with_windows_default,
    set_checkable_upload_rows,
    set_table_rows,
)
from ui_qt.workers import FolderScanWorker

EXCEL_DISPLAY_HEADERS = ["Ngay", "So cong chung", "Dong Excel"]
EXCEL_MISSING_HEADERS = ["So thieu", "Nam", "STT"]
EXCEL_ISSUE_HEADERS = ["Loai loi", "Dong", "Ngay", "So goc", "So chuan", "Ly do"]
SCAN_NOT_IN_EXCEL_HEADERS = ["ID", "So", "Ly do", "File"]
SCAN_MISSING_FIELDS_HEADERS = ["ID", "So", "Thieu", "File"]
SCAN_WEB_DUPLICATE_HEADERS = ["ID", "So", "Ly do", "File"]
SCAN_LOCAL_DUPLICATE_HEADERS = ["ID", "So", "Ly do", "File"]
SCAN_EXCEL_MISSING_HEADERS = ["So trong Excel chua thay file"]


class UploadLabMainWindow(QMainWindow):
    def __init__(self, *, working_dir: Path = BASE_DIR):
        super().__init__()
        self.working_dir = Path(working_dir)
        self.contract_book_analysis = None
        self.current_manifest_path: Path | None = None
        self.scanThread: QThread | None = None
        self.scanWorker: FolderScanWorker | None = None
        self.ui: QWidget | None = None
        self.fromDateEdit: QLineEdit | None = None
        self.toDateEdit: QLineEdit | None = None
        self.excelPathEdit: QLineEdit | None = None
        self.browseExcelButton: QPushButton | None = None
        self.loadExcelButton: QPushButton | None = None
        self.excelSummaryLabel: QLabel | None = None
        self.excelDisplayTable: QTableWidget | None = None
        self.excelMissingTable: QTableWidget | None = None
        self.excelIssueTable: QTableWidget | None = None
        self.folderPathEdit: QLineEdit | None = None
        self.browseFolderButton: QPushButton | None = None
        self.scanFolderButton: QPushButton | None = None
        self.scanProgressBar: QProgressBar | None = None
        self.scanSummaryLabel: QLabel | None = None
        self.scanResultTabs: QTabWidget | None = None
        self.validUploadTable: QTableWidget | None = None
        self.selectAllValidButton: QPushButton | None = None
        self.clearValidSelectionButton: QPushButton | None = None
        self.uploadSelectedButton: QPushButton | None = None
        self.notInExcelTable: QTableWidget | None = None
        self.missingFieldsTable: QTableWidget | None = None
        self.webDuplicateTable: QTableWidget | None = None
        self.localDuplicateTable: QTableWidget | None = None
        self.excelMissingInFolderTable: QTableWidget | None = None
        self.logText: QPlainTextEdit | None = None
        self.validUploadSelection = UploadSelection()
        self.setWindowTitle("Upload Lab")
        self.resize(1280, 860)
        self._load_ui()
        self._connect_excel_tab()
        self._connect_folder_tab()

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

        self.fromDateEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "fromDateEdit"))
        self.toDateEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "toDateEdit"))
        self.excelPathEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "excelPathEdit"))
        self.browseExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "browseExcelButton"))
        self.loadExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "loadExcelButton"))
        self.excelSummaryLabel = cast(QLabel, self.ui.findChild(QLabel, "excelSummaryLabel"))
        self.excelDisplayTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelDisplayTable"))
        self.excelMissingTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelMissingTable"))
        self.excelIssueTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelIssueTable"))

        if self.fromDateEdit is not None and not self.fromDateEdit.text().strip():
            self.fromDateEdit.setText(default_export_from_date())
        if self.toDateEdit is not None and not self.toDateEdit.text().strip():
            self.toDateEdit.setText(default_export_to_date())

        for table, horizontal in (
            (self.excelDisplayTable, False),
            (self.excelMissingTable, False),
            (self.excelIssueTable, True),
        ):
            if table is not None:
                configure_audit_table_scrollbars(table, horizontal=horizontal)

        if self.browseExcelButton is not None:
            self.browseExcelButton.clicked.connect(self.browse_excel)
        if self.loadExcelButton is not None:
            self.loadExcelButton.clicked.connect(self.load_excel)

    def _connect_folder_tab(self) -> None:
        if self.ui is None:
            return

        self.folderPathEdit = cast(QLineEdit, self.ui.findChild(QLineEdit, "folderPathEdit"))
        self.browseFolderButton = cast(QPushButton, self.ui.findChild(QPushButton, "browseFolderButton"))
        self.scanFolderButton = cast(QPushButton, self.ui.findChild(QPushButton, "scanFolderButton"))
        self.scanProgressBar = cast(QProgressBar, self.ui.findChild(QProgressBar, "scanProgressBar"))
        self.scanSummaryLabel = cast(QLabel, self.ui.findChild(QLabel, "scanSummaryLabel"))
        self.scanResultTabs = cast(QTabWidget, self.ui.findChild(QTabWidget, "scanResultTabs"))
        self.validUploadTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "validUploadTable"))
        self.selectAllValidButton = cast(QPushButton, self.ui.findChild(QPushButton, "selectAllValidButton"))
        self.clearValidSelectionButton = cast(QPushButton, self.ui.findChild(QPushButton, "clearValidSelectionButton"))
        self.uploadSelectedButton = cast(QPushButton, self.ui.findChild(QPushButton, "uploadSelectedButton"))
        self.notInExcelTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "notInExcelTable"))
        self.missingFieldsTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "missingFieldsTable"))
        self.webDuplicateTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "webDuplicateTable"))
        self.localDuplicateTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "localDuplicateTable"))
        self.excelMissingInFolderTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelMissingInFolderTable"))
        self.logText = cast(QPlainTextEdit, self.ui.findChild(QPlainTextEdit, "logText"))

        if self.browseFolderButton is not None:
            self.browseFolderButton.clicked.connect(self.browse_folder)
        if self.scanFolderButton is not None:
            self.scanFolderButton.clicked.connect(self.start_folder_scan)
        if self.selectAllValidButton is not None:
            self.selectAllValidButton.clicked.connect(self.select_all_valid_upload_rows)
        if self.clearValidSelectionButton is not None:
            self.clearValidSelectionButton.clicked.connect(self.clear_valid_upload_selection)
        if self.uploadSelectedButton is not None:
            self.uploadSelectedButton.clicked.connect(self.handle_upload_selected)

        for table in (
            self.validUploadTable,
            self.notInExcelTable,
            self.missingFieldsTable,
            self.webDuplicateTable,
            self.localDuplicateTable,
        ):
            if table is not None:
                table.cellDoubleClicked.connect(lambda row, _column, table=table: self._open_scan_table_source_file(table, row))
        if self.validUploadTable is not None:
            self.validUploadTable.itemChanged.connect(self._handle_valid_upload_item_changed)

    def _reset_excel_results(self, summary_text: str) -> None:
        self.contract_book_analysis = None
        if (
            self.excelDisplayTable is None
            or self.excelMissingTable is None
            or self.excelIssueTable is None
            or self.excelSummaryLabel is None
        ):
            return

        set_table_rows(self.excelDisplayTable, EXCEL_DISPLAY_HEADERS, [], resize_columns=False)
        set_table_rows(self.excelMissingTable, EXCEL_MISSING_HEADERS, [], resize_columns=False)
        set_table_rows(self.excelIssueTable, EXCEL_ISSUE_HEADERS, [], resize_columns=False)
        self.excelSummaryLabel.setText(summary_text)

    def _reset_folder_results(self, summary_text: str) -> None:
        if (
            self.scanProgressBar is None
            or self.scanSummaryLabel is None
            or self.validUploadTable is None
            or self.notInExcelTable is None
            or self.missingFieldsTable is None
            or self.webDuplicateTable is None
            or self.localDuplicateTable is None
            or self.excelMissingInFolderTable is None
        ):
            return

        self.current_manifest_path = None
        self.validUploadSelection = UploadSelection()
        self.scanProgressBar.setValue(0)
        self.scanSummaryLabel.setText(summary_text)
        set_checkable_upload_rows(self.validUploadTable, [])
        set_table_rows(self.notInExcelTable, SCAN_NOT_IN_EXCEL_HEADERS, [], resize_columns=False)
        set_table_rows(self.missingFieldsTable, SCAN_MISSING_FIELDS_HEADERS, [], resize_columns=False)
        set_table_rows(self.webDuplicateTable, SCAN_WEB_DUPLICATE_HEADERS, [], resize_columns=False)
        set_table_rows(self.localDuplicateTable, SCAN_LOCAL_DUPLICATE_HEADERS, [], resize_columns=False)
        set_table_rows(self.excelMissingInFolderTable, SCAN_EXCEL_MISSING_HEADERS, [], resize_columns=False)
        self._sync_valid_upload_controls()

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
            self._reset_excel_results("Chua doc Excel.")
            QMessageBox.warning(self, "Upload Lab", "Chua chon file Excel.")
            return
        if self.fromDateEdit is None or self.toDateEdit is None:
            QMessageBox.critical(self, "Upload Lab", "Khong tim thay truong ngay tren giao dien.")
            return

        from_date = self.fromDateEdit.text().strip()
        to_date = self.toDateEdit.text().strip()
        should_resize_columns = self.contract_book_analysis is None
        try:
            self.contract_book_analysis = analyze_contract_book(path, from_date=from_date, to_date=to_date)
        except Exception as exc:
            self._reset_excel_results("Chua doc Excel.")
            QMessageBox.critical(self, "Upload Lab", str(exc))
            return

        analysis = self.contract_book_analysis
        if (
            self.excelDisplayTable is None
            or self.excelMissingTable is None
            or self.excelIssueTable is None
            or self.excelSummaryLabel is None
        ):
            QMessageBox.critical(self, "Upload Lab", "Khong tim thay widget Excel tren giao dien.")
            return

        set_table_rows(
            self.excelDisplayTable,
            EXCEL_DISPLAY_HEADERS,
            [[row.raw_date, row.contract_no, row.row_index] for row in analysis.display_rows],
            resize_columns=should_resize_columns,
        )
        set_table_rows(
            self.excelMissingTable,
            EXCEL_MISSING_HEADERS,
            [[item.contract_no, item.year, item.ordinal] for item in analysis.missing_numbers],
            resize_columns=should_resize_columns,
        )
        set_table_rows(
            self.excelIssueTable,
            EXCEL_ISSUE_HEADERS,
            [
                [
                    issue.kind.value,
                    issue.row_index,
                    issue.raw_date,
                    issue.raw_contract_no,
                    issue.contract_no,
                    issue.message,
                ]
                for issue in analysis.issue_rows
            ],
            resize_columns=should_resize_columns,
        )
        summary = analysis.summary
        self.excelSummaryLabel.setText(
            f"Excel={summary.excel_total} | hop_le={summary.valid_count} | thieu={summary.missing_count} | loi={summary.issue_count} | trung={summary.duplicate_count}"
        )

    def browse_folder(self) -> None:
        if self.ui is None or self.folderPathEdit is None:
            return

        path = QFileDialog.getExistingDirectory(
            self,
            "Chon folder scan",
            str(self.working_dir),
        )
        if path:
            self.folderPathEdit.setText(path)

    def start_folder_scan(self) -> None:
        if self.ui is None or self.folderPathEdit is None:
            return
        if self.contract_book_analysis is None:
            QMessageBox.warning(self, "Upload Lab", "Hay load Excel truoc khi scan folder.")
            return
        if self.scanThread is not None and self.scanThread.isRunning():
            QMessageBox.information(self, "Upload Lab", "Dang scan folder.")
            return

        folder_path = Path(self.folderPathEdit.text().strip())
        if not folder_path.exists() or not folder_path.is_dir():
            self._reset_folder_results("Folder khong hop le.")
            QMessageBox.warning(self, "Upload Lab", "Chua chon folder hop le.")
            return

        self._reset_folder_results("Dang scan folder...")

        worker = FolderScanWorker(str(folder_path), self.working_dir)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._handle_scan_progress)
        worker.finished.connect(self._handle_scan_finished)
        worker.failed.connect(self._handle_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_scan_worker_refs)
        self.scanWorker = worker
        self.scanThread = thread
        thread.start()

    def _clear_scan_worker_refs(self) -> None:
        self.scanThread = None
        self.scanWorker = None

    def _handle_scan_progress(self, snapshot: dict) -> None:
        if self.scanProgressBar is None or self.scanSummaryLabel is None:
            return

        processed = int(snapshot.get("processed_files") or 0)
        total = int(snapshot.get("total_files") or 0)
        if total > 0:
            self.scanProgressBar.setValue(int((processed / total) * 100))
        else:
            self.scanProgressBar.setValue(0)
        stats = dict(snapshot.get("stats") or {})
        self.scanSummaryLabel.setText(
            f"processed={processed}/{total} | candidates={stats.get('candidates_found', 0)} | partial={stats.get('extract_partial', 0)}"
        )

    def _handle_scan_finished(self, manifest: dict, manifest_path: str) -> None:
        if self.scanProgressBar is not None:
            self.scanProgressBar.setValue(100)
        self.current_manifest_path = Path(manifest_path)

        if self.contract_book_analysis is None:
            self._reset_folder_results("Hay load Excel truoc khi scan folder.")
            QMessageBox.warning(self, "Upload Lab", "Hay load Excel truoc khi scan folder.")
            return

        try:
            _manifest, records, _total_pending = load_upload_queue(self.current_manifest_path, working_dir=self.working_dir)
            classification = classify_scan_records(
                records,
                self.contract_book_analysis,
                existing_web_contract_nos=set(),
            )
        except Exception as exc:
            self._reset_folder_results("Scan that bai.")
            QMessageBox.critical(self, "Upload Lab", str(exc))
            return

        self.render_scan_classification(classification)

    def _handle_scan_failed(self, error_message: str) -> None:
        self._reset_folder_results("Scan that bai.")
        QMessageBox.critical(self, "Upload Lab", error_message)

    def render_scan_classification(self, classification) -> None:
        if (
            self.scanSummaryLabel is None
            or self.validUploadTable is None
            or self.notInExcelTable is None
            or self.missingFieldsTable is None
            or self.webDuplicateTable is None
            or self.localDuplicateTable is None
            or self.excelMissingInFolderTable is None
        ):
            return

        self.validUploadSelection = UploadSelection.from_valid_rows(classification.valid_upload_rows)
        self.validUploadTable.blockSignals(True)
        try:
            set_checkable_upload_rows(self.validUploadTable, classification.valid_upload_rows)
        finally:
            self.validUploadTable.blockSignals(False)
        set_table_rows(
            self.notInExcelTable,
            SCAN_NOT_IN_EXCEL_HEADERS,
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.not_in_excel_rows],
            resize_columns=False,
        )
        set_table_rows(
            self.missingFieldsTable,
            SCAN_MISSING_FIELDS_HEADERS,
            [[row.record_id, row.contract_no, ", ".join(row.missing_fields), row.source_file] for row in classification.missing_field_rows],
            resize_columns=False,
        )
        set_table_rows(
            self.webDuplicateTable,
            SCAN_WEB_DUPLICATE_HEADERS,
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.web_duplicate_rows],
            resize_columns=False,
        )
        set_table_rows(
            self.localDuplicateTable,
            SCAN_LOCAL_DUPLICATE_HEADERS,
            [[row.record_id, row.contract_no, row.reason, row.source_file] for row in classification.duplicate_local_rows],
            resize_columns=False,
        )
        set_table_rows(
            self.excelMissingInFolderTable,
            SCAN_EXCEL_MISSING_HEADERS,
            [[contract_no] for contract_no in classification.excel_missing_in_folder],
            resize_columns=False,
        )
        self.scanSummaryLabel.setText(
            "valid={valid} | not_in_excel={not_in_excel} | missing_fields={missing_fields} | web_dup={web_dup} | local_dup={local_dup} | excel_missing={excel_missing}".format(
                valid=len(classification.valid_upload_rows),
                not_in_excel=len(classification.not_in_excel_rows),
                missing_fields=len(classification.missing_field_rows),
                web_dup=len(classification.web_duplicate_rows),
                local_dup=len(classification.duplicate_local_rows),
                excel_missing=len(classification.excel_missing_in_folder),
            )
        )
        self._sync_valid_upload_controls()

    def _sync_valid_upload_controls(self) -> None:
        selected_count = len(self.validUploadSelection.selected_record_ids())
        has_valid_rows = bool(self.validUploadSelection.valid_ids)
        if self.selectAllValidButton is not None:
            self.selectAllValidButton.setEnabled(has_valid_rows)
        if self.clearValidSelectionButton is not None:
            self.clearValidSelectionButton.setEnabled(has_valid_rows)
        if self.uploadSelectedButton is not None:
            self.uploadSelectedButton.setEnabled(False)
            self.uploadSelectedButton.setText(f"Upload file da chon ({selected_count})")

    def _apply_selection_to_valid_upload_table(self) -> None:
        if self.validUploadTable is None:
            return
        self.validUploadTable.blockSignals(True)
        try:
            selected_ids = set(self.validUploadSelection.selected_record_ids())
            for row_index in range(self.validUploadTable.rowCount()):
                item = self.validUploadTable.item(row_index, 0)
                if item is None:
                    continue
                record_id = item.data(Qt.ItemDataRole.UserRole)
                if record_id is None:
                    continue
                item.setCheckState(Qt.Checked if int(record_id) in selected_ids else Qt.Unchecked)
        finally:
            self.validUploadTable.blockSignals(False)
        self._sync_valid_upload_controls()

    def _handle_valid_upload_item_changed(self, item) -> None:
        if self.validUploadTable is None or item.column() != 0:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id is None:
            return
        self.validUploadSelection.set_selected(record_id, item.checkState() == Qt.Checked)
        self._sync_valid_upload_controls()

    def select_all_valid_upload_rows(self) -> None:
        self.validUploadSelection.select_all_valid()
        self._apply_selection_to_valid_upload_table()

    def clear_valid_upload_selection(self) -> None:
        self.validUploadSelection.clear()
        self._apply_selection_to_valid_upload_table()

    def handle_upload_selected(self) -> None:
        selected_ids = checked_record_ids(self.validUploadTable) if self.validUploadTable is not None else []
        self._log_message(
            "Upload selected requires selected-record upload API. Selected IDs: "
            + (", ".join(str(record_id) for record_id in selected_ids) if selected_ids else "(none)")
        )

    def _log_message(self, message: str) -> None:
        if self.logText is not None:
            self.logText.appendPlainText(message)

    def _open_scan_table_source_file(self, table: QTableWidget, row_index: int) -> None:
        if row_index < 0 or table.columnCount() < 1:
            return

        file_item = table.item(row_index, table.columnCount() - 1)
        if file_item is None:
            return
        path = file_item.text().strip()
        if path:
            open_with_windows_default(path)

    def closeEvent(self, event) -> None:
        if self.scanThread is not None and self.scanThread.isRunning():
            QMessageBox.information(self, "Upload Lab", "Dang scan folder. Hay doi scan xong truoc khi dong app.")
            event.ignore()
            return
        super().closeEvent(event)
