from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
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
            table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
    if resize_columns:
        table.resizeColumnsToContents()


def configure_audit_table_scrollbars(table: QTableWidget, *, horizontal: bool = False) -> None:
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn if horizontal else Qt.ScrollBarAsNeeded)


def set_checkable_upload_rows(table: QTableWidget, rows: list) -> None:
    headers = ["Chon", "ID", "So", "Trang thai", "File"]
    table.clear()
    table.clearContents()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        check_item = QTableWidgetItem("")
        check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check_item.setCheckState(Qt.Checked if row.selected else Qt.Unchecked)
        check_item.setData(Qt.ItemDataRole.UserRole, int(row.record_id))
        table.setItem(row_index, 0, check_item)
        for column_index, value in enumerate(
            [row.record_id, row.contract_no, row.status, row.source_file],
            start=1,
        ):
            table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
    table.resizeColumnsToContents()


def checked_record_ids(table: QTableWidget) -> list[int]:
    ids: list[int] = []
    for row_index in range(table.rowCount()):
        item = table.item(row_index, 0)
        if item is not None and item.checkState() == Qt.Checked:
            record_id = item.data(Qt.ItemDataRole.UserRole)
            if record_id is not None:
                ids.append(int(record_id))
    return sorted(ids)
