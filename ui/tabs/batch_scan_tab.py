"""Batch scan tab."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import FolderBrowserWidget, ProgressPanelWidget


class BatchScanTab(QWidget):
    """Tab for batch scanning folders."""

    run_batch_scan = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(960)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.notice_banner = QLabel()
        self.notice_banner.setObjectName("inlineNotice")
        self.notice_banner.setWordWrap(True)
        self.notice_banner.setVisible(False)
        root.addWidget(self.notice_banner)

        content_grid = QGridLayout()
        content_grid.setHorizontalSpacing(14)
        content_grid.setVerticalSpacing(14)
        content_grid.setColumnStretch(0, 1)
        content_grid.setColumnStretch(1, 1)
        root.addLayout(content_grid, 1)

        source_group = QGroupBox("Nguồn quét")
        source_group.setMinimumWidth(460)
        source_group.setMaximumHeight(126)
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(12, 12, 12, 10)
        self.folder_browser = FolderBrowserWidget(
            label_text="Thư mục tổng hồ sơ",
            button_text="Chọn thư mục",
            dialog_title="Chọn thư mục tổng hồ sơ",
            placeholder_text="Chưa chọn thư mục",
        )
        source_layout.addWidget(self.folder_browser)
        content_grid.addWidget(source_group, 0, 0)

        options_group = QGroupBox("Tùy chọn quét")
        options_group.setMinimumWidth(460)
        options_group.setMaximumHeight(150)
        options_layout = QGridLayout(options_group)
        options_layout.setHorizontalSpacing(12)
        options_layout.setVerticalSpacing(8)
        options_layout.setContentsMargins(12, 12, 12, 10)

        options_layout.addWidget(QLabel("Mốc ngày sửa"), 0, 0)
        self.modified_since_input = QLineEdit()
        self.modified_since_input.setPlaceholderText("YYYY-MM-DD")
        self.modified_since_input.setMinimumWidth(180)
        self.modified_since_input.setMaximumWidth(220)
        options_layout.addWidget(self.modified_since_input, 0, 1)

        options_layout.addWidget(QLabel("Độ sâu quét"), 0, 2)
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setMinimum(1)
        self.max_depth_spin.setMaximum(10)
        self.max_depth_spin.setValue(3)
        self.max_depth_spin.setMaximumWidth(90)
        options_layout.addWidget(self.max_depth_spin, 0, 3)

        self.full_rescan_check = QCheckBox("Quét lại toàn bộ, bỏ qua mốc ngày")
        options_layout.addWidget(self.full_rescan_check, 1, 0, 1, 4)
        options_layout.setColumnStretch(1, 1)
        options_layout.setColumnStretch(4, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)
        action_row.setSpacing(10)
        self.run_btn = QPushButton("Quét hồ sơ")
        self.run_btn.setMinimumWidth(150)
        self.run_btn.clicked.connect(self._on_run_clicked)
        action_row.addWidget(self.run_btn)
        action_row.addStretch()
        options_layout.addLayout(action_row, 2, 0, 1, 5)
        content_grid.addWidget(options_group, 1, 0)

        progress_group = QGroupBox("Tiến độ quét")
        progress_group.setMinimumWidth(460)
        progress_group.setMaximumHeight(150)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(12, 12, 12, 10)
        progress_layout.setSpacing(6)
        progress_header = QHBoxLayout()
        progress_header.addStretch()
        self.progress_toggle = QToolButton()
        self.progress_toggle.setText("Ẩn")
        self.progress_toggle.setCheckable(True)
        self.progress_toggle.toggled.connect(self._toggle_progress_panel)
        progress_header.addWidget(self.progress_toggle)
        progress_layout.addLayout(progress_header)

        self.progress_container = QFrame()
        container_layout = QVBoxLayout(self.progress_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_panel = ProgressPanelWidget()
        self.progress_panel.setMinimumHeight(92)
        container_layout.addWidget(self.progress_panel)
        progress_layout.addWidget(self.progress_container)
        content_grid.addWidget(progress_group, 0, 1)

        result_group = QGroupBox("Kết quả")
        result_group.setMinimumWidth(460)
        result_group.setMaximumHeight(150)
        result_layout = QGridLayout(result_group)
        result_layout.setHorizontalSpacing(12)
        result_layout.setVerticalSpacing(8)
        result_layout.setContentsMargins(12, 12, 12, 10)

        result_layout.addWidget(QLabel("Manifest"), 0, 0)
        self.manifest_display = QLineEdit()
        self.manifest_display.setReadOnly(True)
        self.manifest_display.setMinimumWidth(340)
        result_layout.addWidget(self.manifest_display, 0, 1)

        result_layout.addWidget(QLabel("Thư mục output"), 1, 0)
        self.output_display = QLineEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setMinimumWidth(340)
        result_layout.addWidget(self.output_display, 1, 1)

        result_layout.addWidget(QLabel("Tóm tắt"), 2, 0)
        self.stats_display = QLineEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setMinimumWidth(340)
        result_layout.addWidget(self.stats_display, 2, 1)
        result_layout.setColumnStretch(1, 1)
        content_grid.addWidget(result_group, 1, 1)
        content_grid.setRowStretch(2, 1)

    def _toggle_progress_panel(self, collapsed: bool) -> None:
        self.progress_container.setVisible(not collapsed)
        self.progress_toggle.setText("Hiện" if collapsed else "Ẩn")

    def _on_run_clicked(self) -> None:
        folder = self.folder_browser.get_folder_path()
        if not folder:
            self.show_notice("Vui lòng chọn thư mục tổng hồ sơ trước khi quét.", level="warning")
            return

        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            self.show_notice("Thư mục đã chọn không còn tồn tại hoặc không hợp lệ. Hãy chọn lại.", level="warning")
            return

        config = {
            "folder": str(folder_path),
            "modified_since": self.modified_since_input.text().strip() or None,
            "full_rescan": self.full_rescan_check.isChecked(),
            "max_depth": self.max_depth_spin.value(),
        }
        self.clear_notice()
        self.run_btn.setEnabled(False)
        self.progress_toggle.setChecked(False)
        self.progress_panel.reset()
        self.run_batch_scan.emit(config)

    def set_progress(self, progress: int) -> None:
        self.progress_panel.set_progress(progress)

    def set_status(self, status: str) -> None:
        self.progress_panel.set_status(status)

    def set_detail(self, detail: str) -> None:
        self.progress_panel.set_detail(detail)

    def set_file(self, file_path: str) -> None:
        self.progress_panel.set_file(file_path)

    def set_results(self, manifest_path: str, output_folder: str, stats: str) -> None:
        self.manifest_display.setText(manifest_path)
        self.manifest_display.setCursorPosition(0)
        self.output_display.setText(output_folder)
        self.output_display.setCursorPosition(0)
        self.stats_display.setText(stats)
        self.stats_display.setCursorPosition(0)

    def enable_run_button(self, enabled: bool = True) -> None:
        self.run_btn.setEnabled(enabled)

    def show_notice(self, text: str, *, level: str = "info") -> None:
        self.notice_banner.setText(text)
        self.notice_banner.setProperty("noticeLevel", level)
        self.notice_banner.style().unpolish(self.notice_banner)
        self.notice_banner.style().polish(self.notice_banner)
        self.notice_banner.setVisible(bool(text))

    def clear_notice(self) -> None:
        self.notice_banner.clear()
        self.notice_banner.setProperty("noticeLevel", "info")
        self.notice_banner.style().unpolish(self.notice_banner)
        self.notice_banner.style().polish(self.notice_banner)
        self.notice_banner.setVisible(False)
