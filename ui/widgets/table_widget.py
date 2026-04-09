"""Custom table widget for displaying records."""

from typing import List, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView


class RecordsTableWidget(QTableWidget):
    """Table widget for displaying upload records."""
    
    record_double_clicked = pyqtSignal(int)  # Emits record_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = ["record_id", "contract_no", "status", "missing", "source_file"]
        self.headers = {
            "record_id": "Record ID",
            "contract_no": "Số công chứng",
            "status": "Trạng thái",
            "missing": "Missing/Partial",
            "source_file": "File gốc",
        }
        self.widths = {
            "record_id": 80,
            "contract_no": 150,
            "status": 140,
            "missing": 180,
            "source_file": 520,
        }
        self._init_ui()
    
    def _init_ui(self) -> None:
        self.setColumnCount(len(self.columns))
        self.setSelectionMode(3)  # Multi-select rows
        self.setSelectionBehavior(1)  # Select entire row
        
        # Set headers
        for col_idx, col_name in enumerate(self.columns):
            self.setHorizontalHeaderItem(col_idx, QTableWidgetItem(self.headers[col_name]))
            self.setColumnWidth(col_idx, self.widths.get(col_name, 200))
        
        # Stretch last column
        header = self.horizontalHeader()
        header.setSectionResizeMode(len(self.columns) - 1, QHeaderView.ResizeMode.Stretch)
        
        # Connect double-click
        self.itemDoubleClicked.connect(self._on_double_click)
    
    def _on_double_click(self, item: QTableWidgetItem) -> None:
        """Handle double-click on table item."""
        row = item.row()
        record_id_item = self.item(row, 0)
        if record_id_item:
            try:
                record_id = int(record_id_item.text())
                self.record_double_clicked.emit(record_id)
            except ValueError:
                pass
    
    def load_records(self, records: List[Dict[str, Any]]) -> None:
        """Load records into table."""
        self.setRowCount(len(records))
        
        for row_idx, record in enumerate(records):
            for col_idx, col_name in enumerate(self.columns):
                value = str(record.get(col_name, ""))
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(row_idx, col_idx, item)
    
    def get_selected_record_ids(self) -> List[int]:
        """Get list of selected record IDs."""
        record_ids = []
        for item in self.selectedItems():
            if item.column() == 0:  # record_id column
                try:
                    record_id = int(item.text())
                    if record_id not in record_ids:
                        record_ids.append(record_id)
                except ValueError:
                    pass
        return record_ids
    
    def clear_table(self) -> None:
        """Clear all rows."""
        self.setRowCount(0)
