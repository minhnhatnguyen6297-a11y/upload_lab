from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from ui.services.web_list_service import (
    find_missing_contract_numbers,
    lookup_exported_contract_no,
    read_exported_contract_rows,
)


class WebListServiceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def _make_export(self, *values: object) -> Path:
        export_path = self.root / "so_cong_chung.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SO CONG CHUNG"
        for row_index, value in enumerate(values, start=2):
            sheet.cell(row=row_index, column=1).value = value
        workbook.save(export_path)
        workbook.close()
        return export_path

    def test_find_missing_contract_numbers_uses_min_max_by_year(self):
        rows = read_exported_contract_rows(self._make_export("405/2026", "407/2026/CCGD", "410/2026"))

        missing = find_missing_contract_numbers(rows)

        self.assertEqual([item.contract_no for item in missing], ["406/2026", "408/2026", "409/2026"])

    def test_lookup_exported_contract_no_accepts_full_suffix_and_spacing(self):
        rows = read_exported_contract_rows(self._make_export("405/2026"))

        result = lookup_exported_contract_no(rows, " 405/2026/CCGD ")

        self.assertTrue(result.found)
        self.assertEqual(result.contract_no, "405/2026")
        self.assertEqual(result.row_index, 2)

    def test_web_list_service_does_not_require_folder_or_manifest(self):
        rows = read_exported_contract_rows(self._make_export("100/2025", "101/2025"))
        missing = find_missing_contract_numbers(rows)
        result = lookup_exported_contract_no(rows, "100/2025")

        self.assertEqual(missing, [])
        self.assertTrue(result.found)


if __name__ == "__main__":
    unittest.main()
