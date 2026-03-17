from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from interview_trainer.workspace import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_create_and_compile_workspace(self) -> None:
        manager = WorkspaceManager()
        workspace = manager.create_workspace(
            {
                "name": "My Interview Pack",
                "knowledge": {
                    "profile": {
                        "headline": "AI Agent Engineer",
                        "summary": "I build agent workflows with retrieval and evaluation.",
                    },
                    "projects": [
                        {
                            "name": "Agent Console",
                            "business_value": "Helps operators configure workflows.",
                            "documents": [{"content": "This project focuses on reliability and latency."}],
                            "code_files": [{"path": "src/app.py", "content": "def run():\n    return True\n"}],
                        }
                    ],
                },
            }
        )

        self.assertEqual(workspace["name"], "My Interview Pack")
        self.assertEqual(workspace["knowledge"]["projects"][0]["name"], "Agent Console")

        compiled = manager.compile_workspace(workspace["workspace_id"])

        self.assertIsNotNone(compiled["compiled_knowledge"])
        self.assertEqual(compiled["compile_summary"]["projects"], ["Agent Console"])
        self.assertGreaterEqual(compiled["compile_summary"]["code_chunks"], 1)

    def test_import_path_populates_project_documents_and_code(self) -> None:
        manager = WorkspaceManager()
        workspace = manager.create_workspace({"name": "Imported Workspace", "knowledge": {}})

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("Agent project with tracing and evaluation.", encoding="utf-8")
            source_dir = root / "src"
            source_dir.mkdir()
            (source_dir / "workflow.py").write_text("def run_workflow():\n    return 'ok'\n", encoding="utf-8")

            imported = manager.import_path(
                workspace["workspace_id"],
                {
                    "path": str(root),
                    "project_name": "Imported Project",
                },
            )

        self.assertEqual(imported["import_summary"]["project_name"], "Imported Project")
        self.assertEqual(imported["import_summary"]["imported_docs"], 1)
        self.assertEqual(imported["import_summary"]["imported_code_files"], 1)
        self.assertEqual(imported["knowledge"]["projects"][0]["name"], "Imported Project")
        self.assertEqual(imported["knowledge"]["projects"][0]["documents"][0]["path"], "README.md")
        self.assertEqual(imported["knowledge"]["projects"][0]["code_files"][0]["path"], "src/workflow.py")


if __name__ == "__main__":
    unittest.main()
