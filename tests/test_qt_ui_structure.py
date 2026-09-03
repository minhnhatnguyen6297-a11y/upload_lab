from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pathlib import Path

from openpyxl import Workbook

import bootstrap_ui


class QtUIStructureTests(unittest.TestCase):
    def test_pyside6_dependency_declared(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("PySide6", requirements)

    def test_qt_package_files_exist(self):
        self.assertTrue(Path("ui_qt").is_dir())
        self.assertTrue(Path("ui_qt/__init__.py").exists())
        self.assertTrue(Path("ui_qt/app.py").exists())
        self.assertTrue(Path("ui_qt/main_window.py").exists())
        self.assertTrue(Path("ui_qt/widgets.py").exists())
        self.assertTrue(Path("ui_qt/workers.py").exists())

    def test_qt_entrypoint_imports(self):
        from ui_qt.app import run_qt_app
        from ui_qt.main_window import UploadLabMainWindow

        self.assertTrue(callable(run_qt_app))
        self.assertEqual(UploadLabMainWindow.__name__, "UploadLabMainWindow")

    def test_ui_runner_uses_qt_entrypoint(self):
        import ui_runner

        with patch.object(ui_runner, "run_qt_app", return_value=123) as mocked_run_qt_app:
            self.assertEqual(ui_runner.main(), 123)
            mocked_run_qt_app.assert_called_once_with()

    def test_qt_main_window_loads_ui_and_preserves_working_dir(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir) / "working-dir-check"
            window = UploadLabMainWindow(working_dir=working_dir)

            self.assertEqual(window.windowTitle(), "Upload Lab")
            self.assertIsNotNone(window.centralWidget())
            self.assertTrue(hasattr(window, "ui"))
            self.assertIs(window.ui, window.centralWidget())
            self.assertEqual(window.centralWidget().objectName(), "centralWidget")
            self.assertEqual(window.ui.objectName(), "centralWidget")
            self.assertEqual(window.working_dir, working_dir)
            self.assertIsNotNone(app)

    def test_excel_tab_widgets_exist(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QLineEdit, QPushButton, QProgressBar, QTabWidget, QTableWidget

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()

        widget_checks = [
            ("fromDateEdit", QLineEdit),
            ("toDateEdit", QLineEdit),
            ("excelPathEdit", QLineEdit),
            ("configureUploaderButton", QPushButton),
            ("downloadExcelButton", QPushButton),
            ("browseExcelButton", QPushButton),
            ("loadExcelButton", QPushButton),
            ("excelSummaryLabel", QLabel),
            ("excelDisplayTable", QTableWidget),
            ("excelMissingTable", QTableWidget),
            ("excelIssueTable", QTableWidget),
            ("folderPathEdit", QLineEdit),
            ("browseFolderButton", QPushButton),
            ("scanFolderButton", QPushButton),
            ("scanProgressBar", QProgressBar),
            ("scanSummaryLabel", QLabel),
            ("scanResultTabs", QTabWidget),
            ("folderNumbersTable", QTableWidget),
            ("selectAllValidButton", QPushButton),
            ("clearValidSelectionButton", QPushButton),
            ("filterIssueNumbersButton", QPushButton),
            ("selectMissingExcelButton", QPushButton),
            ("uploadSelectedButton", QPushButton),
            ("continueUploadButton", QPushButton),
            ("closeUploadBrowserButton", QPushButton),
            ("notaryComboBox", QComboBox),
            ("secretaryEdit", QLineEdit),
            ("refreshStaffOptionsButton", QPushButton),
            ("uploadProgressBar", QProgressBar),
            ("uploadProgressLabel", QLabel),
            ("stopUploadButton", QPushButton),
        ]

        for name, widget_type in widget_checks:
            with self.subTest(name=name):
                widget = window.ui.findChild(widget_type, name)
                self.assertIsNotNone(widget)
                self.assertIsInstance(widget, widget_type)

        for table in (window.excelDisplayTable, window.excelMissingTable, window.excelIssueTable):
            self.assertEqual(table.verticalScrollBarPolicy(), Qt.ScrollBarAlwaysOn)
            self.assertEqual(table.editTriggers(), table.EditTrigger.NoEditTriggers)
        self.assertEqual(window.excelIssueTable.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOn)
        self.assertEqual(
            [window.excelMissingTable.horizontalHeaderItem(index).text() for index in range(window.excelMissingTable.columnCount())],
            ["So thieu", "Nam", "STT", "Chu thich"],
        )
        self.assertEqual(window.scanResultTabs.count(), 1)
        self.assertEqual(window.scanResultTabs.tabText(0), "Cac so trong folder")
        self.assertIsNotNone(app)

    def test_folder_number_selection_controls_follow_checkbox_state(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        from ui.services.scan_classification_service import FolderScanRow, ScanClassification
        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        classification = ScanClassification(
            folder_rows=[
                FolderScanRow(10, "10/2026/CCGD", "10/2026", "extracted", "a.docx", [], False, "da co trong Excel", False),
                FolderScanRow(11, "11/2026/CCGD", "11/2026", "extracted", "b.docx", [], True, "chua co trong Excel", False),
            ],
            missing_in_excel_record_ids={11},
            has_excel=True,
        )

        window.render_scan_classification(classification)

        self.assertEqual(window.folderNumbersTable.rowCount(), 2)
        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [11])
        self.assertTrue(window.selectAllValidButton.isEnabled())
        self.assertTrue(window.clearValidSelectionButton.isEnabled())
        self.assertFalse(window.filterIssueNumbersButton.isEnabled())
        self.assertTrue(window.selectMissingExcelButton.isEnabled())
        self.assertTrue(window.uploadSelectedButton.isEnabled())
        self.assertEqual(window.uploadSelectedButton.text(), "Upload file da chon (1)")
        self.assertEqual(window.folderNumbersTable.item(0, 4).text(), "chua co trong Excel")
        self.assertEqual(window.folderNumbersTable.item(1, 4).text(), "da co trong Excel")

        selected_item = window.folderNumbersTable.item(0, 0)
        selected_item.setCheckState(Qt.Unchecked)

        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [])
        self.assertEqual(window.uploadSelectedButton.text(), "Upload file da chon (0)")

        window.clear_folder_selection()
        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [])
        self.assertEqual(window.folderNumbersTable.item(1, 0).checkState(), Qt.Unchecked)
        self.assertFalse(window.uploadSelectedButton.isEnabled())
        self.assertEqual(window.uploadSelectedButton.text(), "Upload file da chon (0)")

        window.select_all_folder_rows()
        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [10, 11])
        self.assertEqual(window.folderNumbersTable.item(0, 0).checkState(), Qt.Checked)
        self.assertTrue(window.uploadSelectedButton.isEnabled())
        self.assertEqual(window.uploadSelectedButton.text(), "Upload file da chon (2)")

        window.select_missing_excel_rows()
        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [11])
        self.assertEqual(window.folderNumbersTable.item(0, 0).checkState(), Qt.Checked)
        self.assertIsNotNone(app)

    def test_filter_issue_numbers_toggles_selection_and_selected_rows_render_first(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        from ui.services.scan_classification_service import FolderScanRow, ScanClassification
        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        classification = ScanClassification(
            folder_rows=[
                FolderScanRow(10, "1572/2025/VBTT/CCGD", "1572/2025", "extracted", "old.docx", [], True, "sai nam", True),
                FolderScanRow(11, "9/2026/CCGD", "9/2026", "extracted", "ok.docx", [], True, "chua co trong Excel", False),
                FolderScanRow(12, "204/2026/CCGD", "204/2026", "extracted", "bad.docx", [], True, "sai format", True),
            ],
            missing_in_excel_record_ids={10, 11, 12},
            has_excel=True,
        )

        window.render_scan_classification(classification)

        self.assertEqual([window.folderNumbersTable.item(row, 1).text() for row in range(3)], ["10", "11", "12"])

        window.filter_issue_numbers()

        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [11])
        self.assertEqual(window.folderNumbersTable.item(0, 1).text(), "11")
        self.assertEqual(window.folderNumbersTable.item(0, 0).checkState(), Qt.Checked)
        self.assertEqual(window.filterIssueNumbersButton.text(), "Hoan tac loc so loi")

        window.filter_issue_numbers()

        self.assertEqual(window.folderNumberSelection.selected_record_ids(), [10, 11, 12])
        self.assertEqual(window.filterIssueNumbersButton.text(), "Loc so loi")
        self.assertIsNotNone(app)

    def test_refresh_scan_results_without_excel_renders_folder_rows(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / "runs" / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("{}", encoding="utf-8")
            window = UploadLabMainWindow(working_dir=temp_root)
            window.contract_book_analysis = None
            window.current_manifest_path = manifest_path
            record = SimpleNamespace(
                record_id=31,
                contract_no="31/2026/CCGD",
                status="extracted",
                source_file=Path("a.docx"),
                missing_fields=[],
            )

            with patch("ui_qt.main_window.load_upload_queue", return_value=({}, [record], 1)), patch(
                "ui_qt.main_window.QMessageBox.critical"
            ) as mocked_critical:
                window._refresh_scan_results_from_manifest()

            mocked_critical.assert_not_called()
            self.assertEqual(window.folderNumbersTable.rowCount(), 1)
            self.assertEqual(window.folderNumberSelection.selected_record_ids(), [])
        self.assertIsNotNone(app)

    def test_download_excel_from_web_queues_work_in_upload_thread(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            window = UploadLabMainWindow(working_dir=temp_root)
            window.fromDateEdit.setText("01/01/2026")
            window.toDateEdit.setText("18/06/2026")
            emitted_commands = []
            window.downloadExcelRequested.connect(emitted_commands.append)
            with patch.object(window, "ensure_upload_runtime_ready", return_value=True), patch.object(
                window, "_ensure_upload_worker"
            ):
                window.download_excel_from_web()

            self.assertEqual(emitted_commands, [{"from_date": "01/01/2026", "to_date": "18/06/2026"}])
            self.assertFalse(window.downloadExcelButton.isEnabled())
        self.assertIsNotNone(app)

    def test_upload_selected_queues_prepare_without_calling_session_on_gui_thread(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui.services.scan_classification_service import FolderScanRow, ScanClassification
        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            window = UploadLabMainWindow(working_dir=temp_root)
            window.current_manifest_path = temp_root / "runs" / "manifest.json"
            window.current_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            window.current_manifest_path.write_text("{}", encoding="utf-8")
            classification = ScanClassification(
                folder_rows=[
                    FolderScanRow(21, "21/2026/CCGD", "21/2026", "extracted", "c.docx", [], True, "chua co trong Excel"),
                    FolderScanRow(22, "22/2026/CCGD", "22/2026", "extracted", "d.docx", [], True, "chua co trong Excel"),
                ],
                missing_in_excel_record_ids={21, 22},
                has_excel=True,
            )
            window.render_scan_classification(classification)
            window.folderNumberSelection.set_selected(22, False)
            window._apply_selection_to_folder_table()

            commands = []
            window.prepareUploadRequested.connect(commands.append)

            with patch.object(window, "ensure_upload_runtime_ready", return_value=True), patch.object(
                window,
                "_ensure_upload_worker",
                return_value=MagicMock(),
            ):
                window.handle_upload_selected()

            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0]["selected_record_ids"], [21])
            self.assertEqual(commands[0]["cong_chung_vien"], "Phạm Minh Chi")
            self.assertEqual(commands[0]["thu_ky"], "Nguyễn Nhật Minh")
            self.assertTrue(window.uploadBusy)
            self.assertTrue(window.stopUploadButton.isEnabled())
            self.assertFalse(window.continueUploadButton.isEnabled())
            self.assertFalse(window.closeUploadBrowserButton.isEnabled())
        self.assertIsNotNone(app)

    def test_upload_worker_owns_stop_event_on_dedicated_python_thread(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        from ui_qt.workers import UploadWorker

        app = QApplication.instance() or QApplication([])

        class FakeSession:
            def __init__(self):
                self.command = None

            def prepare_manifest(self, manifest_path, stop_event, **kwargs):
                self.command = (manifest_path, stop_event, kwargs)
                return {"prepared_count": 1, "remaining": 0}

            def poll_manual_login(self):
                return {"status": "idle"}

            def poll_prepared_pages(self):
                return {"saved_record_ids": [], "closed_record_ids": [], "open_record_ids": []}

            def close(self):
                return None

        with tempfile.TemporaryDirectory() as temp_dir:
            worker = UploadWorker(Path(temp_dir))
            fake_session = FakeSession()
            worker._ensure_session = lambda: fake_session
            loop = QEventLoop()
            result = []
            worker.prepared.connect(lambda summary: (result.append(summary), loop.quit()))
            worker.prepare(
                {
                    "manifest_path": "manifest.json",
                    "selected_record_ids": [11, 12],
                    "exclude_contract_nos": [],
                    "cong_chung_vien": "Phạm Minh Chi",
                    "thu_ky": "Nguyễn Nhật Minh",
                }
            )
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            worker.close_session()

            self.assertEqual(result, [{"prepared_count": 1, "remaining": 0}])
            self.assertIs(fake_session.command[1], worker.stop_event)
            self.assertEqual(fake_session.command[2]["selected_record_ids"], {11, 12})
        self.assertIsNotNone(app)

    def test_upload_progress_stop_and_continue_reuse_selected_records(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui.services.scan_classification_service import FolderScanRow, ScanClassification
        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            window = UploadLabMainWindow(working_dir=temp_root)
            window.current_manifest_path = temp_root / "runs" / "manifest.json"
            window.current_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            window.current_manifest_path.write_text("{}", encoding="utf-8")
            classification = ScanClassification(
                folder_rows=[
                    FolderScanRow(31, "31/2026/CCGD", "31/2026", "extracted", "a.docx", [], True, "chua co trong Excel"),
                    FolderScanRow(32, "32/2026/CCGD", "32/2026", "extracted", "b.docx", [], True, "chua co trong Excel"),
                ],
                missing_in_excel_record_ids={31, 32},
                has_excel=True,
            )
            window.render_scan_classification(classification)

            commands = []
            window.prepareUploadRequested.connect(commands.append)
            fake_worker = MagicMock()
            window.uploadWorker = fake_worker

            with patch.object(window, "ensure_upload_runtime_ready", return_value=True), patch.object(
                window,
                "_ensure_upload_worker",
                return_value=fake_worker,
            ), patch.object(
                window, "_refresh_scan_results_from_manifest"
            ):
                window.handle_upload_selected()
                window._handle_upload_progress(
                    {"event": "record_prepared", "prepared_count": 1, "total_pending": 2, "contract_no": "31/2026"}
                )
                self.assertEqual(window.uploadProgressBar.value(), 50)
                self.assertIn("31/2026", window.uploadProgressLabel.text())
                window.stop_upload()
                window.uploadWorker.request_stop.assert_called_once_with()

                window._handle_upload_prepared({"prepared_count": 1, "remaining": 1})

                self.assertTrue(window.continueUploadButton.isEnabled())
                self.assertTrue(window.closeUploadBrowserButton.isEnabled())

                window.continue_upload_selected()
                window._handle_upload_prepared({"prepared_count": 1, "remaining": 0})

            self.assertEqual(len(commands), 2)
            self.assertEqual(commands[0]["selected_record_ids"], [31, 32])
            self.assertEqual(commands[1]["selected_record_ids"], [31, 32])
            self.assertFalse(window.continueUploadButton.isEnabled())
        self.assertIsNotNone(app)

    def test_excel_load_renders_clean_missing_and_issue_tables(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workbook_path = temp_root / "book.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet["A1"] = "SO CONG CHUNG"
            sheet["B1"] = "NGAY, THANG, NAM CONG CHUNG"
            sheet["A2"] = "1/2026"
            sheet["B2"] = "01/01/2026"
            sheet["A3"] = "3/2026"
            sheet["B3"] = "01/01/2026"
            sheet["A4"] = "66.2026"
            sheet["B4"] = "01/01/2026"
            workbook.save(workbook_path)
            workbook.close()

            window = UploadLabMainWindow(working_dir=temp_root)

            window.excelPathEdit.setText(str(workbook_path))
            window.fromDateEdit.setText("01/01/2026")
            window.toDateEdit.setText("18/06/2026")
            window.load_excel()

            self.assertIn("Excel=3 | hop_le=2 | thieu=1 | loi=1 | trung=0", window.excelSummaryLabel.text())
            self.assertEqual(window.excelDisplayTable.rowCount(), 2)
            self.assertEqual(window.excelDisplayTable.item(0, 1).text(), "1/2026")
            self.assertEqual(window.excelMissingTable.rowCount(), 1)
            self.assertEqual(window.excelMissingTable.item(0, 0).text(), "2/2026")
            self.assertEqual(window.excelMissingTable.item(0, 3).text(), "Thieu that")
            self.assertEqual(window.excelIssueTable.rowCount(), 1)
            self.assertEqual(window.excelIssueTable.item(0, 0).text(), "sai_format")
            self.assertIsNotNone(app)

    def test_failed_excel_load_clears_new_excel_tables(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        window.excelDisplayTable.setRowCount(1)
        window.excelMissingTable.setRowCount(1)
        window.excelIssueTable.setRowCount(1)
        window.excelPathEdit.setText(str(Path("missing.xlsx").resolve()))

        with patch("ui_qt.main_window.QMessageBox.critical") as mocked_critical:
            window.load_excel()

        mocked_critical.assert_called_once()
        self.assertEqual(window.excelSummaryLabel.text(), "Chua doc Excel.")
        self.assertEqual(window.excelDisplayTable.rowCount(), 0)
        self.assertEqual(window.excelMissingTable.rowCount(), 0)
        self.assertEqual(window.excelIssueTable.rowCount(), 0)
        self.assertIsNotNone(app)

    def test_close_event_quits_running_scan_thread(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        fake_thread = MagicMock()
        fake_thread.isRunning.return_value = True
        window.scanThread = fake_thread

        event = MagicMock()
        with patch("ui_qt.main_window.QMessageBox.information") as mocked_info, patch(
            "ui_qt.main_window.FluentWindow.closeEvent"
        ) as mocked_super_close:
            window.closeEvent(event)

        mocked_info.assert_called_once_with(
            window,
            "Upload Lab",
            "Dang scan folder. Hay doi scan xong truoc khi dong app.",
        )
        event.ignore.assert_called_once_with()
        mocked_super_close.assert_not_called()
        self.assertIsNotNone(app)

    def test_close_event_allows_close_when_no_scan_running(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()
        window.scanThread = None

        event = MagicMock()
        with patch("ui_qt.main_window.QMessageBox.information") as mocked_info, patch(
            "ui_qt.main_window.FluentWindow.closeEvent"
        ) as mocked_super_close:
            window.closeEvent(event)

        mocked_info.assert_not_called()
        event.ignore.assert_not_called()
        mocked_super_close.assert_called_once_with(event)
        self.assertIsNotNone(app)

    def test_pyside6_import_available_after_install(self):
        if importlib.util.find_spec("PySide6") is None:
            self.skipTest("PySide6 is not installed in this environment yet")

        module = importlib.import_module("PySide6")
        self.assertIsNotNone(module)

    def test_bootstrap_probe_runtime_handles_pyside6_in_child_process(self):
        runtime = bootstrap_ui.probe_runtime(Path(sys.executable))

        self.assertTrue(runtime.get("ok"), msg=runtime.get("probe_error"))
        self.assertTrue(runtime["modules"]["PySide6"])


if __name__ == "__main__":
    unittest.main()
