from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path

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
        self.assertTrue(Path("ui_qt/forms/main_window.ui").exists())

    def test_qt_entrypoint_imports(self):
        from ui_qt.app import run_qt_app
        from ui_qt.main_window import UploadLabMainWindow

        self.assertTrue(callable(run_qt_app))
        self.assertEqual(UploadLabMainWindow.__name__, "UploadLabMainWindow")

    def test_qt_main_window_loads_ui_and_preserves_working_dir(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        from PySide6.QtWidgets import QApplication

        from ui_qt.main_window import UploadLabMainWindow

        app = QApplication.instance() or QApplication([])
        working_dir = Path("D:/upload_lab_repo/.worktrees/qt-workflow-redesign")
        window = UploadLabMainWindow(working_dir=working_dir)

        self.assertEqual(window.windowTitle(), "Upload Lab")
        self.assertIsNotNone(window.centralWidget())
        self.assertTrue(hasattr(window, "ui"))
        self.assertEqual(window.centralWidget().objectName(), "centralWidget")
        self.assertEqual(window.ui.objectName(), "centralWidget")
        self.assertEqual(window.working_dir, working_dir)
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
