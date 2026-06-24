from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest

from ui.services.contract_book_audit import ContractBookAnalysis, ContractBookRow
from ui.services.scan_classification_service import classify_scan_records


@dataclass(frozen=True)
class FakeRecord:
    record_id: int
    contract_no: str
    status: str
    source_file: Path
    missing_fields: list[str]


class ScanClassificationServiceTests(unittest.TestCase):
    def _analysis(self) -> ContractBookAnalysis:
        rows = [
            ContractBookRow(2, "1/2026", "05/01/2026", "1/2026", 2026, 1, None),
            ContractBookRow(3, "2/2026", "05/01/2026", "2/2026", 2026, 2, None),
        ]
        return ContractBookAnalysis(Path("book.xlsx"), rows, [], [], [], 1, 2)

    def test_without_excel_lists_all_folder_rows_and_selects_none(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "9/2026/CCGD", "extracted", Path("b.docx"), ["tai_san"]),
            ],
            None,
        )

        self.assertEqual([row.record_id for row in result.folder_rows], [10, 11])
        self.assertEqual([row.selected for row in result.folder_rows], [False, False])
        self.assertEqual(result.missing_in_excel_record_ids, set())
        self.assertIn("chua load Excel", result.folder_rows[0].note)
        self.assertIn("missing: tai_san", result.folder_rows[1].note)

    def test_with_excel_selects_numbers_missing_from_excel_by_default(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "9/2026/CCGD", "extracted", Path("b.docx"), []),
                FakeRecord(12, "2/2026/CCGD", "extracted", Path("c.docx"), ["tai_san"]),
            ],
            self._analysis(),
        )

        self.assertEqual([row.record_id for row in result.folder_rows], [10, 11, 12])
        self.assertEqual([row.selected for row in result.folder_rows], [False, True, False])
        self.assertEqual(result.missing_in_excel_record_ids, {11})
        self.assertIn("da co trong Excel", result.folder_rows[0].note)
        self.assertIn("chua co trong Excel", result.folder_rows[1].note)
        self.assertIn("missing: tai_san", result.folder_rows[2].note)

    def test_missing_fields_and_local_duplicates_are_notes_not_blockers(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "9/2026/CCGD", "extracted", Path("a.docx"), ["tai_san"]),
                FakeRecord(11, "9/2026/CCGD", "extracted", Path("b.docx"), []),
            ],
            self._analysis(),
        )

        self.assertEqual([row.record_id for row in result.folder_rows], [10, 11])
        self.assertEqual([row.selected for row in result.folder_rows], [True, True])
        self.assertEqual(result.missing_in_excel_record_ids, {10, 11})
        self.assertIn("missing: tai_san", result.folder_rows[0].note)
        self.assertIn("trung trong folder", result.folder_rows[0].note)
        self.assertIn("trung trong folder", result.folder_rows[1].note)

    def test_blank_contract_number_is_never_auto_selected_as_missing_excel(self):
        result = classify_scan_records(
            [FakeRecord(10, "", "extracted", Path("a.docx"), [])],
            self._analysis(),
        )

        self.assertEqual([row.record_id for row in result.folder_rows], [10])
        self.assertEqual(result.folder_rows[0].selected, False)
        self.assertEqual(result.missing_in_excel_record_ids, set())
        self.assertIn("khong co so", result.folder_rows[0].note)

    def test_leading_zero_scan_number_matches_excel_canonical_contract(self):
        result = classify_scan_records(
            [FakeRecord(10, "01/2026/CCGD", "extracted", Path("a.docx"), [])],
            self._analysis(),
        )

        self.assertEqual(result.folder_rows[0].normalized_contract_no, "1/2026")
        self.assertEqual(result.folder_rows[0].selected, False)
        self.assertIn("da co trong Excel", result.folder_rows[0].note)

    def test_bad_format_and_wrong_year_folder_numbers_are_marked_as_issues(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1572/2025/VBTT/CCGD", "extracted", Path("old.docx"), []),
                FakeRecord(11, "2042026/CCGD", "extracted", Path("bad.docx"), []),
                FakeRecord(12, "9/2026/CCGD", "extracted", Path("ok.docx"), []),
            ],
            self._analysis(),
        )

        rows = {row.record_id: row for row in result.folder_rows}
        self.assertTrue(rows[10].has_issue)
        self.assertFalse(rows[10].selected)
        self.assertIn("sai nam", rows[10].note)
        self.assertTrue(rows[11].has_issue)
        self.assertFalse(rows[11].selected)
        self.assertIn("sai format", rows[11].note)
        self.assertFalse(rows[12].has_issue)
        self.assertTrue(rows[12].selected)


if __name__ == "__main__":
    unittest.main()
