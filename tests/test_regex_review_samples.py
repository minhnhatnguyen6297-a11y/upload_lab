from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docx import Document

from review_regex_samples import run_review


def make_docx(path: Path, *paragraphs: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(str(path))
    return path


class RegexReviewSamplesTests(unittest.TestCase):
    def test_run_review_writes_ai_readable_report(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            input_dir = root / "input"
            reports_dir = root / "reports"
            make_docx(
                input_dir / "sample.docx",
                "HOP DONG CHUYEN NHUONG QUYEN SU DUNG DAT",
                "I. BEN CHUYEN NHUONG",
                "Ong: Tran Van A Sinh ngay: 01/01/1980",
                "Can cuoc cong dan so: 036080000001 do Bo Cong an cap ngay 01/01/2024;",
                "Thuong tru tai: xa A, tinh B.",
                "II. BEN NHAN CHUYEN NHUONG",
                "Ba: Nguyen Thi B Sinh ngay: 02/02/1982",
                "Can cuoc cong dan so: 036182000002 do Bo Cong an cap ngay 02/02/2024;",
                "Thuong tru tai: xa C, tinh D.",
                "quyen su dung dat cua ben A co dia chi tai: xa A, tinh B.",
                "- Thua dat so: 10",
                "So cong chung 405/2026/CCGD",
            )

            report_path = run_review(input_dir=input_dir, reports_dir=reports_dir)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report_path.with_suffix(".xlsx").exists())
            self.assertEqual(len(payload["files"]), 1)
            item = payload["files"][0]
            self.assertEqual(item["file"], "sample.docx")
            self.assertIn("document_kind", item)
            self.assertIn("so_cong_chung", item)
            self.assertIn("nguoi_yeu_cau", item)
            self.assertIn("duong_su", item)
            self.assertIn("tai_san", item)
            self.assertIn("missing_fields", item)
            self.assertIn("raw_excerpt", item)

    def test_run_review_scans_nested_sample_folders(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            input_dir = root / "input"
            reports_dir = root / "reports"
            make_docx(
                input_dir / "transfer" / "case-01" / "sample.docx",
                "HOP DONG CHUYEN NHUONG QUYEN SU DUNG DAT",
                "So cong chung 406/2026/CCGD",
            )

            report_path = run_review(input_dir=input_dir, reports_dir=reports_dir)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["files"][0]["file"], "transfer/case-01/sample.docx")

    def test_run_review_skips_word_temp_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            input_dir = root / "input"
            reports_dir = root / "reports"
            make_docx(input_dir / "~$temp.docx", "So cong chung 407/2026/CCGD")
            make_docx(input_dir / "real.docx", "So cong chung 408/2026/CCGD")

            report_path = run_review(input_dir=input_dir, reports_dir=reports_dir)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual([item["file"] for item in payload["files"]], ["real.docx"])


if __name__ == "__main__":
    unittest.main()
