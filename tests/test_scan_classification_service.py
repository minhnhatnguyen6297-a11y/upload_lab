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

    def test_classifies_valid_match_and_defaults_selected(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "9/2026/CCGD", "extracted", Path("b.docx"), []),
                FakeRecord(12, "2/2026/CCGD", "extracted", Path("c.docx"), ["tai_san"]),
            ],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.valid_upload_rows], [10])
        self.assertEqual(result.valid_upload_rows[0].selected, True)
        self.assertEqual([row.record_id for row in result.not_in_excel_rows], [11])
        self.assertEqual([row.record_id for row in result.missing_field_rows], [12])

    def test_classifies_web_duplicates(self):
        result = classify_scan_records(
            [FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), [])],
            self._analysis(),
            existing_web_contract_nos={"1/2026"},
        )

        self.assertEqual([row.record_id for row in result.web_duplicate_rows], [10])
        self.assertEqual(result.valid_upload_rows, [])

    def test_classifies_web_duplicate_before_not_in_excel(self):
        result = classify_scan_records(
            [FakeRecord(10, "9/2026/CCGD", "extracted", Path("a.docx"), [])],
            self._analysis(),
            existing_web_contract_nos={"9/2026"},
        )

        self.assertEqual([row.record_id for row in result.web_duplicate_rows], [10])
        self.assertEqual(result.not_in_excel_rows, [])
        self.assertEqual(result.valid_upload_rows, [])

    def test_classifies_local_duplicates_after_first_valid_row(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "1/2026/CCGD", "extracted", Path("b.docx"), []),
            ],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.valid_upload_rows], [10])
        self.assertEqual([row.record_id for row in result.duplicate_local_rows], [11])

    def test_classifies_local_duplicates_after_missing_field_row(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), ["tai_san"]),
                FakeRecord(11, "1/2026/CCGD", "extracted", Path("b.docx"), []),
            ],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.missing_field_rows], [10])
        self.assertEqual([row.record_id for row in result.duplicate_local_rows], [11])
        self.assertEqual(result.valid_upload_rows, [])

    def test_missing_field_row_counts_as_found_in_folder_for_excel_missing(self):
        result = classify_scan_records(
            [FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), ["tai_san"])],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.missing_field_rows], [10])
        self.assertEqual(result.excel_missing_in_folder, ["2/2026"])

    def test_leading_zero_scan_number_matches_excel_canonical_contract(self):
        result = classify_scan_records(
            [FakeRecord(10, "01/2026/CCGD", "extracted", Path("a.docx"), [])],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual([row.record_id for row in result.valid_upload_rows], [10])
        self.assertEqual(result.valid_upload_rows[0].contract_no, "01/2026/CCGD")
        self.assertEqual(result.valid_upload_rows[0].normalized_contract_no, "1/2026")
        self.assertEqual(result.not_in_excel_rows, [])

    def test_reports_excel_numbers_missing_from_valid_scan_rows(self):
        result = classify_scan_records(
            [
                FakeRecord(10, "1/2026/CCGD", "extracted", Path("a.docx"), []),
                FakeRecord(11, "2/2026/CCGD", "extracted", Path("b.docx"), ["tai_san"]),
                FakeRecord(12, "9/2026/CCGD", "extracted", Path("c.docx"), []),
            ],
            self._analysis(),
            existing_web_contract_nos=set(),
        )

        self.assertEqual(result.excel_missing_in_folder, [])
        self.assertEqual([row.record_id for row in result.valid_upload_rows], [10])


if __name__ == "__main__":
    unittest.main()
