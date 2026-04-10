from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

import ui.main_window as main_window_module


class PyQt6SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.workdir = Path(self.tempdir.name)
        QSettings(main_window_module.SETTINGS_ORG, main_window_module.SETTINGS_APP).clear()
        self.manifest_path = self.workdir / "runs" / "manifest.json"
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps({"run_id": "run-ui"}), encoding="utf-8")
        self.export_path = self.workdir / "downloads" / "so_cong_chung.xlsx"
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        self.export_path.write_text("stub", encoding="utf-8")

        artifact_dir = self.workdir / "upload_runs" / "demo_run"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "before_save_128_2026_CCGD.png").write_text("img", encoding="utf-8")
        (artifact_dir / "debug_128_2026_CCGD.json").write_text("{}", encoding="utf-8")

        def make_record(record_id: int, contract_no: str, status: str, *, missing_fields: list[str] | None = None):
            source_file = self.workdir / f"{record_id}.docx"
            source_file.write_text("dummy", encoding="utf-8")
            upload_form = {
                "so_cong_chung": contract_no.replace("/CCGD", ""),
                "ten_hop_dong": "Hợp đồng demo",
                "nhom_hop_dong": "Chuyển nhượng",
                "loai_tai_san": "" if missing_fields else "Đất ở",
                "tai_san": "" if missing_fields else "Thửa đất 12",
                "file_hop_dong": str(source_file),
            }
            raw_row = {
                "reason": "Seed data",
                "last_error": "" if status != "prepared_partial" else "Thiếu trường quan trọng",
                "prepared_at": "2026-04-08T09:35:14",
                "artifact_dir": str(artifact_dir),
                "verify_json": json.dumps(
                    {
                        "warnings": ["Missing critical field: tai_san"] if missing_fields else [],
                        "fields": {
                            "so_cong_chung": {
                                "expected": contract_no.replace("/CCGD", ""),
                                "actual": contract_no.replace("/CCGD", ""),
                                "success": True,
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
            }
            return SimpleNamespace(
                record_id=record_id,
                contract_no=contract_no,
                status=status,
                source_file=source_file,
                upload_form=upload_form,
                missing_fields=missing_fields or [],
                raw_row=raw_row,
            )

        self.records = [
            make_record(101, "128/2026/CCGD", "prepared_dry_run"),
            make_record(102, "147/2026/CCGD", "prepared_partial", missing_fields=["tai_san"]),
            make_record(103, "300/2026/CCGD", "extracted"),
        ]

        self.patches = [
            patch.object(main_window_module, "probe_playwright_runtime", return_value=(True, "Playwright sẵn sàng")),
            patch.object(
                main_window_module,
                "get_uploader_setup_status",
                return_value={"ready": True, "message": "Uploader đã sẵn sàng.", "values": {}},
            ),
            patch.object(main_window_module, "load_requester_contract_lookup", return_value=({}, None)),
            patch.object(main_window_module, "load_upload_queue", return_value=({"run_id": "run-ui"}, self.records, 3)),
            patch.object(main_window_module, "read_exported_contract_numbers", return_value={"300/2026"}),
        ]
        for active_patch in self.patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

        self.window = main_window_module.MainWindow(working_dir=self.workdir)
        self.addCleanup(self.window.close)
        self.app.processEvents()

    def test_main_window_smoke_flow(self):
        self.assertEqual(self.window.tabs.count(), 2)
        self.assertEqual(self.window.upload_tab._state, "no_manifest")
        self.assertTrue(self.window.log_viewer.is_collapsed())
        self.assertGreaterEqual(self.window.minimumWidth(), 980)
        self.assertGreaterEqual(self.window.batch_tab.minimumWidth(), 960)
        self.assertIn("docs.google.com", self.window.upload_tab.get_requester_sheet_url())

        self.window.upload_tab.set_manifest_path(str(self.manifest_path))
        self.window.upload_tab.set_export_path(str(self.export_path))
        self.app.processEvents()

        self.assertEqual(self.window.upload_tab._state, "has_partial")
        self.assertIn("Manifest:", self.window.upload_tab.summary_label.text())
        self.assertEqual(self.window.upload_tab.queue_table.proxy_model.rowCount(), 2)
        self.assertEqual(self.window.upload_tab.duplicate_table.proxy_model.rowCount(), 1)
        self.assertEqual(self.window.upload_tab.overview_labels["record_id"].text(), "101")
        self.assertEqual(self.window.upload_tab.start_btn.text(), "Upload")

        self.window.upload_tab.queue_table.set_record_checked(101, True)
        self.app.processEvents()
        self.assertIn("(1)", self.window.upload_tab.finalize_btn.text())

        self.window.upload_tab.search_input.setText("147/2026")
        self.app.processEvents()
        self.assertEqual(self.window.upload_tab.queue_table.proxy_model.rowCount(), 1)
        self.assertEqual(self.window.upload_tab.overview_labels["record_id"].text(), "102")

    def test_batch_finished_auto_applies_manifest_to_upload(self):
        self.window.upload_tab.set_export_path(str(self.export_path))
        self.app.processEvents()

        self.window._on_batch_finished(
            {
                "manifest_path": str(self.manifest_path),
                "stats": {
                    "processed_files": 3,
                    "total_supported_files": 3,
                    "candidates_found": 3,
                    "extract_success": 3,
                    "extract_partial": 0,
                    "extract_failed": 0,
                },
            }
        )
        self.app.processEvents()

        self.assertEqual(self.window.upload_tab.get_manifest_path(), str(self.manifest_path))
        self.assertEqual(self.window.upload_tab.queue_table.proxy_model.rowCount(), 2)
        self.assertIn(self.manifest_path.name, self.window.upload_tab.summary_label.text())

    def test_export_downloaded_auto_sets_compare_file(self):
        export_path_2 = self.workdir / "downloads" / "tu_web.xlsx"
        export_path_2.write_text("stub", encoding="utf-8")

        self.window.upload_tab.set_manifest_path(str(self.manifest_path))
        self.app.processEvents()

        self.window._on_export_downloaded(str(export_path_2))
        self.app.processEvents()

        self.assertEqual(self.window.upload_tab.get_export_path(), str(export_path_2))
        self.assertFalse(self.window.upload_tab.export_notice.isVisible())


if __name__ == "__main__":
    unittest.main()
