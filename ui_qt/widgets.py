from __future__ import annotations

import os
from pathlib import Path

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
