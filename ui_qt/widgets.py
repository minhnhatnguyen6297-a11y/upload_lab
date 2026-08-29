from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


def open_with_windows_default(path: str) -> bool:
    file_path = Path(path)
    if not file_path.exists() or not hasattr(os, "startfile"):
        return False
    os.startfile(str(file_path))  # type: ignore[attr-defined]
    return True


def set_table_rows(
    table: QTableWidget,
    headers: list[str],
    rows: list[list[str]],
    *,
    resize_columns: bool = True,
) -> None:
    table.clear()
    table.clearContents()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            item = QTableWidgetItem(str(value))
            # Align numeric and short index columns to center
            if column_index in (0, 1) or str(value).isdigit():
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row_index, column_index, item)
    if resize_columns:
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)


def configure_audit_table_scrollbars(table: QTableWidget, *, horizontal: bool = False) -> None:
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn if horizontal else Qt.ScrollBarAsNeeded)


def set_checkable_upload_rows(table: QTableWidget, rows: list) -> None:
    headers = ["Chon", "ID", "So", "Trang thai", "Ghi chu", "File"]
    table.clear()
    table.clearContents()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))

    color_blue = QColor("#0284C7")
    color_green = QColor("#16A34A")
    color_red = QColor("#DC2626")

    for row_index, row in enumerate(rows):
        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Checked if row.selected else Qt.Unchecked)
        check_item.setData(Qt.ItemDataRole.UserRole, int(row.record_id))
        check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row_index, 0, check_item)

        id_item = QTableWidgetItem(str(row.record_id))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row_index, 1, id_item)

        so_item = QTableWidgetItem(str(row.contract_no))
        so_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        so_font = so_item.font()
        so_font.setBold(True)
        so_item.setFont(so_font)
        table.setItem(row_index, 2, so_item)

        status_item = QTableWidgetItem(str(row.status))
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row_index, 3, status_item)

        note_str = str(row.note)
        note_item = QTableWidgetItem(note_str)
        note_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        note_font = note_item.font()
        note_font.setBold(True)
        note_item.setFont(note_font)

        if "chua co" in note_str.lower():
            note_item.setForeground(QBrush(color_blue))
        elif "da co" in note_str.lower():
            note_item.setForeground(QBrush(color_green))
        elif any(err in note_str.lower() for err in ("sai", "loi", "khong")):
            note_item.setForeground(QBrush(color_red))
        table.setItem(row_index, 4, note_item)

        file_item = QTableWidgetItem(str(row.source_file))
        file_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.setItem(row_index, 5, file_item)

    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)


def checked_record_ids(table: QTableWidget) -> list[int]:
    ids: list[int] = []
    for row_index in range(table.rowCount()):
        item = table.item(row_index, 0)
        if item is not None and item.checkState() == Qt.Checked:
            record_id = item.data(Qt.ItemDataRole.UserRole)
            if record_id is not None:
                ids.append(int(record_id))
    return sorted(ids)

