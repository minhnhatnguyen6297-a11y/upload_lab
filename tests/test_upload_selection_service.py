from __future__ import annotations

import unittest

from ui.services.scan_classification_service import ClassifiedScanRow
from ui.services.upload_selection_service import UploadSelection


def row(record_id: int, *, selected: bool = True) -> ClassifiedScanRow:
    return ClassifiedScanRow(
        record_id=record_id,
        contract_no=f"{record_id}/2026/CCGD",
        normalized_contract_no=f"{record_id}/2026",
        status="extracted",
        source_file=f"{record_id}.docx",
        missing_fields=(),
        selected=selected,
        reason="Hop le de upload.",
    )


class UploadSelectionServiceTests(unittest.TestCase):
    def test_defaults_to_valid_row_selection(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])

        self.assertEqual(selection.selected_record_ids(), [1, 2])

    def test_can_unselect_one_row(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])
        selection.set_selected(2, False)

        self.assertEqual(selection.selected_record_ids(), [1])

    def test_select_all_valid_does_not_include_invalid_ids(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])
        selection.set_selected(99, True)
        selection.select_all_valid()

        self.assertEqual(selection.selected_record_ids(), [1, 2])

    def test_clear_deselects_all_valid_rows(self):
        selection = UploadSelection.from_valid_rows([row(1), row(2)])
        selection.clear()

        self.assertEqual(selection.selected_record_ids(), [])


if __name__ == "__main__":
    unittest.main()
