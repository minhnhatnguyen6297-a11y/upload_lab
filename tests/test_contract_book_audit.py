from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from ui.services.contract_book_audit import (
    ContractBookWarningKind,
    analyze_contract_book,
    parse_contract_book_no,
    parse_contract_date,
)


class ContractBookAuditTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def _make_book(self, rows: list[tuple[object, object]]) -> Path:
        path = self.root / "book.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SO CONG CHUNG"
        sheet["B1"] = "NGAY, THANG, NAM CONG CHUNG"
        for index, (contract_no, date_value) in enumerate(rows, start=2):
            sheet.cell(row=index, column=1).value = contract_no
            sheet.cell(row=index, column=2).value = date_value
        workbook.save(path)
        workbook.close()
        return path

    def test_parse_contract_book_no_supports_common_forms(self):
        self.assertEqual(parse_contract_book_no("01/2026"), (2026, 1, "1/2026"))
        self.assertEqual(parse_contract_book_no("09/2026/CCGD"), (2026, 9, "9/2026"))
        self.assertEqual(parse_contract_book_no("10.2025"), (2025, 10, "10/2025"))
        self.assertEqual(parse_contract_book_no("123", default_year=2026), (2026, 123, "123/2026"))

    def test_parse_contract_date_supports_strings_and_excel_values(self):
        self.assertEqual(parse_contract_date("05/01/2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date("05-01-2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(date(2026, 1, 5)), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(datetime(2026, 1, 5, 14, 30)), date(2026, 1, 5))

    def test_analyze_contract_book_uses_min_to_max_ordinal_only(self):
        path = self._make_book([
            ("01/2026", "05/01/2026"),
            ("03/2026/CCGD", "05/01/2026"),
            ("5", "06/01/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertEqual([row.ordinal for row in analysis.valid_rows], [1, 3, 5])
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026", "4/2026"])
        self.assertEqual(analysis.min_ordinal, 1)
        self.assertEqual(analysis.max_ordinal, 5)

    def test_warns_for_unparseable_column_a(self):
        path = self._make_book([
            ("Nguyen Van A", "05/01/2026"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertEqual(len(analysis.parse_error_rows), 1)
        self.assertEqual(analysis.parse_error_rows[0].row_index, 2)
        self.assertEqual(analysis.parse_error_rows[0].raw_contract_no, "Nguyen Van A")
        self.assertEqual(analysis.parse_error_rows[0].kind, ContractBookWarningKind.PARSE_ERROR)

    def test_warns_when_date_cannot_be_parsed_after_contract_number(self):
        path = self._make_book([
            ("01/2026", "not a date"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.DATE_PARSE_ERROR
            and warning.row_index == 2
            for warning in analysis.warning_rows
        ))

    def test_warns_when_contract_year_disagrees_with_date_year(self):
        path = self._make_book([
            ("10.2025", "05/02/2026"),
            ("11/2026", "06/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.YEAR_MISMATCH
            and warning.row_index == 2
            for warning in analysis.warning_rows
        ))

    def test_warns_when_date_order_goes_backwards(self):
        path = self._make_book([
            ("01/2026", "06/02/2026"),
            ("02/2026", "05/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.DATE_ORDER
            and warning.row_index == 3
            for warning in analysis.warning_rows
        ))

    def test_warns_when_ordinal_order_goes_backwards(self):
        path = self._make_book([
            ("05/2026", "05/02/2026"),
            ("04/2026", "05/02/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertTrue(any(
            warning.kind == ContractBookWarningKind.ORDINAL_ORDER
            and warning.row_index == 3
            for warning in analysis.warning_rows
        ))

    def test_skips_header_row_when_column_a_looks_like_contract_header(self):
        path = self._make_book([
            ("SO CONG CHUNG", "NGAY, THANG, NAM CONG CHUNG"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path)

        self.assertEqual([row.row_index for row in analysis.valid_rows], [3])


if __name__ == "__main__":
    unittest.main()
