"""Main PyQt6 application window."""

from __future__ import annotations

import json
import os
import threading
from collections import Counter
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.styles.stylesheets import MAIN_STYLESHEET
from ui.tabs import BatchScanTab, UploadTab
from ui.threads import BatchScanWorker, UploadWorker
from ui.widgets import LogViewerWidget

try:
    from batch_scan import MAX_SCAN_DEPTH
    from playwright_uploader import (
        DEFAULT_REQUESTER_SHEET_URL,
        NamDinhUploaderSession,
        default_export_from_date,
        default_export_to_date,
        download_contract_book_export,
        ensure_uploader_env_file,
        finalize_uploaded_records,
        get_uploader_setup_status,
        load_requester_contract_lookup,
        load_upload_queue,
        load_uploader_settings,
        probe_playwright_runtime,
        read_exported_contract_numbers,
        sanitize_contract_no,
        save_uploader_env,
        split_records_by_existing_contract_nos,
    )
except ImportError:  # pragma: no cover
    from ..batch_scan import MAX_SCAN_DEPTH
    from ..playwright_uploader import (
        DEFAULT_REQUESTER_SHEET_URL,
        NamDinhUploaderSession,
        default_export_from_date,
        default_export_to_date,
        download_contract_book_export,
        ensure_uploader_env_file,
        finalize_uploaded_records,
        get_uploader_setup_status,
        load_requester_contract_lookup,
        load_upload_queue,
        load_uploader_settings,
        probe_playwright_runtime,
        read_exported_contract_numbers,
        sanitize_contract_no,
        save_uploader_env,
        split_records_by_existing_contract_nos,
    )


SETTINGS_ORG = "UploadLab"
SETTINGS_APP = "PyQt6UI"
UPLOAD_STATUS_LABELS = {
    "extracted": "Chờ upload",
    "upload_failed": "Lỗi upload",
    "prepared_dry_run": "Chờ rà soát",
    "prepared_partial": "Thiếu trường",
    "uploaded_success": "Đã xác nhận",
}
QUEUE_ALLOWED_FINALIZE = {"prepared_dry_run", "prepared_partial"}


class UploaderConfigDialog(QDialog):
    """Simple modal dialog for uploader credentials and runtime options."""

    FIELD_DEFS = [
        ("ND_BASE_URL", "Base URL", False),
        ("ND_LOGIN_URL", "Login URL", False),
        ("ND_CREATE_URL", "Create URL", False),
        ("ND_USERNAME", "Tài khoản", False),
        ("ND_PASSWORD", "Mật khẩu", True),
        ("ND_MAX_PREPARED_TABS", "Số tab tối đa", False),
        ("ND_POST_PREPARE_DELAY_MS", "Delay sau mỗi tab (ms)", False),
    ]

    def __init__(self, values: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Cấu hình web")
        self.setMinimumWidth(560)
        self.inputs: dict[str, QLineEdit] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel(
            "Nhập thông tin đăng nhập và cấu hình uploader. Sau khi lưu, tool sẽ tự đăng nhập để tạo nd_storage_state.json."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        layout.addLayout(form)

        for key, label, is_secret in self.FIELD_DEFS:
            field = QLineEdit(str(values.get(key, "")))
            if is_secret:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            self.inputs[key] = field
            form.addRow(label, field)

        self.status_label = QLabel(
            "Nếu đã có nd_storage_state.json hợp lệ, bạn vẫn có thể lưu lại để cập nhật cấu hình."
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_btn)
        self.save_btn = QPushButton("Lưu và đăng nhập")
        button_row.addWidget(self.save_btn)
        layout.addLayout(button_row)

    def values(self) -> dict[str, str]:
        return {key: field.text().strip() for key, field in self.inputs.items()}

    def set_status(self, message: str, *, error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setProperty("state", "error" if error else "warning")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_busy(self, busy: bool) -> None:
        self.save_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)


class MainWindow(QMainWindow):
    """Main application window with batch scan and upload tabs."""

    async_log = pyqtSignal(str)
    upload_config_saved_signal = pyqtSignal()
    upload_config_error_signal = pyqtSignal(str)
    export_downloaded_signal = pyqtSignal(str)
    export_download_error_signal = pyqtSignal(str)

    def __init__(self, parent=None, working_dir: Path | None = None) -> None:
        super().__init__(parent)
        self.working_dir = Path(working_dir or Path.cwd())
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._restoring_settings = False
        self._upload_running = False
        self._upload_stop_requested = False
        self._last_upload_summary: dict[str, Any] | None = None
        self._live_upload_summary: dict[str, Any] = {}
        self._current_manifest: dict[str, Any] | None = None
        self._current_total_pending = 0
        self._queue_rows_by_id: dict[int, dict[str, Any]] = {}
        self._duplicate_rows_by_id: dict[int, dict[str, Any]] = {}
        self._existing_web_contract_nos: set[str] = set()
        self._web_compare_loaded = False
        self._uploader_setup_status: dict[str, Any] = {}
        self.playwright_ready = False
        self.playwright_message = ""
        self._config_dialog: UploaderConfigDialog | None = None

        ensure_uploader_env_file(self.working_dir)
        self.setWindowTitle("Batch Scan & Upload Tool - Nam Định")
        self.setMinimumSize(980, 660)
        self.resize(1080, 760)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._create_ui()
        self.batch_worker = BatchScanWorker(self)
        self.upload_worker = UploadWorker(self)
        self._connect_signals()
        self._restore_settings()
        self._refresh_upload_runtime_state()
        if self.upload_tab.get_manifest_path():
            self._on_upload_refresh_queue()
        else:
            self._sync_upload_summary()

    def _create_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.batch_tab = BatchScanTab()
        self.upload_tab = UploadTab()
        self.tabs.addTab(self.batch_tab, "Quét hồ sơ")
        self.tabs.addTab(self.upload_tab, "Upload hồ sơ")
        layout.addWidget(self.tabs, 1)

        self.log_viewer = LogViewerWidget()
        self.log_viewer.setMaximumHeight(190)
        layout.addWidget(self.log_viewer)

        self.statusBar().showMessage("Sẵn sàng")

    def _connect_signals(self) -> None:
        self.batch_tab.run_batch_scan.connect(self._on_batch_run_clicked)
        self.batch_worker.progress_updated.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_finished)
        self.batch_worker.error.connect(self._on_batch_error)
        self.batch_worker.log.connect(self.log_viewer.append_log)

        self.upload_tab.configure_uploader.connect(self._open_upload_config_dialog)
        self.upload_tab.refresh_queue.connect(self._on_upload_refresh_queue)
        self.upload_tab.start_upload.connect(self._on_upload_start)
        self.upload_tab.stop_upload.connect(self._on_upload_stop)
        self.upload_tab.finalize_records.connect(self._on_upload_finalize)
        self.upload_tab.download_web_export.connect(self._on_download_web_export)
        self.upload_tab.manifest_path_changed.connect(self._on_manifest_path_changed)
        self.upload_tab.requester_sheet_url_changed.connect(self._on_requester_sheet_url_changed)
        self.upload_tab.export_path_changed.connect(self._on_export_path_changed)
        self.upload_tab.open_source_requested.connect(self._open_source_for_record)
        self.upload_tab.open_path_requested.connect(self._open_path)

        self.upload_worker.progress.connect(self._on_upload_progress)
        self.upload_worker.finished.connect(self._on_upload_finished)
        self.upload_worker.error.connect(self._on_upload_error)
        self.upload_worker.log.connect(self.log_viewer.append_log)

        self.async_log.connect(self.log_viewer.append_log)
        self.upload_config_saved_signal.connect(self._on_upload_config_saved)
        self.upload_config_error_signal.connect(self._on_upload_config_error)
        self.export_downloaded_signal.connect(self._on_export_downloaded)
        self.export_download_error_signal.connect(self._on_export_download_error)

    def _restore_settings(self) -> None:
        self._restoring_settings = True
        try:
            geometry = self.settings.value("main/geometry")
            if geometry:
                self.restoreGeometry(geometry)

            current_tab = int(self.settings.value("main/current_tab", 0))
            self.tabs.setCurrentIndex(max(0, min(current_tab, self.tabs.count() - 1)))

            batch_folder = str(self.settings.value("batch/folder", "") or "")
            if batch_folder:
                self.batch_tab.folder_browser.set_folder_path(batch_folder)
            self.batch_tab.modified_since_input.setText(str(self.settings.value("batch/modified_since", "") or ""))
            self.batch_tab.full_rescan_check.setChecked(bool(self.settings.value("batch/full_rescan", False, type=bool)))
            self.batch_tab.max_depth_spin.setValue(
                int(self.settings.value("batch/max_depth", MAX_SCAN_DEPTH, type=int))
            )

            manifest_path = str(self.settings.value("upload/manifest_path", "") or "")
            if manifest_path:
                self.upload_tab.set_manifest_path(manifest_path)
            requester_sheet_url = str(
                self.settings.value("upload/requester_sheet_url", DEFAULT_REQUESTER_SHEET_URL) or ""
            )
            self.upload_tab.set_requester_sheet_url(requester_sheet_url or DEFAULT_REQUESTER_SHEET_URL)
            export_path = str(self.settings.value("upload/export_path", "") or "")
            if export_path:
                self.upload_tab.set_export_path(export_path)
            from_date = str(self.settings.value("upload/from_date", default_export_from_date()) or "")
            to_date = str(self.settings.value("upload/to_date", default_export_to_date()) or "")
            self.upload_tab.set_date_range(from_date, to_date)

            splitter_value = self.settings.value("upload/splitter_sizes")
            if isinstance(splitter_value, list):
                self.upload_tab.set_splitter_sizes([int(size) for size in splitter_value if str(size).strip()])
            elif isinstance(splitter_value, str) and splitter_value.strip():
                self.upload_tab.set_splitter_sizes(
                    [int(part) for part in splitter_value.split(",") if part.strip()]
                )
            self.log_viewer.set_collapsed(bool(self.settings.value("main/log_collapsed", True, type=bool)))
        finally:
            self._restoring_settings = False

        if self.upload_tab.get_manifest_path():
            self.upload_tab.set_ui_state("manifest_selected_unloaded")
            self.upload_tab.set_compare_status("", False)
        else:
            self.upload_tab.set_ui_state("no_manifest")
            self.upload_tab.set_compare_status("", False)

    def _save_settings(self) -> None:
        self.settings.setValue("main/geometry", self.saveGeometry())
        self.settings.setValue("main/current_tab", self.tabs.currentIndex())
        self.settings.setValue("batch/folder", self.batch_tab.folder_browser.get_folder_path())
        self.settings.setValue("batch/modified_since", self.batch_tab.modified_since_input.text().strip())
        self.settings.setValue("batch/full_rescan", self.batch_tab.full_rescan_check.isChecked())
        self.settings.setValue("batch/max_depth", self.batch_tab.max_depth_spin.value())
        self.settings.setValue("upload/manifest_path", self.upload_tab.get_manifest_path())
        self.settings.setValue("upload/requester_sheet_url", self.upload_tab.get_requester_sheet_url())
        self.settings.setValue("upload/export_path", self.upload_tab.get_export_path())
        self.settings.setValue("upload/from_date", self.upload_tab.from_date_input.text().strip())
        self.settings.setValue("upload/to_date", self.upload_tab.to_date_input.text().strip())
        self.settings.setValue("upload/splitter_sizes", self.upload_tab.get_splitter_sizes())
        self.settings.setValue("main/log_collapsed", self.log_viewer.is_collapsed())

    def _notify_upload(self, message: str, *, level: str = "info", status_message: str | None = None) -> None:
        self.upload_tab.show_notice(message, level=level)
        if status_message:
            self.statusBar().showMessage(status_message)

    def _clear_upload_notice(self) -> None:
        self.upload_tab.clear_notice()

    def _notify_batch(self, message: str, *, level: str = "info", status_message: str | None = None) -> None:
        self.batch_tab.show_notice(message, level=level)
        if status_message:
            self.statusBar().showMessage(status_message)

    def _clear_batch_notice(self) -> None:
        self.batch_tab.clear_notice()

    def _apply_manifest_to_upload(self, manifest_path: str) -> None:
        manifest_value = str(manifest_path or "").strip()
        if not manifest_value:
            return

        resolved_manifest = str(Path(manifest_value))
        self.async_log.emit(f"[BATCH->UPLOAD] Gắn manifest mới sang tab upload: {resolved_manifest}")
        self.tabs.setCurrentWidget(self.upload_tab)
        self.upload_tab.set_manifest_path(resolved_manifest)
        if not self.upload_tab.get_export_path().strip():
            self._notify_upload(
                f"Manifest mới đã được gắn sẵn: {Path(resolved_manifest).name}. Chọn file đối chiếu hoặc tải danh sách web để lọc trùng.",
                level="success",
                status_message="Đã cập nhật manifest cho tab upload",
            )

    def _refresh_upload_runtime_state(self) -> bool:
        self.playwright_ready, self.playwright_message = probe_playwright_runtime()
        self._uploader_setup_status = get_uploader_setup_status(self.working_dir)
        upload_ready = bool(self.playwright_ready and self._uploader_setup_status.get("ready"))
        if not self.playwright_ready:
            capability_text = "Chưa sẵn sàng mở trình duyệt upload. Mở log để xem chi tiết môi trường chạy."
        elif upload_ready:
            capability_text = "Kết nối web đã sẵn sàng. Có thể tải danh sách và upload."
        elif self._uploader_setup_status.get("missing_fields"):
            capability_text = "Chưa có đủ thông tin đăng nhập web. Bấm 'Cấu hình web' để bổ sung."
        else:
            capability_text = "Cần đăng nhập web lần đầu. Bấm 'Cấu hình web' để tạo phiên làm việc."
        self.upload_tab.set_runtime_status(capability_text, upload_ready)
        return upload_ready

    def _ensure_upload_runtime_ready(self, *, show_dialog: bool = True) -> bool:
        if self._refresh_upload_runtime_state():
            return True
        if show_dialog and self.playwright_ready:
            self._open_upload_config_dialog()
        return False

    def _open_upload_config_dialog(self) -> None:
        if self._config_dialog is not None and self._config_dialog.isVisible():
            self._config_dialog.raise_()
            self._config_dialog.activateWindow()
            return

        values = dict(self._uploader_setup_status.get("values") or {})
        dialog = UploaderConfigDialog(values, self)
        dialog.save_btn.clicked.connect(self._submit_upload_config_dialog)
        self._config_dialog = dialog
        dialog.open()

    def _submit_upload_config_dialog(self) -> None:
        dialog = self._config_dialog
        if dialog is None:
            return

        values = dialog.values()
        base_url = values.get("ND_BASE_URL", "").rstrip("/")
        if base_url and not values.get("ND_LOGIN_URL"):
            values["ND_LOGIN_URL"] = base_url
        if base_url and not values.get("ND_CREATE_URL"):
            values["ND_CREATE_URL"] = f"{base_url}/ho-so-cong-chung/tao-moi-nhanh"

        missing = [
            label
            for key, label in (
                ("ND_BASE_URL", "Base URL"),
                ("ND_LOGIN_URL", "Login URL"),
                ("ND_CREATE_URL", "Create URL"),
                ("ND_USERNAME", "Tài khoản"),
                ("ND_PASSWORD", "Mật khẩu"),
            )
            if not values.get(key)
        ]
        if missing:
            dialog.set_status("Còn thiếu: " + ", ".join(missing), error=True)
            return

        try:
            max_tabs = int(values.get("ND_MAX_PREPARED_TABS") or "10")
            delay_ms = int(values.get("ND_POST_PREPARE_DELAY_MS") or "1500")
            if max_tabs <= 0 or delay_ms < 0:
                raise ValueError
        except ValueError:
            dialog.set_status("Số tab tối đa phải > 0 và delay phải >= 0.", error=True)
            return

        values["ND_BASE_URL"] = base_url
        values["ND_MAX_PREPARED_TABS"] = str(max_tabs)
        values["ND_POST_PREPARE_DELAY_MS"] = str(delay_ms)
        values["ND_STORAGE_STATE_PATH"] = "nd_storage_state.json"
        dialog.set_busy(True)
        dialog.set_status("Đang lưu cấu hình và đăng nhập để tạo nd_storage_state.json...")

        def worker() -> None:
            try:
                save_uploader_env(values, base_dir=self.working_dir)
                session = NamDinhUploaderSession(
                    load_uploader_settings(self.working_dir),
                    working_dir=self.working_dir,
                    log_callback=self.async_log.emit,
                )
                try:
                    session.ensure_authenticated()
                finally:
                    session.close()
            except Exception as exc:  # pragma: no cover - threaded UI plumbing
                self.upload_config_error_signal.emit(str(exc))
                return
            self.upload_config_saved_signal.emit()

        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot()
    def _on_upload_config_saved(self) -> None:
        if self._config_dialog is not None:
            self._config_dialog.accept()
            self._config_dialog = None
        self.async_log.emit("[UPLOAD][CONFIG] Đã lưu cấu hình uploader và tạo nd_storage_state.json.")
        self._refresh_upload_runtime_state()
        if self.upload_tab.get_manifest_path():
            self._on_upload_refresh_queue()
        self._notify_upload(
            "Đã lưu cấu hình web và đăng nhập thành công. Bạn có thể tiếp tục thao tác.",
            level="success",
            status_message="Đã lưu cấu hình web",
        )

    @pyqtSlot(str)
    def _on_upload_config_error(self, error_text: str) -> None:
        if self._config_dialog is not None:
            self._config_dialog.set_busy(False)
            self._config_dialog.set_status("Không đăng nhập được. Kiểm tra lại thông tin rồi thử lại.", error=True)
        self.async_log.emit(f"[UPLOAD][CONFIG] Lỗi cấu hình uploader: {error_text}")
        self._notify_upload(
            "Không đăng nhập được vào web. Kiểm tra lại cấu hình rồi thử lại.",
            level="error",
            status_message="Không đăng nhập được vào web",
        )

    @pyqtSlot(str)
    def _on_manifest_path_changed(self, path: str) -> None:
        if self._restoring_settings:
            return
        self.async_log.emit(f"[UPLOAD][INPUT] Chọn manifest: {path or '(trống)'}")
        self.upload_tab.clear_manifest_notice()
        self._last_upload_summary = None
        self._live_upload_summary = {}
        self._queue_rows_by_id = {}
        self._duplicate_rows_by_id = {}
        self.upload_tab.load_queue_records([])
        self.upload_tab.load_duplicate_records([])
        self._clear_upload_notice()
        self.upload_tab.clear_requester_notice()
        self._sync_upload_summary(manifest_name=Path(path).name if path else "-", run_id="-")
        if path:
            self.upload_tab.set_ui_state("loading_queue")
            self.upload_tab.set_compare_status("", False)
            if not self._upload_running:
                self._on_upload_refresh_queue()
        else:
            self.upload_tab.set_ui_state("no_manifest")
            self.upload_tab.set_compare_status("", False)

    @pyqtSlot(str)
    def _on_requester_sheet_url_changed(self, url: str) -> None:
        if self._restoring_settings:
            return
        self.async_log.emit(f"[UPLOAD][INPUT] Cap nhat link doi chieu requester: {url or '(trong)'}")
        self.upload_tab.clear_requester_notice()
        if self.upload_tab.get_manifest_path() and not self._upload_running:
            self._on_upload_refresh_queue()

    @pyqtSlot(str)
    def _on_export_path_changed(self, path: str) -> None:
        if self._restoring_settings:
            return
        self.async_log.emit(f"[UPLOAD][INPUT] Chọn file đối chiếu: {path or '(trống)'}")
        self.upload_tab.clear_export_notice()
        if path:
            self.upload_tab.set_compare_status("", False)
            self._clear_upload_notice()
            if self.upload_tab.get_manifest_path() and not self._upload_running:
                self._on_upload_refresh_queue()
        else:
            self.upload_tab.set_compare_status("", False)
            if self.upload_tab.get_manifest_path() and not self._upload_running:
                self._on_upload_refresh_queue()

    @pyqtSlot()
    def _on_upload_refresh_queue(self) -> None:
        if self._upload_running:
            return

        manifest_value = self.upload_tab.get_manifest_path().strip()
        if not manifest_value:
            self._queue_rows_by_id = {}
            self._duplicate_rows_by_id = {}
            self.upload_tab.load_queue_records([])
            self.upload_tab.load_duplicate_records([])
            self.upload_tab.set_ui_state("no_manifest")
            self.upload_tab.set_manifest_notice("Chưa có file manifest.", level="warning")
            self._sync_upload_summary(manifest_name="-", run_id="-")
            return

        manifest_path = Path(manifest_value)
        if not manifest_path.exists():
            self.upload_tab.set_ui_state("error")
            self.async_log.emit(f"[UPLOAD][QUEUE] Không tìm thấy manifest: {manifest_path}")
            self.upload_tab.set_manifest_notice("Không tìm thấy file manifest. Hãy chọn lại.", level="warning")
            return

        self.upload_tab.set_ui_state("loading_queue")
        self.statusBar().showMessage("Đang tải queue upload...")
        self._clear_upload_notice()
        self.async_log.emit(f"[UPLOAD][QUEUE] Bắt đầu nạp queue từ manifest: {manifest_path}")

        requester_lookup, requester_warning = load_requester_contract_lookup(
            working_dir=self.working_dir,
            sheet_url=self.upload_tab.get_requester_sheet_url(),
            log_callback=self.async_log.emit,
        )
        if requester_warning:
            self.upload_tab.set_requester_notice(requester_warning, level="warning")

        try:
            manifest, records, total_pending = load_upload_queue(
                manifest_path,
                working_dir=self.working_dir,
                requester_lookup=requester_lookup,
            )
        except Exception as exc:
            self.upload_tab.load_queue_records([])
            self.upload_tab.load_duplicate_records([])
            self.upload_tab.set_ui_state("error")
            self.async_log.emit(f"[UPLOAD][QUEUE] Lỗi đọc queue: {exc}")
            self._notify_upload(
                "Không nạp được danh sách hồ sơ. Mở log để xem chi tiết lỗi đọc manifest hoặc dữ liệu queue.",
                level="error",
                status_message="Không nạp được danh sách hồ sơ",
            )
            return

        self.upload_tab.clear_manifest_notice()
        if not requester_warning:
            self.upload_tab.clear_requester_notice()
        self.async_log.emit(
            f"[UPLOAD][QUEUE] Đã đọc manifest run_id={manifest.get('run_id')} | records={len(records)} | pending={total_pending}"
        )
        existing_contract_nos = self._load_existing_web_contract_nos()
        filtered_records, duplicate_records = split_records_by_existing_contract_nos(records, existing_contract_nos)
        self._current_manifest = manifest
        self._current_total_pending = total_pending

        previous_selected = {
            record_id for record_id, row in self._queue_rows_by_id.items() if bool(row.get("selected"))
        }
        queue_rows = [self._build_upload_row(record, selected=record.record_id in previous_selected) for record in filtered_records]
        duplicate_rows = [self._build_upload_row(record, selected=False) for record in duplicate_records]

        self._queue_rows_by_id = {int(row["record_id"]): dict(row) for row in queue_rows}
        self._duplicate_rows_by_id = {int(row["record_id"]): dict(row) for row in duplicate_rows}
        self.upload_tab.load_queue_records(queue_rows)
        self.upload_tab.load_duplicate_records(duplicate_rows)
        self._sync_upload_summary(
            manifest_name=manifest_path.name,
            run_id=str(manifest.get("run_id") or "-"),
            total_pending=total_pending,
            queue_rows=queue_rows,
            all_statuses=[record.status for record in records],
            duplicate_count=len(duplicate_rows),
        )

        if not queue_rows:
            self.upload_tab.set_ui_state("queue_empty")
        elif any(bool(row.get("needs_manual_review")) for row in queue_rows):
            self.upload_tab.set_ui_state("has_partial")
        else:
            self.upload_tab.set_ui_state("queue_ready")

        self.statusBar().showMessage("Đã tải queue upload")
        self.async_log.emit(
            f"[UPLOAD] Queue refreshed: pending={len(queue_rows)}/{total_pending} | duplicate_web={len(duplicate_rows)}"
        )
        self._clear_upload_notice()

    def _load_existing_web_contract_nos(self) -> set[str]:
        export_value = self.upload_tab.get_export_path().strip()
        if not export_value:
            self._existing_web_contract_nos = set()
            self._web_compare_loaded = False
            self.upload_tab.clear_export_notice()
            self.upload_tab.set_compare_status("", False)
            self.async_log.emit("[UPLOAD][COMPARE] Chưa có file Excel đối chiếu.")
            return set()

        export_path = Path(export_value)
        if not export_path.exists():
            self._existing_web_contract_nos = set()
            self._web_compare_loaded = False
            self.upload_tab.set_export_notice("Không tìm thấy file Excel đối chiếu. Hãy chọn lại.", level="warning")
            self.upload_tab.set_compare_status("", False)
            self.async_log.emit(f"[UPLOAD][COMPARE] Không tìm thấy file Excel đối chiếu: {export_path}")
            return set()

        self.async_log.emit(f"[UPLOAD][COMPARE] Bắt đầu đọc file đối chiếu: {export_path}")
        try:
            contract_nos = read_exported_contract_numbers(export_path)
        except Exception as exc:
            self._existing_web_contract_nos = set()
            self._web_compare_loaded = False
            self.upload_tab.set_export_notice("Không đọc được file Excel đối chiếu. Kiểm tra lại file.", level="warning")
            self.upload_tab.set_compare_status("", False)
            self.async_log.emit(f"[UPLOAD][DUP] Lỗi đọc file đối chiếu {export_path}: {exc}")
            return set()

        self._existing_web_contract_nos = contract_nos
        self._web_compare_loaded = True
        self.upload_tab.clear_export_notice()
        self.upload_tab.set_compare_status("", True)
        self.async_log.emit(f"[UPLOAD][COMPARE] Đã nạp {len(contract_nos)} số công chứng từ {export_path.name}")
        return contract_nos

    def _build_upload_row(self, record, *, selected: bool) -> dict[str, Any]:
        raw = dict(record.raw_row or {})
        verify: dict[str, Any] = {}
        verify_json = str(raw.get("verify_json") or "").strip()
        if verify_json:
            try:
                verify = json.loads(verify_json)
            except json.JSONDecodeError:
                verify = {"warnings": ["verify_json không hợp lệ"], "fields": {}}

        artifact_dir = str(raw.get("artifact_dir") or "").strip()
        screenshot = ""
        debug_json = ""
        if artifact_dir:
            artifact_path = Path(artifact_dir)
            contract_key = sanitize_contract_no(record.contract_no)
            screenshot_candidate = artifact_path / f"before_save_{contract_key}.png"
            debug_candidate = artifact_path / f"debug_{contract_key}.json"
            if screenshot_candidate.exists():
                screenshot = str(screenshot_candidate)
            if debug_candidate.exists():
                debug_json = str(debug_candidate)

        needs_manual_review = bool(
            record.missing_fields
            or str(record.status) in {"prepared_partial", "upload_failed"}
            or str(raw.get("last_error") or "").strip()
        )
        ready_to_finalize = str(record.status) in QUEUE_ALLOWED_FINALIZE
        return {
            "record_id": int(record.record_id),
            "contract_no": record.contract_no,
            "status": str(record.status),
            "status_text": UPLOAD_STATUS_LABELS.get(str(record.status), str(record.status)),
            "source_file": str(record.source_file),
            "missing_fields": list(record.missing_fields or []),
            "reason": str(raw.get("reason") or ""),
            "last_error": str(raw.get("last_error") or ""),
            "prepared_at": str(raw.get("prepared_at") or ""),
            "uploaded_success_at": str(raw.get("uploaded_success_at") or ""),
            "artifact_dir": artifact_dir if artifact_dir and Path(artifact_dir).exists() else "",
            "screenshot": screenshot,
            "debug_json": debug_json,
            "verify": verify,
            "upload_form": dict(record.upload_form or {}),
            "needs_manual_review": needs_manual_review,
            "ready_to_finalize": ready_to_finalize,
            "selected": bool(selected),
        }

    def _sync_upload_summary(self, **kwargs: Any) -> None:
        manifest_name = kwargs.get("manifest_name")
        if manifest_name is None:
            manifest_path = self.upload_tab.get_manifest_path()
            manifest_name = Path(manifest_path).name if manifest_path else "-"
        run_id = kwargs.get("run_id")
        total_pending = kwargs.get("total_pending", self._current_total_pending)
        queue_rows = kwargs.get("queue_rows", list(self._queue_rows_by_id.values()))
        all_statuses = kwargs.get("all_statuses", [str(row.get("status", "")) for row in queue_rows])
        duplicate_count = kwargs.get("duplicate_count", len(self._duplicate_rows_by_id))

        if self._current_manifest:
            run_id = run_id or str(self._current_manifest.get("run_id") or "-")
        else:
            run_id = run_id or "-"

        status_counter = Counter(all_statuses)
        status_text = ", ".join(
            f"{UPLOAD_STATUS_LABELS.get(status, status)}: {count}"
            for status, count in (
                ("extracted", status_counter.get("extracted", 0)),
                ("upload_failed", status_counter.get("upload_failed", 0)),
                ("prepared_dry_run", status_counter.get("prepared_dry_run", 0)),
                ("prepared_partial", status_counter.get("prepared_partial", 0)),
                ("uploaded_success", status_counter.get("uploaded_success", 0)),
            )
            if count
        ) or "-"

        same_run_summary = (
            self._last_upload_summary
            if self._last_upload_summary and str(self._last_upload_summary.get("run_id")) == str(run_id)
            else None
        )
        live_summary = (
            self._live_upload_summary
            if str(self._live_upload_summary.get("run_id", run_id)) == str(run_id)
            else {}
        )
        prepared_last_chunk = live_summary.get("prepared_count")
        if prepared_last_chunk is None and same_run_summary is not None:
            prepared_last_chunk = same_run_summary.get("prepared_count")

        remaining_count = live_summary.get("remaining")
        if remaining_count is None and same_run_summary is not None:
            remaining_count = same_run_summary.get("remaining")
        if remaining_count is None:
            remaining_count = len(queue_rows)

        artifact_dir = str(live_summary.get("artifact_dir") or "")
        if not artifact_dir and same_run_summary is not None:
            artifact_dir = str(same_run_summary.get("artifact_dir") or "")
        if not artifact_dir:
            artifact_dir = next((str(row.get("artifact_dir") or "") for row in queue_rows if row.get("artifact_dir")), "")

        pending_text = f"{len(queue_rows)}/{total_pending}" if total_pending else str(len(queue_rows))
        if duplicate_count:
            pending_text += f" | trùng web {duplicate_count}"

        self.upload_tab.set_summary(
            {
                "manifest_name": manifest_name,
                "run_id": run_id,
                "pending_count": pending_text,
                "prepared_last_chunk": prepared_last_chunk if prepared_last_chunk is not None else "-",
                "remaining_count": remaining_count,
                "status_counts": status_text,
                "artifact_dir": artifact_dir or "-",
            }
        )

    @pyqtSlot(str)
    def _on_upload_start(self, manifest_path: str) -> None:
        if self._upload_running or self.upload_worker.isRunning():
            return
        if not self._ensure_upload_runtime_ready(show_dialog=True):
            self.async_log.emit(f"[UPLOAD][RUN] Chưa thể upload: {self.playwright_message}")
            self._notify_upload(
                self.upload_tab.runtime_label.text(),
                level="warning",
                status_message="Chưa sẵn sàng kết nối web",
            )
            return
        if not self.upload_tab.get_export_path().strip():
            self._notify_upload(
                "Vui lòng chọn file Excel đối chiếu hoặc tải danh sách web trước khi upload.",
                level="warning",
                status_message="Thiếu file đối chiếu",
            )
            return
        self._load_existing_web_contract_nos()
        if not self._web_compare_loaded:
            self._notify_upload(
                "Chưa đọc được dữ liệu đối chiếu từ Excel. Kiểm tra lại file rồi thử lại.",
                level="warning",
                status_message="Chưa đọc được dữ liệu đối chiếu",
            )
            return

        if not self._queue_rows_by_id:
            self._notify_upload(
                "Danh sách hiện không còn hồ sơ nào để upload.",
                level="info",
                status_message="Không còn hồ sơ để xử lý",
            )
            return

        self._upload_running = True
        self._upload_stop_requested = False
        self._live_upload_summary = {}
        self.upload_tab.set_ui_state("dry_run_running")
        self.statusBar().showMessage("Đang upload hồ sơ lên web...")
        self._notify_upload(
            "Phần mềm đang upload hồ sơ lên web. Có thể mở log nếu cần theo dõi chi tiết từng bước.",
            level="info",
            status_message="Đang upload hồ sơ lên web",
        )
        self.async_log.emit(
            f"[UPLOAD][RUN] Bắt đầu upload | manifest={manifest_path} | compare_loaded={len(self._existing_web_contract_nos)} | queue={len(self._queue_rows_by_id)}"
        )
        self.upload_worker.set_config(
            manifest_path=manifest_path,
            exclude_contract_nos=self._existing_web_contract_nos,
            requester_sheet_url=self.upload_tab.get_requester_sheet_url(),
            working_dir=self.working_dir,
        )
        self.upload_worker.start()

    @pyqtSlot()
    def _on_upload_stop(self) -> None:
        if not self._upload_running:
            return
        self._upload_stop_requested = True
        self.upload_worker.request_stop()
        self.statusBar().showMessage("Đang dừng sau hồ sơ hiện tại...")
        self._notify_upload(
            "Đã ghi nhận yêu cầu dừng. Phần mềm sẽ dừng sau khi xử lý xong hồ sơ hiện tại.",
            level="warning",
            status_message="Đang dừng sau hồ sơ hiện tại",
        )
        self.async_log.emit("[UPLOAD] Đã gửi yêu cầu dừng. Worker sẽ dừng sau hồ sơ hiện tại.")

    @pyqtSlot(dict)
    def _on_upload_progress(self, info: dict) -> None:
        event = str(info.get("event") or "")
        if event in {"queue_loaded", "record_started", "record_prepared", "record_failed", "stopped", "finished"}:
            self._live_upload_summary = {
                "run_id": info.get("run_id") or (self._current_manifest or {}).get("run_id") or "-",
                "prepared_count": info.get("prepared_count"),
                "remaining": info.get("remaining"),
                "artifact_dir": info.get("artifact_dir", ""),
            }
            self._sync_upload_summary(
                manifest_name=Path(self.upload_tab.get_manifest_path()).name if self.upload_tab.get_manifest_path() else "-",
                duplicate_count=len(self._duplicate_rows_by_id),
            )
        if event == "queue_loaded":
            self.async_log.emit(
                "[UPLOAD][RUN] Đã nạp chunk upload | "
                f"chunk={info.get('chunk_size', 0)} | pending={info.get('filtered_pending', 0)} | "
                f"duplicate_web={info.get('excluded_duplicates', 0)}"
            )
        elif event == "record_started":
            self.statusBar().showMessage(f"Đang upload {info.get('contract_no', '')}...")
            self.async_log.emit(
                f"[UPLOAD][RUN] Đang xử lý record #{info.get('record_id')} | số={info.get('contract_no', '')} | còn lại={info.get('remaining', 0)}"
            )
        elif event == "record_prepared":
            self.statusBar().showMessage(f"Đã điền nháp {info.get('contract_no', '')}, chờ rà soát")
            self.async_log.emit(
                f"[UPLOAD][RUN] Hoàn tất hồ sơ {info.get('contract_no', '')} | trạng thái={info.get('status', '')} | còn lại={info.get('remaining', 0)}"
            )
        elif event == "record_failed":
            self.statusBar().showMessage(f"Hồ sơ cần kiểm tra lại: {info.get('contract_no', '')}")
            self._notify_upload(
                f"Hồ sơ {info.get('contract_no', '')} cần kiểm tra lại. Có thể mở log để xem chi tiết.",
                level="warning",
            )
            self.async_log.emit(
                f"[UPLOAD][RUN] Hồ sơ lỗi #{info.get('record_id')} | số={info.get('contract_no', '')} | lỗi={info.get('error', '')}"
            )
        elif event == "stopped":
            self.statusBar().showMessage("Đã ghi nhận yêu cầu dừng.")
            self.async_log.emit(
                f"[UPLOAD][RUN] Đã dừng theo yêu cầu | prepared={info.get('prepared_count', 0)} | remaining={info.get('remaining', 0)}"
            )
        elif event == "finished":
            self.async_log.emit(
                f"[UPLOAD][RUN] Kết thúc chunk | prepared={info.get('prepared_count', 0)} | remaining={info.get('remaining', 0)} | artifact={info.get('artifact_dir', '')}"
            )

    @pyqtSlot(dict)
    def _on_upload_finished(self, summary: dict) -> None:
        self._upload_running = False
        self._last_upload_summary = dict(summary)
        self._live_upload_summary = dict(summary)
        self._on_upload_refresh_queue()
        if self._upload_stop_requested:
            self.upload_tab.set_ui_state("dry_run_stopped")
            self.statusBar().showMessage("Đã dừng upload")
        else:
            self.statusBar().showMessage("Đã điền xong, chờ lưu thủ công trên web")
            if self._queue_rows_by_id:
                if any(bool(row.get("needs_manual_review")) for row in self._queue_rows_by_id.values()):
                    self.upload_tab.set_ui_state("has_partial")
                else:
                    self.upload_tab.set_ui_state("queue_ready")
            else:
                self.upload_tab.set_ui_state("queue_empty")
        self._upload_stop_requested = False
        error_count = len(summary.get("errors") or [])
        if error_count:
            level = "warning"
            message = (
                f"Đã điền nháp {summary.get('prepared_count', 0)} hồ sơ. "
                f"Có {error_count} hồ sơ cần kiểm tra lại trong danh sách và log trước khi bấm Lưu."
            )
        else:
            level = "success"
            message = (
                f"Đã điền nháp {summary.get('prepared_count', 0)} hồ sơ. "
                "Trình duyệt vẫn mở để bạn rà soát, bấm Lưu rồi quay lại xác nhận upload."
            )
        if summary.get("artifact_dir"):
            message += f" Artifact mới: {summary.get('artifact_dir')}"
        self._notify_upload(
            message,
            level=level,
            status_message="Chờ rà soát và lưu thủ công",
        )

    @pyqtSlot(str)
    def _on_upload_error(self, error_msg: str) -> None:
        self._upload_running = False
        self._upload_stop_requested = False
        self._on_upload_refresh_queue()
        self.upload_tab.set_ui_state("error")
        self.statusBar().showMessage("Lỗi upload")
        self.async_log.emit(f"[UPLOAD][RUN] Lỗi worker upload: {error_msg}")
        self._notify_upload(
            "Không upload được hồ sơ lên web. Mở log để xem chi tiết và thử lại.",
            level="error",
            status_message="Không upload được hồ sơ",
        )

    @pyqtSlot(list)
    def _on_upload_finalize(self, record_ids: list) -> None:
        valid_ids = [
            record_id
            for record_id in record_ids
            if self._queue_rows_by_id.get(int(record_id), {}).get("ready_to_finalize")
        ]
        skipped_ids = [record_id for record_id in record_ids if record_id not in valid_ids]
        if not valid_ids:
            self._notify_upload(
                "Chỉ các hồ sơ đã upload hoặc cần rà soát mới có thể xác nhận đã upload.",
                level="warning",
                status_message="Không thể xác nhận các hồ sơ đã chọn",
            )
            return

        self.async_log.emit(f"[UPLOAD][FINALIZE] Bắt đầu xác nhận đã upload cho {len(valid_ids)} hồ sơ")
        count = finalize_uploaded_records(valid_ids, working_dir=self.working_dir)
        self.async_log.emit(f"[UPLOAD][FINALIZE] Đã cập nhật {count} hồ sơ sang uploaded_success")
        self._last_upload_summary = None
        self._on_upload_refresh_queue()
        self.upload_tab.set_ui_state("finalize_success")
        message = f"Đã xác nhận {count} hồ sơ đã upload."
        if skipped_ids:
            message += f"\nBỏ qua {len(skipped_ids)} hồ sơ chưa đủ điều kiện xác nhận."
        self._notify_upload(message, level="success", status_message="Đã cập nhật trạng thái hồ sơ")

    @pyqtSlot(tuple)
    def _on_download_web_export(self, dates: tuple) -> None:
        if not self._ensure_upload_runtime_ready(show_dialog=True):
            self.async_log.emit(f"[UPLOAD][EXPORT] Chưa thể tải danh sách web: {self.playwright_message}")
            self._notify_upload(
                self.upload_tab.runtime_label.text(),
                level="warning",
                status_message="Chưa sẵn sàng kết nối web",
            )
            return

        from_date, to_date = dates
        self.statusBar().showMessage("Đang tải số công chứng từ web...")
        self._notify_upload(
            "Đang tải danh sách số công chứng từ web. Có thể mở log để theo dõi chi tiết.",
            level="info",
            status_message="Đang tải danh sách từ web",
        )
        self.async_log.emit(f"[UPLOAD][EXPORT] Bắt đầu tải số công chứng từ web | from={from_date} | to={to_date}")

        def worker() -> None:
            try:
                export_path = download_contract_book_export(
                    from_date=from_date,
                    to_date=to_date,
                    working_dir=self.working_dir,
                    log_callback=self.async_log.emit,
                )
            except Exception as exc:  # pragma: no cover - threaded UI plumbing
                self.export_download_error_signal.emit(str(exc))
                return
            self.export_downloaded_signal.emit(str(export_path))

        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot(str)
    def _on_export_downloaded(self, export_path: str) -> None:
        self.upload_tab.set_export_path(export_path)
        self.statusBar().showMessage("Đã tải số công chứng từ web")
        applied_message = f"Đã tải xong danh sách từ web và chọn {Path(export_path).name} làm file đối chiếu mặc định."
        if self.upload_tab.get_manifest_path():
            applied_message += " Danh sách hồ sơ đã được nạp lại theo file mới."
        self.async_log.emit(f"[UPLOAD][EXPORT] Đã tải xong file Excel: {export_path}")
        self._notify_upload(
            applied_message,
            level="success",
            status_message="Đã tải danh sách từ web",
        )

    @pyqtSlot(str)
    def _on_export_download_error(self, error_text: str) -> None:
        self.statusBar().showMessage("Lỗi tải số công chứng từ web")
        self.async_log.emit(f"[UPLOAD][EXPORT] Tải danh sách web thất bại: {error_text}")
        self._notify_upload(
            "Không tải được danh sách số công chứng từ web. Mở log để xem chi tiết và thử lại.",
            level="error",
            status_message="Không tải được danh sách từ web",
        )

    def _open_source_for_record(self, record_id: int) -> None:
        row = self._queue_rows_by_id.get(record_id) or self._duplicate_rows_by_id.get(record_id)
        if not row:
            return
        self._open_path(str(row.get("source_file") or ""))

    def _open_path(self, path: str) -> None:
        target = Path(str(path or "").strip())
        if not target.exists():
            self.async_log.emit(f"[UPLOAD] Không tìm thấy đường dẫn: {target}")
            self._notify_upload(
                "Không tìm thấy tệp hoặc thư mục cần mở. Kiểm tra lại hồ sơ hoặc artifact.",
                level="warning",
                status_message="Không tìm thấy đường dẫn",
            )
            return
        try:
            os.startfile(str(target))
            self.async_log.emit(f"[UPLOAD] Mở: {target}")
        except Exception as exc:
            self.async_log.emit(f"[UPLOAD] Không mở được {target}: {exc}")
            self._notify_upload(
                "Không mở được tệp hoặc thư mục này. Mở log để xem chi tiết hệ thống.",
                level="error",
                status_message="Không mở được tệp",
            )

    @pyqtSlot(dict)
    def _on_batch_run_clicked(self, config: dict) -> None:
        self._clear_batch_notice()
        self.batch_worker.set_config(
            folder=config["folder"],
            modified_since=config.get("modified_since"),
            full_rescan=config.get("full_rescan", False),
            max_depth=config.get("max_depth", MAX_SCAN_DEPTH),
            working_dir=self.working_dir,
        )
        self.batch_worker.start()
        self.statusBar().showMessage("Đang quét hồ sơ...")
        self._notify_batch(
            "Đang quét hồ sơ. Có thể mở log nếu cần theo dõi chi tiết.",
            level="info",
            status_message="Đang quét hồ sơ",
        )
        self.log_viewer.append_log(
            "[BATCH] Bắt đầu quét folder: "
            f"{config['folder']} | modified_since={config.get('modified_since') or '-'} | "
            f"full_rescan={config.get('full_rescan', False)} | max_depth={config.get('max_depth', MAX_SCAN_DEPTH)}"
        )

    @pyqtSlot(dict)
    def _on_batch_progress(self, snapshot: dict) -> None:
        stage = snapshot.get("stage", "")
        step = snapshot.get("step", "")
        processed = int(snapshot.get("processed_files", 0))
        total = int(snapshot.get("total_files", 0))
        stats = dict(snapshot.get("stats", {}))
        current_file = str(snapshot.get("current_file", ""))
        last_outcome = str(snapshot.get("last_outcome", ""))
        last_contract_no = str(snapshot.get("last_contract_no", ""))
        rate = float(snapshot.get("files_per_second", 0.0))
        eta_seconds = snapshot.get("eta_seconds")
        elapsed_seconds = float(snapshot.get("elapsed_seconds", 0.0))

        progress_value = (processed / total * 100.0) if total else 0.0
        if stage == "done" and total:
            progress_value = 100.0
        self.batch_tab.set_progress(int(progress_value))

        if stage == "indexing":
            status = "Đang chuẩn bị danh sách file"
            detail = (
                f"Word {stats.get('total_docx_files', 0)} | "
                f"hỗ trợ {stats.get('total_supported_files', 0)}"
            )
        else:
            eta_text = self._format_seconds(eta_seconds)
            status_parts = [f"đã xử lý {processed}/{total or 0}"]
            if stage == "done":
                status = "Hoàn tất"
            elif step == "extract":
                status = "Đang trích xuất"
            else:
                status = "Đang quét"
            detail_parts = status_parts + [
                f"ứng viên {stats.get('candidates_found', 0)}",
                f"thành công {stats.get('extract_success', 0)}",
                f"partial {stats.get('extract_partial', 0)}",
                f"lỗi {stats.get('extract_failed', 0)}",
            ]
            if rate > 0:
                detail_parts.append(f"tốc độ {rate:.2f} file/s")
            if eta_text != "--":
                detail_parts.append(f"ETA {eta_text}")
            if last_contract_no:
                detail_parts.append(f"số {last_contract_no}")
            detail = " | ".join(detail_parts)

        self.batch_tab.set_status(status)
        self.batch_tab.set_detail(detail)
        self.batch_tab.set_file(current_file)

    @pyqtSlot(dict)
    def _on_batch_finished(self, manifest: dict) -> None:
        manifest_path = manifest.get("manifest_path", "")
        output_folder = str(self.working_dir / "output")
        stats = manifest.get("stats", {})
        summary = (
            f"đã xử lý {stats.get('processed_files', 0)}/{stats.get('total_supported_files', 0)} | "
            f"ứng viên {stats.get('candidates_found', 0)} | "
            f"thành công {stats.get('extract_success', 0)} | "
            f"partial {stats.get('extract_partial', 0)} | "
            f"lỗi {stats.get('extract_failed', 0)}"
        )
        self.batch_tab.set_results(manifest_path, output_folder, summary)
        self.batch_tab.enable_run_button(True)
        self.statusBar().showMessage("Quét hồ sơ hoàn tất")
        self.async_log.emit(
            f"[BATCH] Hoàn tất quét hồ sơ | manifest={manifest_path} | output={output_folder} | summary={summary}"
        )
        self._notify_batch(
            f"Đã quét hồ sơ xong. Manifest mới đã sẵn sàng cho tab upload.",
            level="success",
            status_message="Quét hồ sơ hoàn tất",
        )
        self._apply_manifest_to_upload(str(manifest_path))

    @pyqtSlot(str)
    def _on_batch_error(self, error_msg: str) -> None:
        self.batch_tab.enable_run_button(True)
        self.statusBar().showMessage("Lỗi quét hồ sơ")
        self.async_log.emit(f"[BATCH] Lỗi quét hồ sơ: {error_msg}")
        self._notify_batch(
            "Không quét được hồ sơ. Mở log để xem chi tiết lỗi rồi thử lại.",
            level="error",
            status_message="Không quét được hồ sơ",
        )

    @staticmethod
    def _format_seconds(seconds: float | None) -> str:
        if seconds is None:
            return "--"
        total_seconds = max(0, int(round(seconds)))
        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def closeEvent(self, event) -> None:  # pragma: no cover - UI shutdown
        self._save_settings()
        if self.upload_worker.isRunning():
            self.upload_worker.request_stop()
            self.upload_worker.wait(2000)
        event.accept()
