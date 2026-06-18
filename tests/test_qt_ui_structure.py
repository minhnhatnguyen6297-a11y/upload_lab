from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import unittest
import tempfile
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
        self.assertTrue(Path("ui_qt/forms/main_window.ui").exists())

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

        from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QProgressBar, QTabWidget, QTableWidget

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        window = UploadLabMainWindow()

        widget_checks = [
            ("excelPathEdit", QLineEdit),
            ("browseExcelButton", QPushButton),
            ("loadExcelButton", QPushButton),
            ("excelSummaryLabel", QLabel),
            ("excelResultTabs", QTabWidget),
            ("parsedExcelTable", QTableWidget),
            ("missingExcelTable", QTableWidget),
            ("excelWarningTable", QTableWidget),
            ("excelParseErrorTable", QTableWidget),
            ("folderPathEdit", QLineEdit),
            ("browseFolderButton", QPushButton),
            ("scanFolderButton", QPushButton),
            ("scanProgressBar", QProgressBar),
            ("scanSummaryLabel", QLabel),
            ("scanResultTabs", QTabWidget),
            ("validUploadTable", QTableWidget),
            ("notInExcelTable", QTableWidget),
            ("missingFieldsTable", QTableWidget),
            ("webDuplicateTable", QTableWidget),
            ("localDuplicateTable", QTableWidget),
            ("excelMissingInFolderTable", QTableWidget),
        ]

        for name, widget_type in widget_checks:
            with self.subTest(name=name):
                widget = window.ui.findChild(widget_type, name)
                self.assertIsNotNone(widget)
                self.assertIsInstance(widget, widget_type)

        self.assertEqual(window.excelResultTabs.count(), 4)
        self.assertEqual(window.scanResultTabs.count(), 6)
        self.assertIsNotNone(app)

    def test_failed_excel_load_clears_previous_results(self):
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
            sheet["A2"] = "01/2026"
            sheet["B2"] = "05/01/2026"
            workbook.save(workbook_path)
            workbook.close()

            window = UploadLabMainWindow(working_dir=temp_root)

            window.excelPathEdit.setText(str(workbook_path))
            window.load_excel()
            self.assertIn("Excel=1", window.excelSummaryLabel.text())
            self.assertGreater(window.parsedExcelTable.rowCount(), 0)

            missing_path = temp_root / "missing.xlsx"
            window.excelPathEdit.setText(str(missing_path))
            with patch("ui_qt.main_window.QMessageBox.critical") as mocked_critical:
                window.load_excel()

            mocked_critical.assert_called_once()
            self.assertEqual(window.contract_book_analysis, None)
            self.assertEqual(window.excelSummaryLabel.text(), "Chua doc Excel.")
            self.assertEqual(window.parsedExcelTable.rowCount(), 0)
            self.assertEqual(window.missingExcelTable.rowCount(), 0)
            self.assertEqual(window.excelWarningTable.rowCount(), 0)
            self.assertEqual(window.excelParseErrorTable.rowCount(), 0)
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
            "ui_qt.main_window.QMainWindow.closeEvent"
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
            "ui_qt.main_window.QMainWindow.closeEvent"
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
