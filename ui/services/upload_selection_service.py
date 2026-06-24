from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ui.services.scan_classification_service import FolderScanRow


@dataclass
class UploadSelection:
    row_ids: set[int] = field(default_factory=set)
    selected_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_rows(cls, rows: list[FolderScanRow]) -> UploadSelection:
        row_ids = {int(row.record_id) for row in rows}
        selected_ids = {int(row.record_id) for row in rows if row.selected}
        return cls(row_ids=row_ids, selected_ids=selected_ids)

    def set_selected(self, record_id: int | str, selected: bool) -> None:
        record_id = int(record_id)
        if record_id not in self.row_ids:
            return
        if selected:
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def select_all(self) -> None:
        self.selected_ids = set(self.row_ids)

    def select_only(self, record_ids: Iterable[int]) -> None:
        requested_ids = {int(record_id) for record_id in record_ids}
        self.selected_ids = self.row_ids & requested_ids

    def clear(self) -> None:
        self.selected_ids.clear()

    def selected_record_ids(self) -> list[int]:
        return sorted(self.selected_ids)
