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

    def test_library_project_compiled_preview_exposes_auto_and_manual_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))

            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Short pitch",
                    "pitch_90": "Long pitch",
                    "business_value": "Build agent workflows for operations teams",
                    "architecture": "React UI + Python orchestrator",
                    "manual_evidence": [
                        {
                            "evidence_id": "manual-evidence-1",
                            "title": "Load Test",
                            "summary": "Benchmarked 100 interview-style queries locally.",
                            "source_ref": "benchmarks/load-test.md",
                            "confidence": "high",
                        }
                    ],
                    "manual_metrics": [
                        {
                            "evidence_id": "manual-metric-1",
                            "metric_name": "first_token_latency",
                            "metric_value": "850ms",
                            "baseline": "1.7s",
                            "method": "local benchmark",
                            "environment": "sqlite + fast model",
                            "source_note": "benchmarks/load-test.md",
                        }
                    ],
                    "manual_retrieval_units": [
                        {
                            "unit_id": "manual-ru-1",
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why this architecture?"],
                            "short_answer": "I optimized for debuggability first.",
                            "long_answer": "I chose smaller components so I could reason about retrieval failures quickly.",
                            "key_points": ["debuggability", "latency"],
                            "supporting_refs": ["manual-evidence-1", "manual-metric-1"],
                            "hooks": ["The retrieval router was the hardest part."],
                            "safe_claims": ["The architecture was chosen for debuggability."],
                        }
                    ],
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

            client.post(f"/api/workspaces/{workspace['workspace_id']}/compile").json()
            preview = client.get(f"/api/library/projects/{project['project_id']}/compiled-preview").json()

        self.assertTrue(preview["compiled"])
        self.assertEqual(preview["project_id"], project["project_id"])
        self.assertGreaterEqual(len(preview["module_cards"]), 1)
        self.assertIn("manual-evidence-1", {item["evidence_id"] for item in preview["evidence_cards"]})
        self.assertIn("manual-metric-1", {item["evidence_id"] for item in preview["metric_evidence"]})
        self.assertIn("manual-ru-1", {item["unit_id"] for item in preview["retrieval_units"]})

    def test_library_bundle_history_supports_reuse_and_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Pitch one",
                    "business_value": "Build agent workflows",
                    "architecture": "React + Python",
                    "manual_evidence": [
                        {
                            "evidence_id": "manual-evidence-1",
                            "title": "Load Test",
                            "summary": "Benchmarked 100 interview questions locally.",
                            "source_ref": "benchmarks/load-test.md",
                            "confidence": "high",
                        }
                    ],
                    "manual_retrieval_units": [
                        {
                            "unit_id": "manual-ru-1",
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why this architecture?"],
                            "short_answer": "I optimized for debuggability first.",
                            "long_answer": "I split the system to make retrieval failures easier to debug.",
                            "key_points": ["debuggability", "latency"],
                            "supporting_refs": ["manual-evidence-1"],
                            "hooks": ["The retrieval router was the hardest part."],
                            "safe_claims": ["The architecture was chosen for debuggability."],
                        }
                    ],
                },
            ).json()
            project_two = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Retrieval Ops",
                    "pitch_30": "Pitch two",
                    "business_value": "Improve retrieval quality",
                    "architecture": "SQLite + local bundle compiler",
                    "manual_evidence": [
                        {
                            "evidence_id": "manual-evidence-2",
                            "title": "Offline Eval",
                            "summary": "Compared three reranking strategies offline.",
                            "source_ref": "evals/retrieval-ops.md",
                            "confidence": "high",
                        }
                    ],
                    "manual_retrieval_units": [
                        {
                            "unit_id": "manual-ru-2",
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why this retrieval pipeline?"],
                            "short_answer": "I optimized bundle reuse for fast company switching.",
                            "long_answer": "I stored session-ready snapshots so I could swap contexts in seconds.",
                            "key_points": ["reuse", "switching"],
                            "supporting_refs": ["manual-evidence-2"],
                            "hooks": ["Bundle reuse made company-specific switching much faster."],
                            "safe_claims": ["The pipeline prioritized fast context switching."],
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
                    "project_ids": [project_one["project_id"]],
                    "overlay_id": overlay["overlay_id"],
                },
            ).json()

            first_payload = client.post(
                f"/api/library/presets/{preset['preset_id']}/build-session-payload"
            ).json()
            client.put(
                f"/api/library/presets/{preset['preset_id']}",
                json={
                    "project_ids": [project_one["project_id"], project_two["project_id"]],
                    "overlay_id": overlay["overlay_id"],
                },
            ).json()
            second_payload = client.post(
                f"/api/library/presets/{preset['preset_id']}/build-session-payload"
            ).json()

            reused = client.post(
                f"/api/library/bundles/{first_payload['activation_summary']['bundle_id']}/reuse-session-payload"
            ).json()
            comparison = client.get(
                f"/api/library/bundles/{second_payload['activation_summary']['bundle_id']}/compare/"
                f"{first_payload['activation_summary']['bundle_id']}"
            ).json()

        self.assertEqual(len(reused["knowledge"]["projects"]), 1)
        self.assertEqual(reused["knowledge"]["projects"][0]["project_id"], project_one["project_id"])
        self.assertEqual(reused["briefing"]["company"], "Alibaba")
        self.assertEqual(comparison["project_count_delta"], 1)
        self.assertEqual(comparison["added_projects"], ["Retrieval Ops"])
        self.assertEqual(comparison["removed_projects"], [])
        self.assertIn("Retrieval Ops / tradeoff_reasoning", comparison["added_retrieval_units"])
        self.assertEqual(comparison["removed_retrieval_units"], [])
        self.assertIn("Offline Eval", comparison["added_evidence_titles"])
        self.assertEqual(comparison["removed_evidence_titles"], [])
        self.assertIn("Bundle reuse made company-specific switching much faster.", comparison["added_hook_texts"])
        self.assertEqual(comparison["removed_hook_texts"], [])

    def test_library_document_assets_support_project_and_role_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()

            created = client.post(
                f"/api/library/projects/{project['project_id']}/documents",
                json={
                    "title": "Design Notes",
                    "path": "notes/design.md",
                    "content": "Initial architecture notes",
                },
            ).json()
            listing = client.get(f"/api/library/projects/{project['project_id']}/documents").json()
            updated = client.put(
                f"/api/library/documents/{created['document_id']}",
                json={
                    "title": "Architecture Notes",
                    "content": "Updated architecture notes",
                },
            ).json()
            created_role = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/role-documents",
                json={
                    "title": "Alibaba JD",
                    "content": "Need agent platform experience",
                },
            ).json()
            role_listing = client.get(
                f"/api/library/workspaces/{workspace['workspace_id']}/role-documents"
            ).json()
            deleted = client.delete(f"/api/library/documents/{created['document_id']}").json()
            listing_after_delete = client.get(f"/api/library/projects/{project['project_id']}/documents").json()

        self.assertEqual(created["source_kind"], "manual")
        self.assertEqual(len(listing["documents"]), 1)
        self.assertEqual(updated["title"], "Architecture Notes")
        self.assertEqual(updated["content"], "Updated architecture notes")
        self.assertEqual(created_role["scope"], "role")
        self.assertEqual(len(role_listing["documents"]), 1)
        self.assertEqual(role_listing["documents"][0]["title"], "Alibaba JD")
        self.assertEqual(deleted["status"], "deleted")
        self.assertEqual(listing_after_delete["documents"], [])

    def test_library_project_roundtrip_preserves_manual_authoring_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            created = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "manual_evidence": [
                        {
                            "title": "Load Test",
                            "summary": "Benchmarked 100 interview-style queries locally.",
                            "source_ref": "benchmarks/load-test.md",
                            "confidence": "high",
                        }
                    ],
                    "manual_metrics": [
                        {
                            "metric_name": "first_token_latency",
                            "metric_value": "850ms",
                            "baseline": "1.7s",
                            "method": "local benchmark",
                            "environment": "sqlite + fast model",
                            "source_note": "benchmarks/load-test.md",
                        }
                    ],
                    "manual_retrieval_units": [
                        {
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why this architecture?"],
                            "short_answer": "I optimized for debuggability first.",
                            "long_answer": "I chose smaller components so I could reason about retrieval failures quickly.",
                            "key_points": ["debuggability", "latency"],
                            "supporting_refs": ["manual-evidence-1"],
                            "hooks": ["The retrieval router was the hardest part."],
                            "safe_claims": ["The architecture was chosen for debuggability."],
                        }
                    ],
                },
            ).json()
            fetched = client.get(f"/api/library/projects/{created['project_id']}").json()

        self.assertEqual(len(fetched["manual_evidence"]), 1)
        self.assertEqual(fetched["manual_evidence"][0]["title"], "Load Test")
        self.assertEqual(len(fetched["manual_metrics"]), 1)
        self.assertEqual(fetched["manual_metrics"][0]["metric_name"], "first_token_latency")
        self.assertEqual(len(fetched["manual_retrieval_units"]), 1)
        self.assertEqual(fetched["manual_retrieval_units"][0]["unit_type"], "tradeoff_reasoning")

    def test_library_repo_reindex_refreshes_imported_assets_and_keeps_manual_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "agent-console"
            repo_root.mkdir()
            (repo_root / "README.md").write_text("Version 1 doc", encoding="utf-8")
            src_dir = repo_root / "src"
            src_dir.mkdir()
            (src_dir / "workflow.py").write_text("def run():\n    return 'v1'\n", encoding="utf-8")

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
            repo_id = imported["knowledge"]["projects"][0]["repo_summaries"][0]["repo_id"]
            client.post(
                f"/api/library/projects/{project['project_id']}/documents",
                json={
                    "title": "Interview Notes",
                    "path": "notes/interview.md",
                    "content": "Manual project notes",
                },
            ).json()

            (repo_root / "README.md").write_text("Version 2 doc", encoding="utf-8")
            (src_dir / "workflow.py").write_text("def run():\n    return 'v2'\n", encoding="utf-8")

            reindexed = client.post(f"/api/library/repos/{repo_id}/reindex").json()
            refreshed_project = client.get(f"/api/library/projects/{project['project_id']}").json()

        imported_docs = [item for item in refreshed_project["documents"] if item["source_kind"] == "repo_import"]
        manual_docs = [item for item in refreshed_project["documents"] if item["source_kind"] == "manual"]

        self.assertEqual(reindexed["import_summary"]["project_name"], "Agent Console")
        self.assertEqual(reindexed["import_summary"]["imported_docs"], 1)
        self.assertEqual(reindexed["import_summary"]["imported_code_files"], 1)
        self.assertTrue(any(item["content"] == "Version 2 doc" for item in imported_docs))
        self.assertTrue(any(item["title"] == "Interview Notes" for item in manual_docs))
        self.assertTrue(any(item["content"] == "Manual project notes" for item in manual_docs))
        self.assertTrue(any(item["content"] == "def run():\n    return 'v2'\n" for item in refreshed_project["code_files"]))


if __name__ == "__main__":
    unittest.main()
