from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from ui.services.contract_book_audit import (
    ContractBookIssueKind,
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

    def test_parse_contract_book_no_accepts_only_slash_year_forms(self):
        self.assertEqual(parse_contract_book_no("001/2026"), (2026, 1, "1/2026"))
        self.assertEqual(parse_contract_book_no("09/2026/CCGD"), (2026, 9, "9/2026"))
        self.assertIsNone(parse_contract_book_no("66.2026"))
        self.assertIsNone(parse_contract_book_no("123", default_year=2026))

    def test_parse_contract_date_supports_strings_and_excel_values(self):
        self.assertEqual(parse_contract_date("05/01/2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date("05-01-2026"), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(date(2026, 1, 5)), date(2026, 1, 5))
        self.assertEqual(parse_contract_date(datetime(2026, 1, 5, 14, 30)), date(2026, 1, 5))

    def test_missing_uses_clean_rows_only(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], ["1/2026", "3/2026"])
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026"])
        self.assertEqual([item.note for item in analysis.missing_numbers], ["Thieu that"])
        self.assertEqual(analysis.summary.valid_count, 2)
        self.assertEqual(analysis.summary.missing_count, 1)

    def test_wrong_year_and_bad_format_do_not_create_missing_for_other_years(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
            ("296/2025", "02/01/2026"),
            ("2047.2025", "02/01/2026"),
            ("344/2006", "02/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026"])
        self.assertEqual(
            [(issue.raw_contract_no, issue.kind) for issue in analysis.issue_rows],
            [
                ("296/2025", ContractBookIssueKind.WRONG_YEAR),
                ("2047.2025", ContractBookIssueKind.BAD_FORMAT),
                ("344/2006", ContractBookIssueKind.WRONG_YEAR),
            ],
        )

    def test_duplicate_numbers_move_all_duplicate_rows_to_issues(self):
        path = self._make_book([
            ("59/2026", "01/01/2026"),
            ("60/2026", "01/01/2026"),
            ("060/2026/CCGD", "01/01/2026"),
            ("61/2026", "01/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], ["59/2026", "61/2026"])
        duplicate_issues = [issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.DUPLICATE]
        self.assertEqual([issue.contract_no for issue in duplicate_issues], ["60/2026", "60/2026"])
        self.assertEqual(analysis.summary.duplicate_count, 2)
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["60/2026"])
        self.assertEqual([item.note for item in analysis.missing_numbers], ["Co trong vung loi: trung_so"])

    def test_dates_that_move_back_and_forth_do_not_create_date_issues(self):
        path = self._make_book([
            ("8/2026", "08/01/2026"),
            ("9/2026", "06/01/2026"),
            ("10/2026", "06/01/2026"),
            ("11/2026", "07/01/2026"),
            ("12/2026", "07/01/2026"),
            ("13/2026", "07/01/2026"),
            ("14/2026", "07/01/2026"),
            ("15/2026", "07/01/2026"),
            ("16/2026", "07/01/2026"),
            ("17/2026", "07/01/2026"),
            ("18/2026", "07/01/2026"),
            ("19/2026", "07/01/2026"),
            ("20/2026", "07/01/2026"),
            ("21/2026", "08/01/2026"),
            ("22/2026", "08/01/2026"),
            ("23/2026", "08/01/2026"),
            ("24/2026", "08/01/2026"),
            ("25/2026", "08/01/2026"),
            ("26/2026", "08/01/2026"),
            ("27/2026", "08/01/2026"),
            ("28/2026", "08/01/2026"),
            ("29/2026", "08/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], [f"{ordinal}/2026" for ordinal in range(8, 30)])
        self.assertEqual(analysis.issue_rows, [])
        self.assertEqual(analysis.missing_numbers, [])

    def test_invalid_date_stays_in_issue_rows_and_out_of_missing_notes(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("2/2026", "khong hop le"),
            ("3/2026", "01/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.contract_no for row in analysis.display_rows], ["1/2026", "3/2026"])
        self.assertEqual([item.contract_no for item in analysis.missing_numbers], ["2/2026"])
        self.assertEqual([item.note for item in analysis.missing_numbers], ["Co trong vung loi: ngay_khong_hop_le"])
        self.assertEqual(
            [(issue.contract_no, issue.kind) for issue in analysis.issue_rows],
            [("2/2026", ContractBookIssueKind.DATE_PARSE_ERROR)],
        )

    def test_skips_header_row_when_column_a_looks_like_contract_header(self):
        path = self._make_book([
            ("SO CONG CHUNG", "NGAY, THANG, NAM CONG CHUNG"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.row_index for row in analysis.display_rows], [3])


if __name__ == "__main__":
    unittest.main()
