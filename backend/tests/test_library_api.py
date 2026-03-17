from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from interview_trainer.api import create_app


class LibraryApiTests(unittest.TestCase):
    def test_library_workspace_and_project_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))

            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            created_project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console", "business_value": "Build agent workflows"},
            ).json()

            listing = client.get(f"/api/library/workspaces/{workspace['workspace_id']}/projects").json()
            updated = client.put(
                f"/api/library/projects/{created_project['project_id']}",
                json={"architecture": "React + Python orchestrator"},
            ).json()

        self.assertEqual(created_project["name"], "Agent Console")
        self.assertEqual(len(listing["projects"]), 1)
        self.assertEqual(listing["projects"][0]["project_id"], created_project["project_id"])
        self.assertEqual(updated["architecture"], "React + Python orchestrator")

    def test_library_project_repo_import_and_listing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "agent-console"
            repo_root.mkdir()
            (repo_root / "README.md").write_text("Agent console docs", encoding="utf-8")
            src_dir = repo_root / "src"
            src_dir.mkdir()
            (src_dir / "workflow.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")

            client = TestClient(create_app(workspace_storage_root=root / "library"))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()

            imported = client.post(
                f"/api/library/projects/{project['project_id']}/repos/import-path",
                json={"path": str(repo_root)},
            ).json()
            repos = client.get(f"/api/library/projects/{project['project_id']}/repos").json()

        self.assertEqual(imported["import_summary"]["project_name"], "Agent Console")
        self.assertEqual(len(repos["repos"]), 1)
        self.assertEqual(repos["repos"][0]["root_path"], str(repo_root))
        self.assertEqual(repos["repos"][0]["status"], "ready")

    def test_build_session_payload_returns_knowledge_briefing_and_activation_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))

            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Short pitch",
                    "business_value": "Build agent workflows for operations teams",
                    "architecture": "React UI + Python orchestrator",
                    "documents": [
                        {
                            "path": "README.md",
                            "content": "Latency dropped from 1.8s to 900ms.",
                        }
                    ],
                    "code_files": [
                        {
                            "path": "src/orchestrator/workflow.py",
                            "content": "def run():\n    return 'ok'\n",
                        }
                    ],
                },
            ).json()
            overlay = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
                json={
                    "name": "Alibaba",
                    "company": "Alibaba",
                    "job_description": "agent platform",
                    "business_context": "support internal engineering teams",
                },
            ).json()
            preset = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/presets",
                json={
                    "name": "Alibaba preset",
                    "project_ids": [project["project_id"]],
                    "overlay_id": overlay["overlay_id"],
                },
            ).json()

            payload = client.post(
                f"/api/library/presets/{preset['preset_id']}/build-session-payload"
            ).json()

        self.assertEqual(payload["knowledge"]["projects"][0]["project_id"], project["project_id"])
        self.assertEqual(payload["knowledge"]["projects"][0]["pitch_30"], "Short pitch")
        self.assertEqual(payload["briefing"]["company"], "Alibaba")
        self.assertEqual(payload["briefing"]["job_description"], "agent platform")
        self.assertEqual(payload["activation_summary"]["project_count"], 1)
        self.assertGreaterEqual(payload["activation_summary"]["retrieval_unit_count"], 1)


if __name__ == "__main__":
    unittest.main()
