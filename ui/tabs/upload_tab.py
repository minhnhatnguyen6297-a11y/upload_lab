"""Upload tab UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import FileBrowserWidget, RecordsTableWidget


STATE_MESSAGES = {
    "no_manifest": "Chọn manifest để bắt đầu làm việc.",
    "manifest_selected_unloaded": "Đã chọn manifest. Danh sách hồ sơ sẽ được nạp tự động.",
    "loading_queue": "Đang nạp danh sách hồ sơ từ manifest.",
    "queue_empty": "Hiện chưa còn hồ sơ nào cần xử lý trong manifest này.",
    "queue_ready": "Danh sách hồ sơ đã sẵn sàng để thao tác.",
    "dry_run_running": "Phần mềm đang upload hồ sơ lên web.",
    "dry_run_stopped": "Đã dừng sau hồ sơ hiện tại. Bạn có thể kiểm tra rồi upload tiếp.",
    "has_partial": "Có hồ sơ cần kiểm tra lại trước khi xác nhận đã upload.",
    "error": "Một thao tác chưa hoàn tất. Xem ghi chú bên dưới để biết cần xử lý gì.",
    "finalize_success": "Đã cập nhật trạng thái cho các hồ sơ đã chọn.",
}


class UploadTab(QWidget):
    """Console-style upload control panel."""

    configure_uploader = pyqtSignal()
    refresh_queue = pyqtSignal()
    start_upload = pyqtSignal(str)
    stop_upload = pyqtSignal()
    finalize_records = pyqtSignal(list)
    download_web_export = pyqtSignal(tuple)
    manifest_path_changed = pyqtSignal(str)
    export_path_changed = pyqtSignal(str)
    open_source_requested = pyqtSignal(int)
    open_path_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(1200)
        self._state = "no_manifest"
        self._runtime_ready = False
        self._compare_loaded = False
        self._queue_rows: dict[int, dict[str, Any]] = {}
        self._duplicate_rows: dict[int, dict[str, Any]] = {}
        self._current_record_id: int | None = None
        self._record_notes: dict[int, str] = {}
        self._build_ui()
        self.set_ui_state("no_manifest")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        data_group = QGroupBox("Dữ liệu đầu vào")
        data_layout = QGridLayout(data_group)
        data_layout.setContentsMargins(12, 14, 12, 12)
        data_layout.setHorizontalSpacing(12)
        data_layout.setVerticalSpacing(8)
        self.manifest_browser = FileBrowserWidget(
            label_text="Manifest hồ sơ",
            button_text="Chọn manifest",
            dialog_title="Chọn manifest batch scan",
            file_filter="JSON Files (*.json)",
            placeholder_text="Chưa chọn manifest",
        )
        self.manifest_browser.browse_btn.setFixedWidth(150)
        self.manifest_browser.file_changed.connect(self.manifest_path_changed.emit)
        data_layout.addWidget(self.manifest_browser, 0, 0, 1, 2)

        self.manifest_notice = QLabel("")
        self.manifest_notice.setObjectName("inlineNotice")
        self.manifest_notice.setWordWrap(True)
        self.manifest_notice.setVisible(False)
        data_layout.addWidget(self.manifest_notice, 1, 0, 1, 2)

        self.export_browser = FileBrowserWidget(
            label_text="Excel đối chiếu số công chứng",
            button_text="Chọn Excel",
            dialog_title="Chọn file Excel đối chiếu",
            file_filter="Excel Files (*.xlsx *.xlsm *.xltx *.xltm)",
            placeholder_text="Chưa chọn file Excel đối chiếu",
        )
        self.export_browser.browse_btn.setFixedWidth(150)
        self.export_browser.file_changed.connect(self.export_path_changed.emit)
        data_layout.addWidget(self.export_browser, 2, 0, 1, 2)

        self.export_notice = QLabel("")
        self.export_notice.setObjectName("inlineNotice")
        self.export_notice.setWordWrap(True)
        self.export_notice.setVisible(False)
        data_layout.addWidget(self.export_notice, 3, 0, 1, 2)

        web_group = QFrame()
        web_group_layout = QHBoxLayout(web_group)
        web_group_layout.setContentsMargins(0, 0, 0, 0)
        web_group_layout.setSpacing(8)
        web_group_layout.addWidget(QLabel("Từ ngày"))
        self.from_date_input = QLineEdit()
        self.from_date_input.setMaximumWidth(120)
        web_group_layout.addWidget(self.from_date_input)
        web_group_layout.addWidget(QLabel("Đến ngày"))
        self.to_date_input = QLineEdit()
        self.to_date_input.setMaximumWidth(120)
        web_group_layout.addWidget(self.to_date_input)
        self.download_btn = QPushButton("Tải danh sách web")
        self.download_btn.setFixedWidth(150)
        self.download_btn.clicked.connect(self._on_download_clicked)
        web_group_layout.addWidget(self.download_btn)
        web_group_layout.addStretch(1)
        data_layout.addWidget(web_group, 4, 0, 1, 2)

        self.runtime_label = QLabel("Chưa kiểm tra khả năng kết nối web.")
        self.runtime_label.setObjectName("inlineNotice")
        self.runtime_label.setWordWrap(True)
        self.runtime_label.setVisible(False)
        data_layout.addWidget(self.runtime_label, 5, 0)

        self.compare_label = QLabel("Chưa nạp dữ liệu đối chiếu.")
        self.compare_label.setObjectName("inlineNotice")
        self.compare_label.setWordWrap(True)
        self.compare_label.setVisible(False)
        data_layout.addWidget(self.compare_label, 5, 1)
        root.addWidget(data_group)

        action_frame = QFrame()
        action_frame.setObjectName("actionBar")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(10, 10, 10, 10)
        action_layout.setSpacing(8)

        self.configure_btn = QPushButton("Cấu hình web")
        self.configure_btn.clicked.connect(self.configure_uploader.emit)

        self.refresh_btn = QPushButton("Nạp lại DS")
        self.refresh_btn.clicked.connect(self.refresh_queue.emit)

        self.start_btn = QPushButton("Upload")
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.stop_btn = QPushButton("Dừng")
        self.stop_btn.clicked.connect(self.stop_upload.emit)

        self.finalize_btn = QPushButton("Xác nhận upload")
        self.finalize_btn.clicked.connect(self._on_finalize_clicked)

        for button in (
            self.configure_btn,
            self.refresh_btn,
            self.start_btn,
            self.stop_btn,
            self.finalize_btn,
        ):
            button.setFixedWidth(150)
            action_layout.addWidget(button)
        action_layout.addStretch(1)
        root.addWidget(action_frame)

        self.state_banner = QLabel()
        self.state_banner.setObjectName("stateBanner")
        self.state_banner.setVisible(False)

        self.action_notice = QLabel("")
        self.action_notice.setObjectName("inlineNotice")
        self.action_notice.setWordWrap(True)
        self.action_notice.setVisible(False)
        root.addWidget(self.action_notice)

        summary_frame = QFrame()
        summary_frame.setObjectName("summaryStrip")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 6, 10, 6)
        self.summary_label = QLabel("-")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        root.addWidget(summary_frame)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        root.addWidget(self.main_splitter, 1)

        queue_group = QGroupBox("Danh sách hồ sơ")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setContentsMargins(10, 10, 10, 10)
        queue_layout.setSpacing(10)
        self.main_splitter.addWidget(queue_group)

        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Tìm số công chứng"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nhập số công chứng hoặc record id")
        self.search_input.textChanged.connect(self._apply_queue_filters)
        filter_layout.addWidget(self.search_input, 1)

        filter_layout.addWidget(QLabel("Trạng thái"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("Tất cả", "all")
        self.status_filter.addItem("Chờ upload", "extracted")
        self.status_filter.addItem("Lỗi upload", "upload_failed")
        self.status_filter.addItem("Chờ rà soát", "prepared_dry_run")
        self.status_filter.addItem("Thiếu trường", "prepared_partial")
        self.status_filter.addItem("Đã xác nhận", "uploaded_success")
        self.status_filter.currentIndexChanged.connect(self._apply_queue_filters)
        filter_layout.addWidget(self.status_filter)

        self.only_partial_check = QCheckBox("Chỉ hồ sơ partial/lỗi")
        self.only_partial_check.toggled.connect(self._apply_queue_filters)
        filter_layout.addWidget(self.only_partial_check)

        self.only_selected_check = QCheckBox("Chỉ hồ sơ đã chọn")
        self.only_selected_check.toggled.connect(self._apply_queue_filters)
        filter_layout.addWidget(self.only_selected_check)
        queue_layout.addWidget(filter_frame)

        self.queue_table = RecordsTableWidget(mode="queue")
        self.queue_table.current_record_changed.connect(self._handle_current_record_changed)
        self.queue_table.open_source_requested.connect(self.open_source_requested.emit)
        self.queue_table.checked_record_ids_changed.connect(self._handle_checked_records_changed)
        queue_layout.addWidget(self.queue_table)
        self.main_splitter.addWidget(queue_group)

        self.bottom_tabs = QTabWidget()
        self.main_splitter.addWidget(self.bottom_tabs)

        duplicate_group = QWidget()
        duplicate_layout = QVBoxLayout(duplicate_group)
        duplicate_layout.setContentsMargins(10, 10, 10, 10)
        self.duplicate_table = RecordsTableWidget(mode="duplicate")
        self.duplicate_table.open_source_requested.connect(self.open_source_requested.emit)
        duplicate_layout.addWidget(self.duplicate_table)
        self.bottom_tabs.addTab(duplicate_group, "Hồ sơ trùng trên web")

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_content = QWidget()
        detail_layout = QVBoxLayout(detail_content)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        detail_scroll.setWidget(detail_content)
        self.main_splitter.addWidget(detail_scroll)

        detail_group = QGroupBox("Chi tiết hồ sơ")
        detail_group_layout = QVBoxLayout(detail_group)
        detail_group_layout.setContentsMargins(12, 12, 12, 12)
        detail_group_layout.setSpacing(10)
        self.detail_hint = QLabel("Chọn một hồ sơ trong danh sách để xem chi tiết.")
        self.detail_hint.setWordWrap(True)
        detail_group_layout.addWidget(self.detail_hint)

        overview_frame = QFrame()
        overview_layout = QGridLayout(overview_frame)
        overview_layout.setHorizontalSpacing(10)
        overview_layout.setVerticalSpacing(6)
        self.overview_labels: dict[str, QLabel] = {}
        overview_fields = [
            ("record_id", "Record ID"),
            ("contract_no", "Số công chứng"),
            ("status", "Trạng thái"),
            ("reason", "Diễn giải"),
            ("prepared_at", "Prepared"),
            ("source_file", "File gốc"),
            ("last_error", "Lỗi gần nhất"),
        ]
        for row_index, (key, label) in enumerate(overview_fields):
            overview_layout.addWidget(QLabel(label), row_index, 0)
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            overview_layout.addWidget(value_label, row_index, 1)
            self.overview_labels[key] = value_label
        detail_group_layout.addWidget(overview_frame)

        verify_group = QGroupBox("Đối chiếu")
        verify_layout = QVBoxLayout(verify_group)
        self.verify_view = QTextEdit()
        self.verify_view.setReadOnly(True)
        self.verify_view.setMinimumHeight(170)
        verify_layout.addWidget(self.verify_view)
        detail_group_layout.addWidget(verify_group)

        upload_form_group = QGroupBox("Upload form")
        upload_form_layout = QVBoxLayout(upload_form_group)
        self.upload_form_view = QTextEdit()
        self.upload_form_view.setReadOnly(True)
        self.upload_form_view.setMinimumHeight(180)
        upload_form_layout.addWidget(self.upload_form_view)
        detail_group_layout.addWidget(upload_form_group)

        attachments_group = QGroupBox("Tệp đính kèm")
        attachments_layout = QVBoxLayout(attachments_group)
        attachment_row = QHBoxLayout()
        attachment_row.setSpacing(8)
        self.open_source_btn = QPushButton("Mở file gốc")
        self.open_source_btn.clicked.connect(self._emit_open_source)
        attachment_row.addWidget(self.open_source_btn)
        self.open_screenshot_btn = QPushButton("Mở screenshot")
        self.open_screenshot_btn.clicked.connect(lambda: self._emit_open_path("screenshot"))
        attachment_row.addWidget(self.open_screenshot_btn)
        self.open_debug_btn = QPushButton("Mở debug JSON")
        self.open_debug_btn.clicked.connect(lambda: self._emit_open_path("debug_json"))
        attachment_row.addWidget(self.open_debug_btn)
        self.open_artifact_btn = QPushButton("Mở artifact")
        self.open_artifact_btn.clicked.connect(lambda: self._emit_open_path("artifact_dir"))
        attachment_row.addWidget(self.open_artifact_btn)
        attachment_row.addStretch(1)
        attachments_layout.addLayout(attachment_row)
        self.attachment_hint = QLabel("-")
        self.attachment_hint.setWordWrap(True)
        attachments_layout.addWidget(self.attachment_hint)
        detail_group_layout.addWidget(attachments_group)

        notes_group = QGroupBox("Ghi chú vận hành")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Ghi chú này chỉ sống trong phiên chạy hiện tại.")
        self.notes_edit.textChanged.connect(self._store_current_note)
        notes_layout.addWidget(self.notes_edit)
        detail_group_layout.addWidget(notes_group)

        detail_layout.addWidget(detail_group)
        detail_layout.addStretch(1)
        self.bottom_tabs.addTab(detail_scroll, "Chi tiết hồ sơ")
        self.bottom_tabs.setCurrentIndex(0)
        self.bottom_tabs.setMaximumHeight(170)
        self.main_splitter.setSizes([560, 120])
        self._clear_record_detail()

    def _apply_queue_filters(self) -> None:
        self.queue_table.set_filters(
            self.search_input.text(),
            str(self.status_filter.currentData()),
            self.only_partial_check.isChecked(),
            self.only_selected_check.isChecked(),
        )
        if self.queue_table.proxy_model.rowCount() == 0:
            self._current_record_id = None
            self._clear_record_detail()

    def _handle_current_record_changed(self, record_id: int) -> None:
        self._save_note_for_record(self._current_record_id)
        self._current_record_id = record_id if record_id > 0 else None
        row = self._queue_rows.get(record_id)
        if row is None:
            self._clear_record_detail()
            return
        self._populate_record_detail(row)

    def _handle_checked_records_changed(self, record_ids: list[int]) -> None:
        for record_id, row in list(self._queue_rows.items()):
            row["selected"] = record_id in record_ids
        self.finalize_btn.setText(f"Xác nhận upload ({len(record_ids)})")
        if self.only_selected_check.isChecked():
            self._apply_queue_filters()

    def _save_note_for_record(self, record_id: int | None) -> None:
        if record_id is None:
            return
        self._record_notes[record_id] = self.notes_edit.toPlainText()

    def _store_current_note(self) -> None:
        if self._current_record_id is None:
            return
        self._record_notes[self._current_record_id] = self.notes_edit.toPlainText()

    def _emit_open_source(self) -> None:
        if self._current_record_id is not None:
            self.open_source_requested.emit(self._current_record_id)

    def _emit_open_path(self, key: str) -> None:
        if self._current_record_id is None:
            return
        row = self._queue_rows.get(self._current_record_id)
        if not row:
            return
        path = str(row.get(key, "") or "")
        if path:
            self.open_path_requested.emit(path)

    def _populate_record_detail(self, row: dict[str, Any]) -> None:
        self.detail_hint.setText("Rà soát kỹ phần đối chiếu trước khi xác nhận đã upload.")
        self.overview_labels["record_id"].setText(str(row.get("record_id", "-")))
        self.overview_labels["contract_no"].setText(str(row.get("contract_no", "-")))
        self.overview_labels["status"].setText(str(row.get("status_text", row.get("status", "-"))))
        self.overview_labels["reason"].setText(str(row.get("reason", "-") or "-"))
        self.overview_labels["prepared_at"].setText(str(row.get("prepared_at", "-") or "-"))
        self.overview_labels["source_file"].setText(str(row.get("source_file", "-") or "-"))
        self.overview_labels["last_error"].setText(str(row.get("last_error", "-") or "-"))

        verify = row.get("verify") or {}
        self.verify_view.setHtml(self._render_verify_html(verify, row))
        self.upload_form_view.setPlainText(
            json.dumps(row.get("upload_form") or {}, ensure_ascii=False, indent=2)
        )

        notes = self._record_notes.get(int(row["record_id"]), "")
        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(notes)
        self.notes_edit.blockSignals(False)

        attachment_lines = []
        for key, label in (
            ("artifact_dir", "Artifact"),
            ("screenshot", "Screenshot"),
            ("debug_json", "Debug JSON"),
        ):
            value = str(row.get(key, "") or "")
            attachment_lines.append(f"{label}: {value or '(không có)'}")
        self.attachment_hint.setText("\n".join(attachment_lines))

        self.open_source_btn.setEnabled(True)
        self.open_artifact_btn.setEnabled(bool(row.get("artifact_dir")))
        self.open_screenshot_btn.setEnabled(bool(row.get("screenshot")))
        self.open_debug_btn.setEnabled(bool(row.get("debug_json")))

    def _render_verify_html(self, verify: dict[str, Any], row: dict[str, Any]) -> str:
        fields = dict(verify.get("fields") or {})
        warnings = list(verify.get("warnings") or verify.get("missing_fields") or [])
        lines = ["<div style='font-size:10pt'>"]
        if warnings:
            warning_items = "".join(f"<li>{warning}</li>" for warning in warnings)
            lines.append(
                "<div style='margin-bottom:8px; color:#7f6000;'><b>Cảnh báo</b><ul>"
                f"{warning_items}</ul></div>"
            )
        if not fields:
            lines.append("<div>Chưa có dữ liệu verify. Kiểm tra thêm ở phần upload form.</div>")
        else:
            lines.append("<table width='100%' cellspacing='0' cellpadding='4'>")
            lines.append(
                "<tr><th align='left'>Trường</th><th align='left'>Expected</th>"
                "<th align='left'>Actual</th><th align='left'>Kết quả</th></tr>"
            )
            for field_name, payload in fields.items():
                expected = payload.get("expected", "")
                actual = payload.get("actual", "")
                success = bool(payload.get("success"))
                status_text = "OK" if success else "Thiếu/khác"
                status_color = "#38761d" if success else "#a61c00"
                lines.append(
                    "<tr>"
                    f"<td><b>{field_name}</b></td>"
                    f"<td>{expected}</td>"
                    f"<td>{actual}</td>"
                    f"<td style='color:{status_color};'><b>{status_text}</b></td>"
                    "</tr>"
                )
            lines.append("</table>")
        missing_fields = row.get("missing_fields") or []
        if missing_fields:
            lines.append(
                "<div style='margin-top:8px; color:#7f6000;'><b>Thiếu trường:</b> "
                + ", ".join(str(item) for item in missing_fields)
                + "</div>"
            )
        lines.append("</div>")
        return "".join(lines)

    def _clear_record_detail(self) -> None:
        self.detail_hint.setText("Chọn một hồ sơ trong danh sách để xem chi tiết.")
        for label in self.overview_labels.values():
            label.setText("-")
        self.verify_view.clear()
        self.upload_form_view.clear()
        self.notes_edit.blockSignals(True)
        self.notes_edit.clear()
        self.notes_edit.blockSignals(False)
        self.attachment_hint.setText("-")
        for button in (
            self.open_source_btn,
            self.open_screenshot_btn,
            self.open_debug_btn,
            self.open_artifact_btn,
        ):
            button.setEnabled(False)

    def _on_download_clicked(self) -> None:
        from_date = self.from_date_input.text().strip()
        to_date = self.to_date_input.text().strip()
        if not from_date or not to_date:
            self.set_export_notice("Vui lòng nhập đủ Từ ngày và Đến ngày trước khi tải danh sách từ web.", level="warning")
            return
        self.clear_export_notice()
        self.clear_notice()
        self.download_web_export.emit((from_date, to_date))

    def _on_start_clicked(self) -> None:
        manifest = self.get_manifest_path()
        if not manifest:
            self.set_manifest_notice("Vui lòng chọn file manifest trước khi upload.", level="warning")
            return
        self.clear_manifest_notice()
        self.clear_notice()
        self.start_upload.emit(manifest)

    def _on_finalize_clicked(self) -> None:
        record_ids = self.get_checked_record_ids()
        if not record_ids:
            self.show_notice("Vui lòng tick ít nhất một hồ sơ trước khi xác nhận upload.", level="warning")
            return
        self.clear_notice()
        self.finalize_records.emit(record_ids)

    def show_notice(self, text: str, *, level: str = "info") -> None:
        if level not in {"warning", "error"} or not text:
            self.clear_notice()
            return
        self.action_notice.setText(text)
        self.action_notice.setProperty("noticeLevel", level)
        self.action_notice.style().unpolish(self.action_notice)
        self.action_notice.style().polish(self.action_notice)
        self.action_notice.setVisible(True)

    def clear_notice(self) -> None:
        self.action_notice.clear()
        self.action_notice.setProperty("noticeLevel", "info")
        self.action_notice.style().unpolish(self.action_notice)
        self.action_notice.style().polish(self.action_notice)
        self.action_notice.setVisible(False)

    def set_manifest_notice(self, text: str, *, level: str = "warning") -> None:
        self.manifest_notice.setText(text)
        self.manifest_notice.setProperty("noticeLevel", level)
        self.manifest_notice.style().unpolish(self.manifest_notice)
        self.manifest_notice.style().polish(self.manifest_notice)
        self.manifest_notice.setVisible(bool(text))

    def clear_manifest_notice(self) -> None:
        self.manifest_notice.clear()
        self.manifest_notice.setProperty("noticeLevel", "info")
        self.manifest_notice.style().unpolish(self.manifest_notice)
        self.manifest_notice.style().polish(self.manifest_notice)
        self.manifest_notice.setVisible(False)

    def set_export_notice(self, text: str, *, level: str = "warning") -> None:
        self.export_notice.setText(text)
        self.export_notice.setProperty("noticeLevel", level)
        self.export_notice.style().unpolish(self.export_notice)
        self.export_notice.style().polish(self.export_notice)
        self.export_notice.setVisible(bool(text))

    def clear_export_notice(self) -> None:
        self.export_notice.clear()
        self.export_notice.setProperty("noticeLevel", "info")
        self.export_notice.style().unpolish(self.export_notice)
        self.export_notice.style().polish(self.export_notice)
        self.export_notice.setVisible(False)

    def get_manifest_path(self) -> str:
        return self.manifest_browser.get_file_path()

    def set_manifest_path(self, path: str) -> None:
        self.manifest_browser.set_file_path(path)

    def get_export_path(self) -> str:
        return self.export_browser.get_file_path()

    def set_export_path(self, path: str) -> None:
        self.export_browser.set_file_path(path)

    def set_date_range(self, from_date: str, to_date: str) -> None:
        self.from_date_input.setText(from_date)
        self.to_date_input.setText(to_date)

    def set_runtime_status(self, text: str, ready: bool) -> None:
        self._runtime_ready = ready
        self.runtime_label.setText(text)
        self.runtime_label.setProperty("noticeLevel", "warning" if not ready else "info")
        self.runtime_label.style().unpolish(self.runtime_label)
        self.runtime_label.style().polish(self.runtime_label)
        self.runtime_label.setVisible(not ready)
        self._apply_button_state()

    def set_compare_status(self, text: str, loaded: bool) -> None:
        self._compare_loaded = loaded
        self.compare_label.setText(text)
        self.compare_label.setProperty("noticeLevel", "warning" if not loaded else "info")
        self.compare_label.style().unpolish(self.compare_label)
        self.compare_label.style().polish(self.compare_label)
        self.compare_label.setVisible(bool(text) and not loaded and bool(self.get_export_path()))
        self._apply_button_state()

    def set_summary(self, summary: dict[str, Any]) -> None:
        manifest_name = str(summary.get("manifest_name", "-") or "-")
        run_id = str(summary.get("run_id", "-") or "-")
        pending = str(summary.get("pending_count", "-") or "-")
        remaining = str(summary.get("remaining_count", "-") or "-")
        status_counts = str(summary.get("status_counts", "-") or "-")
        chunk = str(summary.get("prepared_last_chunk", "-") or "-")
        self.summary_label.setText(
            f"Manifest: {manifest_name} | Run: {run_id} | Hồ sơ: {pending} | Còn lại: {remaining} | Chunk: {chunk} | {status_counts}"
        )

    def load_queue_records(self, rows: list[dict[str, Any]]) -> None:
        self._queue_rows = {int(row["record_id"]): dict(row) for row in rows}
        self.queue_table.load_records(rows)
        if not rows:
            self._current_record_id = None
            self._clear_record_detail()
        self._apply_queue_filters()

    def load_duplicate_records(self, rows: list[dict[str, Any]]) -> None:
        self._duplicate_rows = {int(row["record_id"]): dict(row) for row in rows}
        self.duplicate_table.load_records(rows)

    def get_checked_record_ids(self) -> list[int]:
        return self.queue_table.get_selected_record_ids()

    def get_splitter_sizes(self) -> list[int]:
        return [int(size) for size in self.main_splitter.sizes()]

    def set_splitter_sizes(self, sizes: list[int]) -> None:
        if sizes:
            self.main_splitter.setSizes([int(size) for size in sizes])

    def set_ui_state(self, state: str) -> None:
        self._state = state
        self.state_banner.setText(STATE_MESSAGES.get(state, state))
        self.state_banner.setProperty("uiState", state)
        self.state_banner.style().unpolish(self.state_banner)
        self.state_banner.style().polish(self.state_banner)
        self._apply_button_state()

    def _apply_button_state(self) -> None:
        has_manifest = bool(self.get_manifest_path())
        checked_count = len(self.get_checked_record_ids())
        is_running = self._state == "dry_run_running"

        self.configure_btn.setEnabled(True)
        self.refresh_btn.setEnabled(has_manifest and not is_running)
        self.download_btn.setEnabled(self._runtime_ready and not is_running)
        self.start_btn.setEnabled(
            has_manifest
            and not is_running
            and self._runtime_ready
            and self._compare_loaded
            and self._state not in {"loading_queue", "no_manifest"}
        )
        self.stop_btn.setEnabled(is_running)
        self.finalize_btn.setEnabled(checked_count > 0 and not is_running)
