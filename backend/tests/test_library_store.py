from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from interview_trainer.workspace import WorkspaceManager


class LibraryStoreTests(unittest.TestCase):
    def test_workspace_persists_across_manager_restarts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = WorkspaceManager(storage_root=root)
            created = manager.create_workspace(
                {
                    "name": "Persistent Library",
                    "knowledge": {
                        "profile": {
                            "headline": "AI engineer",
                        }
                    },
                }
            )

            reloaded = WorkspaceManager(storage_root=root)
            listing = reloaded.list_workspaces()

        self.assertEqual(len(listing["workspaces"]), 1)
        self.assertEqual(listing["workspaces"][0]["workspace_id"], created["workspace_id"])
        self.assertEqual(listing["workspaces"][0]["name"], "Persistent Library")


if __name__ == "__main__":
    unittest.main()
