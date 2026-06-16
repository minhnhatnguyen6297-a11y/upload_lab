from __future__ import annotations

import importlib
import importlib.util
import sys
import unittest
from pathlib import Path

import bootstrap_ui


class QtUIStructureTests(unittest.TestCase):
    def test_pyside6_dependency_declared(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("PySide6", requirements)

    @unittest.skip("Qt package is created in Task 6")
    def test_qt_package_files_exist(self):
        self.assertTrue(Path("ui_qt").is_dir())
        self.assertTrue(Path("ui_qt/forms/main_window.ui").exists())

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
