from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from interview_trainer.workspace import WorkspaceManager


class LibraryRepositoryTests(unittest.TestCase):
    def test_import_path_records_repo_summary_and_preserves_other_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "agent-console"
            project_root.mkdir()
            (project_root / "README.md").write_text("Agent console docs", encoding="utf-8")
            src_dir = project_root / "src"
            src_dir.mkdir()
            (src_dir / "workflow.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")

            manager = WorkspaceManager(storage_root=root / "library")
            workspace = manager.create_workspace(
                {
                    "name": "Library",
                    "knowledge": {
                        "projects": [
                            {"name": "Agent Console"},
                            {"name": "Ops Dashboard"},
                        ]
                    },
                }
            )

            imported = manager.import_path(
                workspace["workspace_id"],
                {
                    "path": str(project_root),
                    "project_name": "Agent Console",
                },
            )

            reloaded = WorkspaceManager(storage_root=root / "library")
            restored = reloaded.get_workspace(workspace["workspace_id"])

        project_names = [item["name"] for item in restored["knowledge"]["projects"]]
        self.assertEqual(project_names, ["Agent Console", "Ops Dashboard"])
        self.assertEqual(imported["knowledge"]["projects"][0]["documents"][0]["path"], "README.md")
        self.assertEqual(restored["knowledge"]["projects"][0]["code_files"][0]["path"], "src/workflow.py")
        self.assertEqual(restored["knowledge"]["projects"][0]["repo_summaries"][0]["root_path"], str(project_root))
        self.assertEqual(restored["knowledge"]["projects"][0]["repo_summaries"][0]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
