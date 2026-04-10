"""Record table widget used by the upload tab."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QRect, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)


STATUS_TEXT = {
    "extracted": "Chờ upload",
    "upload_failed": "Lỗi upload",
    "prepared_dry_run": "Chờ rà soát",
    "prepared_partial": "Thiếu trường",
    "uploaded_success": "Đã xác nhận",
}

STATUS_COLORS = {
    "extracted": ("#0b5394", "#eaf2fb"),
    "upload_failed": ("#a61c00", "#fdecea"),
    "prepared_dry_run": ("#38761d", "#edf6ea"),
    "prepared_partial": ("#7f6000", "#fff3dd"),
    "uploaded_success": ("#155724", "#e4f5e7"),
}

ROW_TINTS = {
    "upload_failed": "#fff4f2",
    "prepared_partial": "#fffaf0",
    "prepared_dry_run": "#f5fbf2",
}

QUEUE_COLUMNS: list[dict[str, Any]] = [
    {"key": "selected", "title": "", "width": 36, "checkable": True},
    {"key": "record_id", "title": "Record ID", "width": 82},
    {"key": "contract_no", "title": "Số công chứng", "width": 155},
    {"key": "status", "title": "Trạng thái", "width": 128},
    {"key": "missing_fields", "title": "Thiếu trường", "width": 180},
    {"key": "prepared_at", "title": "Prepared", "width": 145},
    {"key": "last_error", "title": "Lỗi gần nhất", "width": 240},
    {"key": "source_file", "title": "File gốc", "width": 430, "resize_mode": "stretch"},
]

DUPLICATE_COLUMNS: list[dict[str, Any]] = [
    {"key": "record_id", "title": "Record ID", "width": 82},
    {"key": "contract_no", "title": "Số công chứng", "width": 155},
    {"key": "status", "title": "Trạng thái local", "width": 128},
    {"key": "source_file", "title": "File gốc", "width": 420},
]


class StatusBadgeDelegate(QStyledItemDelegate):
    """Paint a colored badge for the status column."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if not index.isValid():
            return

        painter.save()
        row = index.data(Qt.ItemDataRole.UserRole) or {}
        status = str(row.get("status", ""))
        label = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        fg_hex, bg_hex = STATUS_COLORS.get(status, ("#333333", "#f2f2f2"))

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            background = row.get("_row_tint")
            if background:
                painter.fillRect(option.rect, QColor(str(background)))

        badge_rect = option.rect.adjusted(8, 6, -8, -6)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg_hex))
        painter.drawRoundedRect(badge_rect, 8, 8)
        painter.setPen(QPen(QColor(fg_hex)))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()


class RecordsTableModel(QAbstractTableModel):
    """Source model for queue and duplicate tables."""

    selection_state_changed = pyqtSignal(list)

    def __init__(self, columns: list[dict[str, Any]], parent=None) -> None:
        super().__init__(parent)
        self.columns = columns
        self.rows: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.columns[section]["title"]
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        column = self.columns[index.column()]
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if column.get("checkable"):
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        column = self.columns[index.column()]
        key = column["key"]
        value = row.get(key)

        if role == Qt.ItemDataRole.UserRole:
            return row
        if role == Qt.ItemDataRole.CheckStateRole and column.get("checkable"):
            return Qt.CheckState.Checked if bool(value) else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            if column.get("checkable"):
                return ""
            if key == "status":
                return STATUS_TEXT.get(str(value), str(value or ""))
            if key == "missing_fields":
                if isinstance(value, list):
                    return ", ".join(str(item) for item in value)
                return str(value or "")
            if key == "prepared_at":
                text = str(value or "")
                return text.replace("T", " ") if text else ""
            return str(value or "")
        if role == Qt.ItemDataRole.ToolTipRole:
            if key == "missing_fields" and isinstance(value, list):
                return "\n".join(str(item) for item in value) if value else "Không thiếu trường"
            if key == "last_error":
                return str(value or "")
            if key == "source_file":
                return str(value or "")
        if role == Qt.ItemDataRole.TextAlignmentRole and key in {"record_id", "prepared_at"}:
            return int(Qt.AlignmentFlag.AlignCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if key == "last_error" and value:
                return QColor("#a61c00")
            if key == "missing_fields" and row.get("needs_manual_review"):
                return QColor("#7f6000")
        if role == Qt.ItemDataRole.BackgroundRole:
            tint = row.get("_row_tint")
            if tint and key != "status":
                return QColor(str(tint))
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if key == "contract_no":
                font.setBold(True)
                return font
            if key == "last_error" and value:
                font.setItalic(True)
                return font
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        column = self.columns[index.column()]
        if not column.get("checkable") or role != Qt.ItemDataRole.CheckStateRole:
            return False
        row = self.rows[index.row()]
        row["selected"] = value == Qt.CheckState.Checked
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.DisplayRole])
        self.selection_state_changed.emit(self.get_checked_record_ids())
        return True

    def load_rows(self, rows: list[dict[str, Any]]) -> None:
        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            normalized = dict(row)
            normalized.setdefault("selected", False)
            status = str(normalized.get("status", ""))
            normalized["_row_tint"] = ROW_TINTS.get(status, "")
            normalized_rows.append(normalized)
        self.beginResetModel()
        self.rows = normalized_rows
        self.endResetModel()
        self.selection_state_changed.emit(self.get_checked_record_ids())

    def row_at(self, row_index: int) -> dict[str, Any]:
        return self.rows[row_index]

    def get_checked_record_ids(self) -> list[int]:
        return [
            int(row["record_id"])
            for row in self.rows
            if row.get("selected") and str(row.get("record_id", "")).strip()
        ]

    def get_row_by_record_id(self, record_id: int) -> dict[str, Any] | None:
        for row in self.rows:
            if int(row.get("record_id", -1)) == int(record_id):
                return row
        return None


class RecordsFilterProxyModel(QSortFilterProxyModel):
    """Filter proxy for queue tables."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.search_text = ""
        self.status_filter = "all"
        self.only_partial = False
        self.only_selected = False

    def set_filters(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        only_partial: bool = False,
        only_selected: bool = False,
    ) -> None:
        self.search_text = search_text.strip().lower()
        self.status_filter = status_filter
        self.only_partial = only_partial
        self.only_selected = only_selected
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        row = model.row_at(source_row)
        if self.search_text:
            haystack = " ".join(
                [
                    str(row.get("contract_no", "")),
                    str(row.get("source_file", "")),
                    str(row.get("record_id", "")),
                ]
            ).lower()
            if self.search_text not in haystack:
                return False
        if self.status_filter and self.status_filter != "all":
            if str(row.get("status", "")) != self.status_filter:
                return False
        if self.only_partial:
            needs_review = bool(row.get("needs_manual_review"))
            if not needs_review:
                return False
        if self.only_selected and not bool(row.get("selected")):
            return False
        return True


class RecordsTableWidget(QWidget):
    """Wrapper around QTableView with sorting and filtering support."""

    current_record_changed = pyqtSignal(int)
    open_source_requested = pyqtSignal(int)
    checked_record_ids_changed = pyqtSignal(list)

    def __init__(self, parent=None, *, mode: str = "queue") -> None:
        super().__init__(parent)
        self.columns = QUEUE_COLUMNS if mode == "queue" else DUPLICATE_COLUMNS
        self.mode = mode
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableView()
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)
        layout.addWidget(self.table)

        self.model = RecordsTableModel(self.columns, self)
        self.proxy_model = RecordsFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.table.setModel(self.proxy_model)
        self._selection_model = None

        for column_index, column in enumerate(self.columns):
            self.table.setColumnWidth(column_index, int(column.get("width", 120)))
            if column["key"] == "status":
                self.table.setItemDelegateForColumn(column_index, StatusBadgeDelegate(self.table))
            resize_mode = QHeaderView.ResizeMode.Fixed
            if column.get("resize_mode") == "stretch" or column_index == len(self.columns) - 1:
                resize_mode = QHeaderView.ResizeMode.Stretch
            self.table.horizontalHeader().setSectionResizeMode(column_index, resize_mode)

        self.table.doubleClicked.connect(self._handle_double_click)
        self.model.selection_state_changed.connect(self.checked_record_ids_changed.emit)

    def _connect_selection_model(self) -> None:
        selection_model = self.table.selectionModel()
        if selection_model is None or selection_model is self._selection_model:
            return
        if self._selection_model is not None:
            try:
                self._selection_model.currentRowChanged.disconnect(self._handle_current_row_changed)
            except Exception:
                pass
        selection_model.currentRowChanged.connect(self._handle_current_row_changed)
        self._selection_model = selection_model

    def _handle_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        source_index = self.proxy_model.mapToSource(current)
        row = self.model.row_at(source_index.row())
        self.current_record_changed.emit(int(row.get("record_id", -1)))

    def _handle_double_click(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        row = self.model.row_at(source_index.row())
        self.open_source_requested.emit(int(row.get("record_id", -1)))

    def load_records(self, rows: list[dict[str, Any]]) -> None:
        self.model.load_rows(rows)
        self._connect_selection_model()
        self.table.sortByColumn(1 if self.mode == "queue" else 0, Qt.SortOrder.AscendingOrder)
        if self.proxy_model.rowCount() > 0:
            self.table.selectRow(0)
            first_index = self.proxy_model.index(0, 0)
            self._handle_current_row_changed(first_index, QModelIndex())

    def clear_table(self) -> None:
        self.model.load_rows([])

    def set_filters(
        self,
        search_text: str = "",
        status_filter: str = "all",
        only_partial: bool = False,
        only_selected: bool = False,
    ) -> None:
        self.proxy_model.set_filters(
            search_text=search_text,
            status_filter=status_filter,
            only_partial=only_partial,
            only_selected=only_selected,
        )
        if self.proxy_model.rowCount() > 0:
            self.table.selectRow(0)
            self._handle_current_row_changed(self.proxy_model.index(0, 0), QModelIndex())

    def get_selected_record_ids(self) -> list[int]:
        return self.model.get_checked_record_ids()

    def get_row_by_record_id(self, record_id: int) -> dict[str, Any] | None:
        return self.model.get_row_by_record_id(record_id)

    def set_record_checked(self, record_id: int, selected: bool) -> None:
        for row_index, row in enumerate(self.model.rows):
            if int(row.get("record_id", -1)) != int(record_id):
                continue
            model_index = self.model.index(row_index, 0)
            state = Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked
            self.model.setData(model_index, state, Qt.ItemDataRole.CheckStateRole)
            break
