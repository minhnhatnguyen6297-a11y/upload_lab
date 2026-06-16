from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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

        self.assertIsNotNone(importlib.util.find_spec("PySide6"))


if __name__ == "__main__":
    unittest.main()
