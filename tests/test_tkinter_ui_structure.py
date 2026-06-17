from __future__ import annotations

import unittest
from pathlib import Path


class TkinterUIStructureTests(unittest.TestCase):
    def test_ui_runner_is_thin_entrypoint(self):
        source = Path("ui_runner.py").read_text(encoding="utf-8")

        self.assertLess(len(source.splitlines()), 40)

    def test_modular_tabs_are_exposed(self):
        app_source = Path("ui/app.py").read_text(encoding="utf-8")
        tabs_init_source = Path("ui/tabs/__init__.py").read_text(encoding="utf-8")
        folder_source = Path("ui/tabs/folder_workflow_tab.py").read_text(encoding="utf-8")
        web_source = Path("ui/tabs/web_list_tab.py").read_text(encoding="utf-8")

        self.assertIn("from ui.tabs import FolderWorkflowTab, WebListTab", app_source)
        self.assertIn("class UploadLabApp", app_source)
        self.assertIn("from .folder_workflow_tab import FolderWorkflowTab", tabs_init_source)
        self.assertIn("from .web_list_tab import WebListTab", tabs_init_source)
        self.assertIn("class FolderWorkflowTab", folder_source)
        self.assertIn("class WebListTab", web_source)


if __name__ == "__main__":
    unittest.main()
