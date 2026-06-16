from __future__ import annotations

import inspect
import unittest

import ui_runner
from ui.app import UploadLabApp
from ui.tabs.folder_workflow_tab import FolderWorkflowTab
from ui.tabs.web_list_tab import WebListTab


class TkinterUIStructureTests(unittest.TestCase):
    def test_ui_runner_is_thin_entrypoint(self):
        source = inspect.getsource(ui_runner)

        self.assertLess(len(source.splitlines()), 40)

    def test_modular_tabs_are_exposed(self):
        self.assertEqual(UploadLabApp.__name__, "UploadLabApp")
        self.assertEqual(WebListTab.__name__, "WebListTab")
        self.assertEqual(FolderWorkflowTab.__name__, "FolderWorkflowTab")


if __name__ == "__main__":
    unittest.main()
