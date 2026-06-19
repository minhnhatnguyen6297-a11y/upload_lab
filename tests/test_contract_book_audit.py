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

    def test_later_number_with_earlier_date_is_date_sequence_issue(self):
        path = self._make_book([
            ("1/2026", "02/01/2026"),
            ("2/2026", "03/01/2026"),
            ("3/2026", "01/01/2026"),
            ("4/2026", "04/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        issue = next(issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.DATE_SEQUENCE)
        self.assertEqual(issue.contract_no, "3/2026")
        self.assertEqual([row.contract_no for row in analysis.display_rows], ["1/2026", "2/2026", "4/2026"])

    def test_same_day_jump_over_ten_moves_later_row_to_issue(self):
        path = self._make_book([
            ("1/2026", "01/01/2026"),
            ("2/2026", "01/01/2026"),
            ("3/2026", "01/01/2026"),
            ("20/2026", "01/01/2026"),
            ("21/2026", "02/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        issue = next(issue for issue in analysis.issue_rows if issue.kind == ContractBookIssueKind.SAME_DAY_JUMP)
        self.assertEqual(issue.contract_no, "20/2026")
        self.assertNotIn("20/2026", [row.contract_no for row in analysis.display_rows])
        self.assertNotIn("20/2026", [item.contract_no for item in analysis.missing_numbers])

    def test_skips_header_row_when_column_a_looks_like_contract_header(self):
        path = self._make_book([
            ("SO CONG CHUNG", "NGAY, THANG, NAM CONG CHUNG"),
            ("01/2026", "05/01/2026"),
        ])

        analysis = analyze_contract_book(path, from_date="01/01/2026", to_date="18/06/2026")

        self.assertEqual([row.row_index for row in analysis.display_rows], [3])


if __name__ == "__main__":
    unittest.main()
