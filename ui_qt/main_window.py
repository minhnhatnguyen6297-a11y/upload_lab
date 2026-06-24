from __future__ import annotations

from dataclasses import replace
import threading
from pathlib import Path
from typing import cast

from PySide6.QtCore import QFile, QThread, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from batch_scan import BASE_DIR
from playwright_uploader import (
    NamDinhUploaderSession,
    default_export_from_date,
    default_export_to_date,
    download_contract_book_export,
    ensure_uploader_env_file,
    get_uploader_setup_status,
    load_upload_queue,
    load_uploader_settings,
    probe_playwright_runtime,
    read_uploader_env,
    save_uploader_env,
)
from ui.services.contract_book_audit import analyze_contract_book
from ui.services.scan_classification_service import FolderScanRow, classify_scan_records
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
EXCEL_MISSING_HEADERS = ["So thieu", "Nam", "STT", "Chu thich"]
EXCEL_ISSUE_HEADERS = ["Loai loi", "Dong", "Ngay", "So goc", "So chuan", "Ly do"]

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
        self.configureUploaderButton: QPushButton | None = None
        self.downloadExcelButton: QPushButton | None = None
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
        self.folderNumbersTable: QTableWidget | None = None
        self.selectAllValidButton: QPushButton | None = None
        self.clearValidSelectionButton: QPushButton | None = None
        self.filterIssueNumbersButton: QPushButton | None = None
        self.selectMissingExcelButton: QPushButton | None = None
        self.uploadSelectedButton: QPushButton | None = None
        self.continueUploadButton: QPushButton | None = None
        self.closeUploadBrowserButton: QPushButton | None = None
        self.logText: QPlainTextEdit | None = None
        self.folderNumberSelection = UploadSelection()
        self.folderScanRows: list[FolderScanRow] = []
        self.missingInExcelRecordIds: set[int] = set()
        self.issueRecordIds: set[int] = set()
        self.issueFilterPreviousSelection: set[int] | None = None
        self.uploadSession: NamDinhUploaderSession | None = None
        self.uploadStopEvent: threading.Event | None = None
        self.activeUploadSelectedRecordIds: set[int] = set()
        self.uploadRemainingCount = 0
        self.playwright_ready = False
        self.playwright_message = ""
        self.uploader_status: dict[str, object] = {}
        self.setWindowTitle("Upload Lab")
        self.resize(1280, 860)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        ensure_uploader_env_file(self.working_dir)
        self.refresh_runtime_status()
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
        self.configureUploaderButton = cast(QPushButton, self.ui.findChild(QPushButton, "configureUploaderButton"))
        self.downloadExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "downloadExcelButton"))
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
                table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                configure_audit_table_scrollbars(table, horizontal=horizontal)

        if self.excelDisplayTable is not None:
            set_table_rows(self.excelDisplayTable, EXCEL_DISPLAY_HEADERS, [], resize_columns=False)
        if self.excelMissingTable is not None:
            set_table_rows(self.excelMissingTable, EXCEL_MISSING_HEADERS, [], resize_columns=False)
        if self.excelIssueTable is not None:
            set_table_rows(self.excelIssueTable, EXCEL_ISSUE_HEADERS, [], resize_columns=False)

        if self.configureUploaderButton is not None:
            self.configureUploaderButton.clicked.connect(self.open_upload_config_dialog)
        if self.downloadExcelButton is not None:
            self.downloadExcelButton.clicked.connect(self.download_excel_from_web)
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
        self.folderNumbersTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "folderNumbersTable"))
        self.selectAllValidButton = cast(QPushButton, self.ui.findChild(QPushButton, "selectAllValidButton"))
        self.clearValidSelectionButton = cast(QPushButton, self.ui.findChild(QPushButton, "clearValidSelectionButton"))
        self.filterIssueNumbersButton = cast(QPushButton, self.ui.findChild(QPushButton, "filterIssueNumbersButton"))
        self.selectMissingExcelButton = cast(QPushButton, self.ui.findChild(QPushButton, "selectMissingExcelButton"))
        self.uploadSelectedButton = cast(QPushButton, self.ui.findChild(QPushButton, "uploadSelectedButton"))
        self.continueUploadButton = cast(QPushButton, self.ui.findChild(QPushButton, "continueUploadButton"))
        self.closeUploadBrowserButton = cast(QPushButton, self.ui.findChild(QPushButton, "closeUploadBrowserButton"))
        self.logText = cast(QPlainTextEdit, self.ui.findChild(QPlainTextEdit, "logText"))

        if self.browseFolderButton is not None:
            self.browseFolderButton.clicked.connect(self.browse_folder)
        if self.scanFolderButton is not None:
            self.scanFolderButton.clicked.connect(self.start_folder_scan)
        if self.selectAllValidButton is not None:
            self.selectAllValidButton.clicked.connect(self.select_all_folder_rows)
        if self.clearValidSelectionButton is not None:
            self.clearValidSelectionButton.clicked.connect(self.clear_folder_selection)
        if self.filterIssueNumbersButton is not None:
            self.filterIssueNumbersButton.clicked.connect(self.filter_issue_numbers)
        if self.selectMissingExcelButton is not None:
            self.selectMissingExcelButton.clicked.connect(self.select_missing_excel_rows)
        if self.uploadSelectedButton is not None:
            self.uploadSelectedButton.clicked.connect(self.handle_upload_selected)
        if self.continueUploadButton is not None:
            self.continueUploadButton.clicked.connect(self.continue_upload_selected)
        if self.closeUploadBrowserButton is not None:
            self.closeUploadBrowserButton.clicked.connect(self.close_upload_browser)

        if self.folderNumbersTable is not None:
            self.folderNumbersTable.cellDoubleClicked.connect(
                lambda row, _column: self._open_scan_table_source_file(self.folderNumbersTable, row)
            )
            self.folderNumbersTable.itemChanged.connect(self._handle_folder_number_item_changed)

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
            or self.folderNumbersTable is None
        ):
            return

        self.current_manifest_path = None
        self.folderNumberSelection = UploadSelection()
        self.folderScanRows = []
        self.missingInExcelRecordIds = set()
        self.issueRecordIds = set()
        self.issueFilterPreviousSelection = None
        self.activeUploadSelectedRecordIds = set()
        self.uploadRemainingCount = 0
        self.scanProgressBar.setValue(0)
        self.scanSummaryLabel.setText(summary_text)
        set_checkable_upload_rows(self.folderNumbersTable, [])
        self._sync_folder_upload_controls()

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

    def refresh_runtime_status(self) -> None:
        self.playwright_ready, self.playwright_message = probe_playwright_runtime()
        self.uploader_status = get_uploader_setup_status(self.working_dir)

    def runtime_summary(self) -> str:
        ready = bool(self.playwright_ready and self.uploader_status.get("ready"))
        status = "ready" if ready else "not_ready"
        message = str(self.uploader_status.get("message") or self.playwright_message or "")
        return f"[SETUP] {status} | {message}"

    def ensure_upload_runtime_ready(self, *, show_dialog: bool = False) -> bool:
        self.refresh_runtime_status()
        ready = bool(self.playwright_ready and self.uploader_status.get("ready"))
        if ready:
            return True
        message = self.runtime_summary()
        self._log_message(message)
        if show_dialog:
            QMessageBox.warning(self, "Upload Lab", message)
        return False

    def open_upload_config_dialog(self) -> None:
        self.refresh_runtime_status()
        values = read_uploader_env(self.working_dir, ensure_exists=True)
        dialog = QDialog(self)
        dialog.setWindowTitle("Cau hinh uploader")
        dialog.setModal(True)

        root_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        root_layout.addLayout(form_layout)

        keys = [
            "ND_BASE_URL",
            "ND_LOGIN_URL",
            "ND_CREATE_URL",
            "ND_USERNAME",
            "ND_PASSWORD",
            "ND_STORAGE_STATE_PATH",
            "ND_BROWSER_CHANNEL",
            "ND_MAX_PREPARED_TABS",
        ]
        field_edits: dict[str, QLineEdit] = {}
        for key in keys:
            edit = QLineEdit(str(values.get(key, "")), dialog)
            if key == "ND_PASSWORD":
                edit.setEchoMode(QLineEdit.EchoMode.Password)
            field_edits[key] = edit
            form_layout.addRow(key, edit)

        status_label = QLabel(self.runtime_summary(), dialog)
        root_layout.addWidget(status_label)

        button_row = QHBoxLayout()
        root_layout.addLayout(button_row)

        def save_only() -> None:
            save_uploader_env({key: edit.text() for key, edit in field_edits.items()}, base_dir=self.working_dir)
            self.refresh_runtime_status()
            status_label.setText(self.runtime_summary())
            self._log_message("[SETUP] Da luu cau hinh uploader.")

        def save_and_login() -> None:
            save_only()
            session = NamDinhUploaderSession(
                load_uploader_settings(self.working_dir),
                working_dir=self.working_dir,
                log_callback=self._log_message,
            )
            try:
                session.ensure_authenticated()
            finally:
                session.close()
            self.refresh_runtime_status()
            status_label.setText(self.runtime_summary())
            self._log_message("[SETUP] Dang nhap xong.")

        save_button = QPushButton("Luu", dialog)
        save_button.clicked.connect(save_only)
        button_row.addWidget(save_button)

        login_button = QPushButton("Luu va dang nhap", dialog)
        login_button.clicked.connect(save_and_login)
        button_row.addWidget(login_button)

        close_button = QPushButton("Dong", dialog)
        close_button.clicked.connect(dialog.accept)
        button_row.addWidget(close_button)

        dialog.resize(760, 320)
        dialog.exec()

    def download_excel_from_web(self) -> None:
        if self.excelPathEdit is None or self.fromDateEdit is None or self.toDateEdit is None:
            return
        if not self.ensure_upload_runtime_ready(show_dialog=True):
            return

        from_date = self.fromDateEdit.text().strip()
        to_date = self.toDateEdit.text().strip()
        export_path = download_contract_book_export(
            from_date=from_date,
            to_date=to_date,
            working_dir=self.working_dir,
            log_callback=self._log_message,
        )
        self.excelPathEdit.setText(str(export_path))
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
            [[item.contract_no, item.year, item.ordinal, item.note] for item in analysis.missing_numbers],
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
        self._refresh_scan_results_from_manifest()

    def _handle_scan_failed(self, error_message: str) -> None:
        self._reset_folder_results("Scan that bai.")
        QMessageBox.critical(self, "Upload Lab", error_message)

    def _refresh_scan_results_from_manifest(self) -> None:
        if self.current_manifest_path is None:
            self._reset_folder_results("Chua co manifest scan.")
            return

        try:
            _manifest, records, _total_pending = load_upload_queue(self.current_manifest_path, working_dir=self.working_dir)
            classification = classify_scan_records(
                records,
                self.contract_book_analysis,
            )
        except Exception as exc:
            self._reset_folder_results("Scan that bai.")
            QMessageBox.critical(self, "Upload Lab", str(exc))
            return

        self.render_scan_classification(classification)

    def render_scan_classification(self, classification) -> None:
        if (
            self.scanSummaryLabel is None
            or self.folderNumbersTable is None
        ):
            return

        self.folderScanRows = list(classification.folder_rows)
        self.folderNumberSelection = UploadSelection.from_rows(classification.folder_rows)
        self.missingInExcelRecordIds = set(classification.missing_in_excel_record_ids)
        self.issueRecordIds = {int(row.record_id) for row in classification.folder_rows if row.has_issue}
        self.issueFilterPreviousSelection = None
        self._render_folder_number_table()
        selected_count = len(self.folderNumberSelection.selected_record_ids())
        missing_count = len(self.missingInExcelRecordIds)
        excel_text = "co Excel" if classification.has_excel else "chua load Excel"
        self.scanSummaryLabel.setText(
            f"folder={len(classification.folder_rows)} | chua_co_excel={missing_count} | da_chon={selected_count} | {excel_text}"
        )
        self._sync_folder_upload_controls()

    def _sync_folder_upload_controls(self) -> None:
        selected_count = len(self.folderNumberSelection.selected_record_ids())
        has_rows = bool(self.folderNumberSelection.row_ids)
        if self.selectAllValidButton is not None:
            self.selectAllValidButton.setEnabled(has_rows)
        if self.clearValidSelectionButton is not None:
            self.clearValidSelectionButton.setEnabled(has_rows)
        if self.filterIssueNumbersButton is not None:
            self.filterIssueNumbersButton.setEnabled(has_rows and bool(self.issueRecordIds))
            self.filterIssueNumbersButton.setText(
                "Hoan tac loc so loi" if self.issueFilterPreviousSelection is not None else "Loc so loi"
            )
        if self.selectMissingExcelButton is not None:
            self.selectMissingExcelButton.setEnabled(has_rows)
        if self.uploadSelectedButton is not None:
            self.uploadSelectedButton.setEnabled(has_rows and selected_count > 0)
            self.uploadSelectedButton.setText(f"Upload file da chon ({selected_count})")
        if self.continueUploadButton is not None:
            self.continueUploadButton.setEnabled(
                self.uploadSession is not None
                and self.uploadRemainingCount > 0
                and bool(self.activeUploadSelectedRecordIds)
                and self.current_manifest_path is not None
            )
        if self.closeUploadBrowserButton is not None:
            self.closeUploadBrowserButton.setEnabled(self.uploadSession is not None)

    def _folder_rows_for_current_selection(self) -> list[FolderScanRow]:
        selected_ids = set(self.folderNumberSelection.selected_record_ids())
        order_by_id = {int(row.record_id): index for index, row in enumerate(self.folderScanRows)}
        rows = [replace(row, selected=int(row.record_id) in selected_ids) for row in self.folderScanRows]
        return sorted(rows, key=lambda row: (not row.selected, order_by_id.get(int(row.record_id), 0)))

    def _render_folder_number_table(self) -> None:
        if self.folderNumbersTable is None:
            return
        self.folderNumbersTable.blockSignals(True)
        try:
            set_checkable_upload_rows(self.folderNumbersTable, self._folder_rows_for_current_selection())
        finally:
            self.folderNumbersTable.blockSignals(False)
        self._sync_folder_upload_controls()

    def _apply_selection_to_folder_table(self) -> None:
        self._render_folder_number_table()

    def _handle_folder_number_item_changed(self, item) -> None:
        if self.folderNumbersTable is None or item.column() != 0:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id is None:
            return
        self.folderNumberSelection.set_selected(record_id, item.checkState() == Qt.Checked)
        self._render_folder_number_table()

    def select_all_folder_rows(self) -> None:
        self.folderNumberSelection.select_all()
        self.issueFilterPreviousSelection = None
        self._apply_selection_to_folder_table()

    def clear_folder_selection(self) -> None:
        self.folderNumberSelection.clear()
        self.issueFilterPreviousSelection = None
        self._apply_selection_to_folder_table()

    def filter_issue_numbers(self) -> None:
        if not self.issueRecordIds:
            QMessageBox.information(self, "Upload Lab", "Chua co so loi de loc.")
            return
        if self.issueFilterPreviousSelection is None:
            self.issueFilterPreviousSelection = set(self.folderNumberSelection.selected_ids)
            self.folderNumberSelection.selected_ids.difference_update(self.issueRecordIds)
        else:
            self.folderNumberSelection.select_only(self.issueFilterPreviousSelection)
            self.issueFilterPreviousSelection = None
        self._apply_selection_to_folder_table()

    def select_missing_excel_rows(self) -> None:
        if not self.missingInExcelRecordIds:
            QMessageBox.information(self, "Upload Lab", "Chua co so thieu trong Excel de chon.")
            return
        self.folderNumberSelection.select_only(self.missingInExcelRecordIds)
        self.issueFilterPreviousSelection = None
        self._apply_selection_to_folder_table()

    def handle_upload_selected(self) -> None:
        selected_ids = set(checked_record_ids(self.folderNumbersTable) if self.folderNumbersTable is not None else [])
        if not selected_ids:
            QMessageBox.warning(self, "Upload Lab", "Chua chon file de upload.")
            return
        if self.current_manifest_path is None or not self.current_manifest_path.exists():
            QMessageBox.warning(self, "Upload Lab", "Chua co manifest scan de upload.")
            return
        if not self.ensure_upload_runtime_ready(show_dialog=True):
            return

        self.activeUploadSelectedRecordIds = set(selected_ids)
        self._prepare_upload_chunk(selected_ids)

    def continue_upload_selected(self) -> None:
        if not self.activeUploadSelectedRecordIds:
            QMessageBox.warning(self, "Upload Lab", "Chua co phien upload de tiep tuc.")
            return
        if self.current_manifest_path is None or not self.current_manifest_path.exists():
            QMessageBox.warning(self, "Upload Lab", "Chua co manifest scan de upload.")
            return
        if not self.ensure_upload_runtime_ready(show_dialog=True):
            return

        self._prepare_upload_chunk(set(self.activeUploadSelectedRecordIds))

    def _ensure_upload_session(self) -> NamDinhUploaderSession:
        if self.uploadSession is None:
            self.uploadSession = NamDinhUploaderSession(
                load_uploader_settings(self.working_dir),
                working_dir=self.working_dir,
                log_callback=self._log_message,
            )
        return self.uploadSession

    def _prepare_upload_chunk(self, selected_ids: set[int]) -> None:
        if self.current_manifest_path is None:
            return

        self.uploadStopEvent = threading.Event()
        session = self._ensure_upload_session()
        try:
            summary = session.prepare_manifest(
                self.current_manifest_path,
                self.uploadStopEvent,
                selected_record_ids=selected_ids,
                exclude_contract_nos=set(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Upload Lab", str(exc))
            self._sync_folder_upload_controls()
            return

        self.activeUploadSelectedRecordIds = set(selected_ids)
        self.uploadRemainingCount = int(summary.get("remaining") or 0)
        self._log_message(
            f"[UPLOAD] prepared={summary.get('prepared_count', 0)} | remaining={self.uploadRemainingCount}"
        )
        self._refresh_scan_results_from_manifest()
        self._sync_folder_upload_controls()

    def close_upload_browser(self) -> None:
        if self.uploadSession is not None:
            self.uploadSession.close()
            self.uploadSession = None
        self.uploadStopEvent = None
        self.uploadRemainingCount = 0
        self._sync_folder_upload_controls()
        self._log_message("[UPLOAD] Da dong browser upload.")

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
        if self.uploadSession is not None:
            self.uploadSession.close()
            self.uploadSession = None
        super().closeEvent(event)
