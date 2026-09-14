from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

from PySide6.QtCore import QFile, QThread, Qt, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
    QSpinBox,
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
    ensure_uploader_env_file,
    get_uploader_setup_status,
    load_upload_queue,
    probe_playwright_runtime,
    read_uploader_env,
    update_uploader_env,
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
from ui_qt.workers import FolderScanWorker, UploadWorker

EXCEL_AUDIT_HEADERS = ["STT", "Ngay", "So cong chung", "Ghi chu"]

class UploadLabMainWindow(QMainWindow):
    # The command carries threading.Event and set instances, which cannot be
    # safely marshalled as a Qt QVariantMap across threads.
    prepareUploadRequested = Signal(object)
    refreshStaffOptionsRequested = Signal()
    reloadStaffOptionsRequested = Signal()
    startLoginRequested = Signal()
    confirmLoginRequested = Signal()
    downloadExcelRequested = Signal(object)
    closeUploadRequested = Signal()

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
        self.notaryComboBox: QComboBox | None = None
        self.secretaryComboBox: QComboBox | None = None
        self.refreshStaffOptionsButton: QPushButton | None = None
        self.uploadChunkSizeSpinBox: QSpinBox | None = None
        self.uploadProgressBar: QProgressBar | None = None
        self.uploadProgressLabel: QLabel | None = None
        self.stopUploadButton: QPushButton | None = None
        self.logText: QPlainTextEdit | None = None
        self.folderNumberSelection = UploadSelection()
        self.folderScanRows: list[FolderScanRow] = []
        self.missingInExcelRecordIds: set[int] = set()
        self.issueRecordIds: set[int] = set()
        self.issueFilterPreviousSelection: set[int] | None = None
        self.uploadThread: QThread | None = None
        self.uploadWorker: UploadWorker | None = None
        self.uploadSessionActive = False
        self.uploadBusy = False
        self.uploadCloseRequested = False
        self.activeUploadSelectedRecordIds: set[int] = set()
        self.uploadRemainingCount = 0
        self.openPreparedRecordIds: set[int] = set()
        self.playwright_ready = False
        self.playwright_message = ""
        self.uploader_status: dict[str, object] = {}
        self.loginStatusLabel: QLabel | None = None
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
        self.excelMissingTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelMissingTable"))
        self.excelIssueTable = cast(QTableWidget, self.ui.findChild(QTableWidget, "excelIssueTable"))

        if self.fromDateEdit is not None and not self.fromDateEdit.text().strip():
            self.fromDateEdit.setText(default_export_from_date())
        if self.toDateEdit is not None and not self.toDateEdit.text().strip():
            self.toDateEdit.setText(default_export_to_date())

        for table, horizontal in (
            (self.excelMissingTable, False),
            (self.excelIssueTable, True),
        ):
            if table is not None:
                table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                configure_audit_table_scrollbars(table, horizontal=horizontal)

        if self.excelMissingTable is not None:
            set_table_rows(self.excelMissingTable, EXCEL_AUDIT_HEADERS, [], resize_columns=False)
        if self.excelIssueTable is not None:
            set_table_rows(self.excelIssueTable, EXCEL_AUDIT_HEADERS, [], resize_columns=False)

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
        self.notaryComboBox = cast(QComboBox, self.ui.findChild(QComboBox, "notaryComboBox"))
        self.secretaryComboBox = cast(QComboBox, self.ui.findChild(QComboBox, "secretaryComboBox"))
        self.refreshStaffOptionsButton = cast(
            QPushButton, self.ui.findChild(QPushButton, "refreshStaffOptionsButton")
        )
        self.uploadChunkSizeSpinBox = cast(
            QSpinBox, self.ui.findChild(QSpinBox, "uploadChunkSizeSpinBox")
        )
        self.uploadProgressBar = cast(QProgressBar, self.ui.findChild(QProgressBar, "uploadProgressBar"))
        self.uploadProgressLabel = cast(QLabel, self.ui.findChild(QLabel, "uploadProgressLabel"))
        self.stopUploadButton = cast(QPushButton, self.ui.findChild(QPushButton, "stopUploadButton"))
        self.logText = cast(QPlainTextEdit, self.ui.findChild(QPlainTextEdit, "logText"))

        self._apply_staff_options(NamDinhUploaderSession.load_staff_options_cache(self.working_dir))
        if self.uploadChunkSizeSpinBox is not None:
            values = read_uploader_env(self.working_dir)
            try:
                chunk_size = int(str(values.get("ND_MAX_PREPARED_TABS") or "10"))
            except ValueError:
                chunk_size = 10
            self.uploadChunkSizeSpinBox.setValue(max(1, min(chunk_size, 30)))

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
        if self.refreshStaffOptionsButton is not None:
            self.refreshStaffOptionsButton.clicked.connect(self.refresh_staff_options)
        if self.uploadChunkSizeSpinBox is not None:
            self.uploadChunkSizeSpinBox.valueChanged.connect(self._save_upload_chunk_size)
        if self.stopUploadButton is not None:
            self.stopUploadButton.clicked.connect(self.stop_upload)

        if self.folderNumbersTable is not None:
            self.folderNumbersTable.cellDoubleClicked.connect(
                lambda row, _column: self._open_scan_table_source_file(self.folderNumbersTable, row)
            )
            self.folderNumbersTable.itemChanged.connect(self._handle_folder_number_item_changed)

    def _reset_excel_results(self, summary_text: str) -> None:
        self.contract_book_analysis = None
        if (
            self.excelMissingTable is None
            or self.excelIssueTable is None
            or self.excelSummaryLabel is None
        ):
            return

        set_table_rows(self.excelMissingTable, EXCEL_AUDIT_HEADERS, [], resize_columns=False)
        set_table_rows(self.excelIssueTable, EXCEL_AUDIT_HEADERS, [], resize_columns=False)
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
        message = str(
            self.uploader_status.get("message")
            if self.playwright_ready
            else self.playwright_message
        )
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
        dialog.setWindowTitle("Ket noi web cong chung")
        dialog.setModal(True)

        root_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        root_layout.addLayout(form_layout)

        base_url_edit = QLineEdit(str(values.get("ND_BASE_URL", "")), dialog)
        base_url_edit.setPlaceholderText("https://congchungnamdinh.ninhbinh.gov.vn")
        form_layout.addRow("Dia chi web", base_url_edit)

        status_label = QLabel(self.runtime_summary(), dialog)
        status_label.setWordWrap(True)
        self.loginStatusLabel = status_label
        root_layout.addWidget(status_label)

        button_row = QHBoxLayout()
        root_layout.addLayout(button_row)

        def save_only() -> bool:
            base_url = base_url_edit.text().strip().rstrip("/")
            if not base_url.startswith(("http://", "https://")):
                QMessageBox.warning(dialog, "Upload Lab", "Dia chi web phai bat dau bang http:// hoac https://.")
                return False
            update_uploader_env(
                {
                    "ND_BASE_URL": base_url,
                    # Empty values mean the stable routes are derived from the base URL.
                    "ND_LOGIN_URL": "",
                    "ND_CREATE_URL": "",
                },
                base_dir=self.working_dir,
            )
            self.refresh_runtime_status()
            status_label.setText(self.runtime_summary())
            self._log_message("[SETUP] Da luu dia chi web. App khong luu tai khoan hoac mat khau.")
            return True

        def open_login_browser() -> None:
            if not save_only():
                return
            self.uploadBusy = True
            self._ensure_upload_worker()
            self._sync_folder_upload_controls()
            status_label.setText("Dang mo Chromium de ban dang nhap...")
            self.startLoginRequested.emit()

        def confirm_login() -> None:
            self._ensure_upload_worker()
            status_label.setText("Dang kiem tra token dang nhap...")
            self.confirmLoginRequested.emit()

        save_button = QPushButton("Luu dia chi", dialog)
        save_button.clicked.connect(save_only)
        button_row.addWidget(save_button)

        login_button = QPushButton("Mo trinh duyet dang nhap", dialog)
        login_button.clicked.connect(open_login_browser)
        button_row.addWidget(login_button)

        confirm_button = QPushButton("Toi da dang nhap", dialog)
        confirm_button.clicked.connect(confirm_login)
        button_row.addWidget(confirm_button)

        close_button = QPushButton("Dong", dialog)
        close_button.clicked.connect(dialog.accept)
        button_row.addWidget(close_button)

        dialog.resize(680, 210)
        dialog.exec()
        self.loginStatusLabel = None

    def download_excel_from_web(self) -> None:
        if self.excelPathEdit is None or self.fromDateEdit is None or self.toDateEdit is None:
            return
        if not self.ensure_upload_runtime_ready(show_dialog=True):
            return

        from_date = self.fromDateEdit.text().strip()
        to_date = self.toDateEdit.text().strip()
        self.uploadBusy = True
        self._ensure_upload_worker()
        self._sync_folder_upload_controls()
        self.downloadExcelButton.setEnabled(False) if self.downloadExcelButton is not None else None
        self._log_message("[UPLOAD][EXPORT] Dang tai Excel tren worker nen giao dien van dung duoc.")
        self.downloadExcelRequested.emit({"from_date": from_date, "to_date": to_date})

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
            self.excelMissingTable is None
            or self.excelIssueTable is None
            or self.excelSummaryLabel is None
        ):
            QMessageBox.critical(self, "Upload Lab", "Khong tim thay widget Excel tren giao dien.")
            return

        set_table_rows(
            self.excelMissingTable,
            EXCEL_AUDIT_HEADERS,
            [
                [index, "", item.contract_no, item.note]
                for index, item in enumerate(analysis.missing_numbers, start=1)
            ],
            resize_columns=should_resize_columns,
        )
        set_table_rows(
            self.excelIssueTable,
            EXCEL_AUDIT_HEADERS,
            [
                [
                    index,
                    issue.raw_date or (issue.contract_date.strftime("%d/%m/%Y") if issue.contract_date else ""),
                    issue.contract_no or issue.raw_contract_no,
                    f"dong {issue.row_index} | {issue.kind.value}: {issue.message}",
                ]
                for index, issue in enumerate(analysis.issue_rows, start=1)
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

    def _refresh_scan_results_from_manifest(
        self,
        *,
        preserve_selection: bool = False,
        removed_record_ids: set[int] | None = None,
    ) -> None:
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

        self.render_scan_classification(
            classification,
            preserve_selection=preserve_selection,
            removed_record_ids=removed_record_ids,
        )

    def render_scan_classification(
        self,
        classification,
        *,
        preserve_selection: bool = False,
        removed_record_ids: set[int] | None = None,
    ) -> None:
        if (
            self.scanSummaryLabel is None
            or self.folderNumbersTable is None
        ):
            return

        previous_selection = self.folderNumberSelection
        refreshed_selection = UploadSelection.from_rows(classification.folder_rows)
        if preserve_selection:
            retained_ids = previous_selection.row_ids & refreshed_selection.row_ids
            newly_seen_ids = refreshed_selection.row_ids - previous_selection.row_ids
            refreshed_selection.selected_ids = (
                (previous_selection.selected_ids & retained_ids)
                | (refreshed_selection.selected_ids & newly_seen_ids)
            )
        refreshed_selection.selected_ids.difference_update(removed_record_ids or set())
        self.folderScanRows = list(classification.folder_rows)
        self.folderNumberSelection = refreshed_selection
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
        chunk_size = self.uploadChunkSizeSpinBox.value() if self.uploadChunkSizeSpinBox is not None else 10
        if self.selectAllValidButton is not None:
            self.selectAllValidButton.setEnabled(not self.uploadBusy and has_rows)
        if self.clearValidSelectionButton is not None:
            self.clearValidSelectionButton.setEnabled(not self.uploadBusy and has_rows)
        if self.filterIssueNumbersButton is not None:
            self.filterIssueNumbersButton.setEnabled(not self.uploadBusy and has_rows and bool(self.issueRecordIds))
            self.filterIssueNumbersButton.setText(
                "Hoan tac loc so loi" if self.issueFilterPreviousSelection is not None else "Loc so loi"
            )
        if self.selectMissingExcelButton is not None:
            self.selectMissingExcelButton.setEnabled(not self.uploadBusy and has_rows)
        if self.uploadSelectedButton is not None:
            self.uploadSelectedButton.setEnabled(not self.uploadBusy and has_rows and selected_count > 0)
            self.uploadSelectedButton.setText(f"Upload file da chon ({selected_count})")
        if self.continueUploadButton is not None:
            next_count = min(chunk_size, self.uploadRemainingCount) if self.uploadRemainingCount > 0 else chunk_size
            self.continueUploadButton.setText(f"Tiep tuc {next_count} so tiep theo")
            self.continueUploadButton.setEnabled(
                not self.uploadBusy
                and self.uploadSessionActive
                and self.uploadRemainingCount > 0
                and bool(self.activeUploadSelectedRecordIds)
                and self.current_manifest_path is not None
            )
        if self.closeUploadBrowserButton is not None:
            self.closeUploadBrowserButton.setEnabled(not self.uploadBusy and self.uploadSessionActive)
        if self.refreshStaffOptionsButton is not None:
            self.refreshStaffOptionsButton.setEnabled(not self.uploadBusy)
        if self.uploadChunkSizeSpinBox is not None:
            self.uploadChunkSizeSpinBox.setEnabled(not self.uploadBusy)
        if self.notaryComboBox is not None:
            self.notaryComboBox.setEnabled(not self.uploadBusy)
        if self.secretaryComboBox is not None:
            self.secretaryComboBox.setEnabled(not self.uploadBusy)
        if self.stopUploadButton is not None:
            self.stopUploadButton.setEnabled(self.uploadBusy)

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

        checked_ids = set(
            checked_record_ids(self.folderNumbersTable)
            if self.folderNumbersTable is not None
            else []
        )
        selected_ids = checked_ids & self.activeUploadSelectedRecordIds
        if not selected_ids:
            QMessageBox.information(self, "Upload Lab", "Khong con ho so nao dang duoc tick de tiep tuc.")
            return
        self._prepare_upload_chunk(selected_ids)

    def _ensure_upload_worker(self) -> UploadWorker:
        if self.uploadWorker is not None:
            return self.uploadWorker
        worker = UploadWorker(self.working_dir)
        thread = QThread(self)
        worker.moveToThread(thread)
        self.prepareUploadRequested.connect(worker.prepare)
        self.refreshStaffOptionsRequested.connect(worker.refresh_options)
        self.reloadStaffOptionsRequested.connect(worker.reload_options)
        self.startLoginRequested.connect(worker.start_login)
        self.confirmLoginRequested.connect(worker.confirm_login)
        self.downloadExcelRequested.connect(worker.download_export)
        self.closeUploadRequested.connect(worker.close_session)
        worker.prepared.connect(self._handle_upload_prepared)
        worker.optionsRefreshed.connect(self._handle_staff_options_refreshed)
        worker.loginStateChanged.connect(self._handle_login_state_changed)
        worker.exportDownloaded.connect(self._handle_export_downloaded)
        worker.preparedPagesChanged.connect(self._handle_prepared_pages_changed)
        worker.failed.connect(self._handle_upload_failed)
        worker.progress.connect(self._handle_upload_progress)
        worker.log.connect(self._log_message)
        worker.closed.connect(self._handle_upload_closed)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._handle_upload_thread_finished)
        self.uploadWorker = worker
        self.uploadThread = thread
        thread.start()
        return worker

    def _prepare_upload_chunk(self, selected_ids: set[int]) -> None:
        if self.current_manifest_path is None:
            return

        self.activeUploadSelectedRecordIds = set(selected_ids)
        self.uploadBusy = True
        self.uploadProgressBar.setValue(0) if self.uploadProgressBar is not None else None
        if self.uploadProgressLabel is not None:
            self.uploadProgressLabel.setText("Dang khoi tao upload...")
        self._ensure_upload_worker()
        self._sync_folder_upload_controls()
        self.prepareUploadRequested.emit(
            {
                "manifest_path": str(self.current_manifest_path),
                "selected_record_ids": sorted(selected_ids),
                "exclude_contract_nos": [],
                "cong_chung_vien": self._selected_staff_value(self.notaryComboBox),
                "thu_ky": self._selected_staff_value(self.secretaryComboBox),
                "chunk_size": self.uploadChunkSizeSpinBox.value() if self.uploadChunkSizeSpinBox is not None else 10,
            }
        )

    def _handle_upload_prepared(self, summary: dict) -> None:
        self.uploadBusy = False
        self.uploadSessionActive = True
        self.uploadRemainingCount = int(summary.get("remaining") or 0)
        self.openPreparedRecordIds = {
            int(record_id) for record_id in summary.get("open_record_ids", [])
        }
        self._log_message(
            f"[UPLOAD] prepared={summary.get('prepared_count', 0)} | remaining={self.uploadRemainingCount}"
        )
        self._refresh_scan_results_from_manifest()
        self._sync_folder_upload_controls()

    def _handle_upload_progress(self, snapshot: dict) -> None:
        prepared = int(snapshot.get("prepared_count") or 0)
        total = int(snapshot.get("total_pending") or snapshot.get("filtered_pending") or 0)
        if self.uploadProgressBar is not None:
            self.uploadProgressBar.setValue(int(prepared * 100 / total) if total else 0)
        if self.uploadProgressLabel is not None:
            contract_no = str(snapshot.get("contract_no") or "")
            self.uploadProgressLabel.setText(
                f"{snapshot.get('event', 'upload')}: {prepared}/{total}" + (f" | {contract_no}" if contract_no else "")
            )

    def _handle_upload_failed(self, operation: str, error_message: str) -> None:
        self.uploadBusy = False
        self.uploadSessionActive = self.uploadWorker is not None
        if self.downloadExcelButton is not None:
            self.downloadExcelButton.setEnabled(True)
        if operation == "login" and self.loginStatusLabel is not None:
            self.loginStatusLabel.setText(f"Dang nhap that bai: {error_message}")
        self._sync_folder_upload_controls()
        QMessageBox.critical(self, "Upload Lab", error_message)

    def stop_upload(self) -> None:
        if self.uploadWorker is not None:
            self.uploadWorker.request_stop()
            if self.uploadProgressLabel is not None:
                self.uploadProgressLabel.setText("Dang dung sau ho so hien tai...")

    @staticmethod
    def _selected_staff_value(combo: QComboBox | None) -> str | None:
        value = combo.currentText().strip() if combo is not None else ""
        return value or None

    def _apply_staff_options(self, options: dict) -> None:
        for combo, key in (
            (self.notaryComboBox, "cong_chung_vien"),
            (self.secretaryComboBox, "thu_ky"),
        ):
            if combo is None:
                continue
            labels = [str(label).strip() for label in options.get(key, []) if str(label).strip()]
            combo.clear()
            combo.addItem("")
            combo.addItems(labels)

    def refresh_staff_options(self) -> None:
        if not self.ensure_upload_runtime_ready(show_dialog=True):
            return
        self.uploadBusy = True
        self._ensure_upload_worker()
        self._sync_folder_upload_controls()
        self.refreshStaffOptionsRequested.emit()

    def _handle_staff_options_refreshed(self, options: dict) -> None:
        self.uploadBusy = False
        self.uploadSessionActive = True
        self._apply_staff_options(options)
        self._sync_folder_upload_controls()

    def _handle_login_state_changed(self, result: dict) -> None:
        status = str(result.get("status") or "")
        message = str(result.get("message") or "")
        if status == "waiting":
            self.uploadBusy = True
        elif status in {"authenticated", "closed", "timeout"}:
            self.uploadBusy = False
        if status == "authenticated":
            self.uploadSessionActive = True
            self.refresh_runtime_status()
            message = "Da dang nhap. Session da duoc luu; app khong luu mat khau."
        if self.loginStatusLabel is not None:
            try:
                self.loginStatusLabel.setText(message or self.runtime_summary())
            except RuntimeError:
                self.loginStatusLabel = None
        self._log_message(f"[LOGIN] {status}: {message}")
        self._sync_folder_upload_controls()

    def _handle_export_downloaded(self, export_path: str) -> None:
        self.uploadBusy = False
        self.uploadSessionActive = True
        if self.downloadExcelButton is not None:
            self.downloadExcelButton.setEnabled(True)
        if self.excelPathEdit is not None:
            self.excelPathEdit.setText(str(export_path))
        self._sync_folder_upload_controls()
        self.load_excel()

    def _handle_prepared_pages_changed(self, result: dict) -> None:
        saved_ids = {int(record_id) for record_id in result.get("saved_record_ids", [])}
        closed_ids = {int(record_id) for record_id in result.get("closed_record_ids", [])}
        self.openPreparedRecordIds = {
            int(record_id) for record_id in result.get("open_record_ids", [])
        }
        if saved_ids:
            self.activeUploadSelectedRecordIds.difference_update(saved_ids)
            self._log_message(f"[UPLOAD] Da Luu {len(saved_ids)} ho so; cac dong nay da roi khoi bang.")
            self._refresh_scan_results_from_manifest(
                preserve_selection=True,
                removed_record_ids=saved_ids,
            )
        if closed_ids:
            self._log_message(
                f"[UPLOAD] Co {len(closed_ids)} tab da dong chua ro da Luu; co the bam Tiep tuc de mo lai."
            )
        self._sync_folder_upload_controls()

    def _save_upload_chunk_size(self, value: int) -> None:
        update_uploader_env({"ND_MAX_PREPARED_TABS": str(int(value))}, base_dir=self.working_dir)
        self._sync_folder_upload_controls()

    def _handle_upload_thread_finished(self) -> None:
        self.uploadThread = None
        self.uploadWorker = None
        if self.uploadCloseRequested:
            self.close()

    def _handle_upload_closed(self) -> None:
        self.uploadSessionActive = False
        self.uploadBusy = False
        self.uploadRemainingCount = 0
        self.openPreparedRecordIds.clear()
        thread = self.uploadThread
        if thread is not None:
            thread.quit()
        self._sync_folder_upload_controls()
        self._log_message("[UPLOAD] Da dong browser upload.")

    def close_upload_browser(self) -> None:
        if self.uploadWorker is None:
            return
        self.uploadWorker.request_stop()
        self.uploadBusy = True
        self.closeUploadRequested.emit()
        self._sync_folder_upload_controls()

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
        if self.uploadWorker is not None or (self.uploadThread is not None and self.uploadThread.isRunning()):
            self.uploadCloseRequested = True
            if self.uploadWorker is not None:
                self.uploadWorker.request_stop()
                self.closeUploadRequested.emit()
            event.ignore()
            return
        super().closeEvent(event)
