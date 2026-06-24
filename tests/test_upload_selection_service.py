from __future__ import annotations

import unittest

from ui.services.scan_classification_service import FolderScanRow
from ui.services.upload_selection_service import UploadSelection


def row(record_id: int, *, selected: bool = False) -> FolderScanRow:
    return FolderScanRow(
        record_id=record_id,
        contract_no=f"{record_id}/2026/CCGD",
        normalized_contract_no=f"{record_id}/2026",
        status="extracted",
        source_file=f"{record_id}.docx",
        missing_fields=[],
        selected=selected,
        note="",
    )


class UploadSelectionServiceTests(unittest.TestCase):
    def test_defaults_to_rows_marked_selected(self):
        selection = UploadSelection.from_rows([row(1), row(2, selected=True)])

        self.assertEqual(selection.selected_record_ids(), [2])

    def test_can_select_one_known_row(self):
        selection = UploadSelection.from_rows([row(1), row(2)])
        selection.set_selected(2, True)

        self.assertEqual(selection.selected_record_ids(), [2])

    def test_can_unselect_using_string_record_id(self):
        selection = UploadSelection.from_rows([row(1, selected=True), row(2, selected=True)])
        selection.set_selected("2", False)

        self.assertEqual(selection.selected_record_ids(), [1])

    def test_select_all_includes_all_folder_rows(self):
        selection = UploadSelection.from_rows([row(1), row(2, selected=True)])
        selection.select_all()

        self.assertEqual(selection.selected_record_ids(), [1, 2])

    def test_select_only_missing_excel_ids_ignores_unknown_ids(self):
        selection = UploadSelection.from_rows([row(1), row(2), row(3)])
        selection.select_only({2, 99})

        self.assertEqual(selection.selected_record_ids(), [2])

    def test_clear_deselects_all_rows(self):
        selection = UploadSelection.from_rows([row(1, selected=True), row(2, selected=True)])
        selection.clear()

        self.assertEqual(selection.selected_record_ids(), [])


if __name__ == "__main__":
    unittest.main()
