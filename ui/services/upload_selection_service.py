from __future__ import annotations

from dataclasses import dataclass, field

from ui.services.scan_classification_service import ClassifiedScanRow


@dataclass
class UploadSelection:
    valid_ids: set[int] = field(default_factory=set)
    selected_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_valid_rows(cls, rows: list[ClassifiedScanRow]) -> UploadSelection:
        valid_ids = {int(row.record_id) for row in rows}
        return cls(valid_ids=valid_ids, selected_ids=set(valid_ids))

    def set_selected(self, record_id: int, selected: bool) -> None:
        if record_id not in self.valid_ids:
            return
        if selected:
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def select_all_valid(self) -> None:
        self.selected_ids = set(self.valid_ids)

    def clear(self) -> None:
        self.selected_ids.clear()

    def selected_record_ids(self) -> list[int]:
        return sorted(self.selected_ids)
