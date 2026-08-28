from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document

import regex_lab


def make_docx(path: Path, *lines: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(str(path))
    return path


TRANSFER = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "Độc lập - Tự do - Hạnh phúc",
    "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT",
    "Chúng tôi gồm có:",
    "I. BÊN CHUYỂN NHƯỢNG: (Bên A)",
    "Ông: Nguyễn Văn A Sinh ngày: 01/01/1980",
    "II. BÊN NHẬN CHUYỂN NHƯỢNG: (Bên B)",
    "Bà: Nguyễn Thị B Sinh ngày: 02/02/1982",
    "ĐIỀU 1: ĐỐI TƯỢNG CỦA HỢP ĐỒNG",
    "Quyền sử dụng đất của bên A có địa chỉ tại: xã A, tỉnh B.",
    "- Thửa đất số: 10",
)


class RegexLabTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "input"
        self.cache = self.root / "cache"
        self.golden = self.root / "golden"
        self.packets = self.root / "packets"

    def test_ingest_reuses_hash_record(self):
        make_docx(self.input / "one.docx", *TRANSFER)
        first = regex_lab.ingest_corpus(self.input, self.cache)
        record_path = self.cache / "records" / f"{next(iter(first['records']))}.json"
        first_mtime = record_path.stat().st_mtime_ns

        second = regex_lab.ingest_corpus(self.input, self.cache)

        self.assertEqual(second["summary"]["reused_count"], 1)
        self.assertEqual(second["summary"]["extracted_count"], 0)
        self.assertEqual(record_path.stat().st_mtime_ns, first_mtime)

    def test_layout_clusters_are_deterministic(self):
        make_docx(self.input / "a.docx", *TRANSFER, "Nội dung A")
        make_docx(self.input / "b.docx", *TRANSFER, "Nội dung B")
        make_docx(self.input / "other.docx", "KÍNH GỬI: VĂN PHÒNG", "Ông: Nguyễn Văn C")

        index = regex_lab.ingest_corpus(self.input, self.cache)

        by_path = {path: index["records"][content_hash]["cluster_id"] for path, content_hash in index["paths"].items()}
        self.assertEqual(by_path["a.docx"], by_path["b.docx"])
        self.assertNotEqual(by_path["a.docx"], by_path["other.docx"])

    def test_layout_clusters_separate_document_kinds(self):
        make_docx(self.input / "transfer.docx", *TRANSFER)
        gift = list(TRANSFER)
        gift[2] = "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT"
        make_docx(self.input / "gift.docx", *gift)

        index = regex_lab.ingest_corpus(self.input, self.cache)
        by_path = {path: index["records"][content_hash]["cluster_id"] for path, content_hash in index["paths"].items()}

        self.assertNotEqual(by_path["transfer.docx"], by_path["gift.docx"])

    def test_review_packet_has_at_most_three_representatives(self):
        for number in range(4):
            make_docx(self.input / f"sample-{number}.docx", *TRANSFER, f"Mẫu {number}")

        result = regex_lab.review_corpus(self.input, self.cache, self.golden, self.packets)
        packet = Path(result["packet_dir"]) / result["packets"][0]

        self.assertLessEqual(packet.read_text(encoding="utf-8").count("\n## sample-"), 3)

    def test_approve_then_verify_and_detect_changed_extraction(self):
        make_docx(self.input / "one.docx", *TRANSFER)
        regex_lab.approve_corpus(self.input, self.cache, self.golden, approve_all=True)
        unchanged = regex_lab.verify_corpus(self.input, self.cache, self.golden)
        self.assertEqual(unchanged["summary"]["UNCHANGED"], 1)
        self.assertEqual(unchanged["exit_code"], 0)

        index_path = self.cache / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        content_hash = next(iter(index["records"]))
        record_path = self.cache / "records" / f"{content_hash}.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["extraction"]["ten_hop_dong"] = "KẾT QUẢ REGEX ĐÃ THAY ĐỔI"
        record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

        changed = regex_lab.verify_corpus(self.input, self.cache, self.golden)
        self.assertEqual(changed["summary"]["CHANGED"], 1)
        self.assertEqual(changed["exit_code"], 1)

    def test_extract_change_is_seen_when_cache_is_invalidated(self):
        make_docx(self.input / "one.docx", *TRANSFER)
        regex_lab.approve_corpus(self.input, self.cache, self.golden, approve_all=True)
        original = regex_lab.extract_contract.extract

        def changed_extract(*args, **kwargs):
            payload = original(*args, **kwargs)
            payload["web_form"]["ten_hop_dong"] = "CHANGED"
            return payload

        with patch.object(regex_lab, "_extractor_fingerprint", return_value="new-code"), patch.object(
            regex_lab.extract_contract, "extract", side_effect=changed_extract
        ):
            changed = regex_lab.verify_corpus(self.input, self.cache, self.golden)
        self.assertEqual(changed["summary"]["CHANGED"], 1)

    def test_verify_detects_removed_golden_sample(self):
        sample = make_docx(self.input / "one.docx", *TRANSFER)
        regex_lab.approve_corpus(self.input, self.cache, self.golden, approve_all=True)
        sample.unlink()

        result = regex_lab.verify_corpus(self.input, self.cache, self.golden)

        self.assertEqual(result["summary"]["REMOVED"], 1)
        self.assertEqual(result["exit_code"], 1)


if __name__ == "__main__":
    unittest.main()
