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

    def test_library_workspace_compiled_preview_supports_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))

            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Short pitch",
                    "business_value": "Build agent workflows for interview practice",
                    "architecture": "React + Python",
                    "manual_retrieval_units": [
                        {
                            "unit_id": "manual-ru-latency",
                            "unit_type": "performance_evidence",
                            "question_forms": ["How did you improve latency?"],
                            "short_answer": "I optimized first-token latency.",
                            "long_answer": "I shortened the retrieval path to improve latency.",
                            "key_points": ["latency", "retrieval"],
                            "supporting_refs": [],
                            "hooks": ["The retrieval router latency was the hardest part."],
                            "safe_claims": ["The system improved latency."],
                        }
                    ],
                },
            ).json()
            client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Bundle Ops",
                    "pitch_30": "Short pitch",
                    "business_value": "Improve bundle reuse",
                    "architecture": "SQLite + local compiler",
                    "manual_retrieval_units": [
                        {
                            "unit_id": "manual-ru-bundle",
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why bundle snapshots?"],
                            "short_answer": "I optimized context switching.",
                            "long_answer": "I stored session payload snapshots to improve company switching.",
                            "key_points": ["bundle", "reuse"],
                            "supporting_refs": [],
                            "hooks": ["Bundle reuse made context switching much faster."],
                            "safe_claims": ["The system prioritized fast switching."],
                        }
                    ],
                },
            ).json()

            client.post(f"/api/workspaces/{workspace['workspace_id']}/compile").json()
            preview = client.get(
                f"/api/library/workspaces/{workspace['workspace_id']}/compiled-preview",
                params={
                    "project_id": project_one["project_id"],
                    "artifact_kind": "retrieval",
                    "search": "latency",
                },
            ).json()

        self.assertTrue(preview["compiled"])
        self.assertEqual(preview["filters"]["project_id"], project_one["project_id"])
        self.assertEqual(preview["filters"]["artifact_kind"], "retrieval")
        self.assertEqual(preview["filters"]["search"], "latency")
        self.assertEqual(preview["module_cards"], [])
        self.assertEqual(preview["evidence_cards"], [])
        self.assertEqual(preview["metric_evidence"], [])
        self.assertEqual([item["unit_id"] for item in preview["retrieval_units"]], ["manual-ru-latency"])
        self.assertEqual(len(preview["project_summaries"]), 1)
        self.assertEqual(preview["project_summaries"][0]["project_id"], project_one["project_id"])

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

    def test_library_preset_clone_and_compare_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()
            project_two = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Retrieval Ops"},
            ).json()
            overlay_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
                json={"name": "Alibaba", "company": "Alibaba"},
            ).json()
            overlay_two = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
                json={"name": "ByteDance", "company": "ByteDance"},
            ).json()
            preset_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/presets",
                json={
                    "name": "Preset A",
                    "project_ids": [project_one["project_id"]],
                    "overlay_id": overlay_one["overlay_id"],
                    "include_role_documents": True,
                },
            ).json()
            preset_two = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/presets",
                json={
                    "name": "Preset B",
                    "project_ids": [project_one["project_id"], project_two["project_id"]],
                    "overlay_id": overlay_two["overlay_id"],
                    "include_role_documents": False,
                },
            ).json()

            cloned = client.post(
                f"/api/library/presets/{preset_one['preset_id']}/clone",
                json={"name": "Preset A Copy"},
            ).json()
            comparison = client.get(
                f"/api/library/presets/{preset_two['preset_id']}/compare/{preset_one['preset_id']}"
            ).json()

        self.assertNotEqual(cloned["preset_id"], preset_one["preset_id"])
        self.assertEqual(cloned["name"], "Preset A Copy")
        self.assertEqual(cloned["project_ids"], preset_one["project_ids"])
        self.assertEqual(cloned["overlay_id"], preset_one["overlay_id"])
        self.assertTrue(cloned["include_role_documents"])
        self.assertEqual(comparison["added_projects"], ["Retrieval Ops"])
        self.assertEqual(comparison["removed_projects"], [])
        self.assertEqual(comparison["left_overlay_name"], "ByteDance")
        self.assertEqual(comparison["right_overlay_name"], "Alibaba")
        self.assertTrue(comparison["overlay_changed"])
        self.assertTrue(comparison["include_role_documents_changed"])
        self.assertEqual(comparison["shared_projects"], ["Agent Console"])

    def test_library_preset_latest_bundle_status_detects_stale_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Pitch",
                    "business_value": "Build agent workflows",
                    "architecture": "React + Python",
                },
            ).json()
            overlay_one = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
                json={"name": "Alibaba", "company": "Alibaba"},
            ).json()
            overlay_two = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/overlays",
                json={"name": "ByteDance", "company": "ByteDance"},
            ).json()
            preset = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/presets",
                json={
                    "name": "Preset A",
                    "project_ids": [project["project_id"]],
                    "overlay_id": overlay_one["overlay_id"],
                    "include_role_documents": True,
                },
            ).json()

            client.post(f"/api/library/presets/{preset['preset_id']}/build-session-payload").json()
            current = client.get(
                f"/api/library/presets/{preset['preset_id']}/latest-bundle-status"
            ).json()

            client.put(
                f"/api/library/projects/{project['project_id']}",
                json={"architecture": "React + Python + SQLite"},
            ).json()
            client.put(
                f"/api/library/presets/{preset['preset_id']}",
                json={
                    "overlay_id": overlay_two["overlay_id"],
                    "include_role_documents": False,
                },
            ).json()
            stale = client.get(
                f"/api/library/presets/{preset['preset_id']}/latest-bundle-status"
            ).json()

        self.assertEqual(current["status"], "current")
        self.assertEqual(current["reasons"], [])
        self.assertEqual(current["latest_bundle"]["preset_id"], preset["preset_id"])
        self.assertEqual(stale["status"], "stale")
        self.assertIn("project_content_updated", stale["reasons"])
        self.assertIn("overlay_changed", stale["reasons"])
        self.assertIn("include_role_documents_changed", stale["reasons"])
        self.assertEqual(stale["stale_project_names"], ["Agent Console"])
        self.assertEqual(stale["latest_bundle"]["overlay_name"], "Alibaba")

    def test_library_authoring_templates_can_be_saved_and_applied_across_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            source_project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
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
                },
            ).json()
            target_project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Bundle Ops"},
            ).json()

            created_template = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/authoring-templates",
                json={
                    "name": "Tradeoff Pack",
                    "description": "Reusable tradeoff template",
                    "source_project_id": source_project["project_id"],
                    "manual_evidence": source_project["manual_evidence"],
                    "manual_metrics": source_project["manual_metrics"],
                    "manual_retrieval_units": source_project["manual_retrieval_units"],
                },
            ).json()
            applied_pack = client.post(
                f"/api/library/projects/{target_project['project_id']}/authoring-pack/apply-template",
                json={
                    "template_id": created_template["template_id"],
                    "mode": "replace",
                },
            ).json()
            refreshed_workspace = client.get(
                f"/api/library/workspaces/{workspace['workspace_id']}"
            ).json()
            refreshed_target = client.get(
                f"/api/library/projects/{target_project['project_id']}"
            ).json()

        self.assertEqual(created_template["name"], "Tradeoff Pack")
        self.assertEqual(created_template["source_project_id"], source_project["project_id"])
        self.assertEqual(len(refreshed_workspace["authoring_templates"]), 1)
        self.assertEqual(applied_pack["summary"]["manual_evidence_count"], 1)
        self.assertEqual(applied_pack["summary"]["manual_metric_count"], 1)
        self.assertEqual(applied_pack["summary"]["manual_retrieval_unit_count"], 1)
        self.assertEqual(refreshed_target["manual_evidence"][0]["title"], "Load Test")
        self.assertEqual(refreshed_target["manual_retrieval_units"][0]["unit_id"], "manual-ru-1")

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

    def test_library_project_authoring_pack_preview_reports_duplicate_ids_and_missing_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()

            preview = client.post(
                f"/api/library/projects/{project['project_id']}/authoring-pack/preview",
                json={
                    "manual_evidence": [
                        {
                            "evidence_id": "shared-proof",
                            "title": "Load Test",
                            "summary": "Benchmarked 100 prompts locally.",
                            "source_ref": "benchmarks/load-test.md",
                        }
                    ],
                    "manual_metrics": [
                        {
                            "evidence_id": "shared-proof",
                            "metric_name": "first_token_latency",
                            "metric_value": "850ms",
                            "baseline": "1.7s",
                            "source_note": "benchmarks/load-test.md",
                        }
                    ],
                    "manual_retrieval_units": [
                        {
                            "unit_id": "tradeoff-1",
                            "unit_type": "tradeoff_reasoning",
                            "question_forms": ["Why this architecture?"],
                            "short_answer": "I optimized for debuggability first.",
                            "long_answer": "Smaller components made retrieval failures easier to inspect.",
                            "supporting_refs": ["shared-proof", "missing-ref"],
                        }
                    ],
                },
            ).json()

        self.assertFalse(preview["validation"]["valid"])
        self.assertIn("shared-proof", "\n".join(preview["validation"]["errors"]))
        self.assertIn("missing-ref", "\n".join(preview["validation"]["errors"]))
        self.assertEqual(preview["summary"]["manual_evidence_count"], 1)
        self.assertEqual(preview["summary"]["manual_metric_count"], 1)
        self.assertEqual(preview["summary"]["manual_retrieval_unit_count"], 1)

    def test_library_project_authoring_pack_replace_roundtrips_manual_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()

            updated = client.put(
                f"/api/library/projects/{project['project_id']}/authoring-pack",
                json={
                    "manual_evidence": [
                        {
                            "evidence_id": "manual-evidence-1",
                            "title": "Load Test",
                            "summary": "Benchmarked 100 prompts locally.",
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
                            "unit_type": "performance_evidence",
                            "question_forms": ["How did you improve latency?"],
                            "short_answer": "I shortened the retrieval path first.",
                            "long_answer": "I moved the strongest evidence closer to the starter path so first token latency dropped quickly.",
                            "key_points": ["latency", "retrieval"],
                            "supporting_refs": ["manual-evidence-1", "manual-metric-1"],
                            "hooks": ["The retrieval router latency was the hardest part."],
                            "safe_claims": ["The system improved first token latency."],
                        }
                    ],
                },
            ).json()
            fetched = client.get(f"/api/library/projects/{project['project_id']}/authoring-pack").json()
            project_after = client.get(f"/api/library/projects/{project['project_id']}").json()

        self.assertTrue(updated["validation"]["valid"])
        self.assertEqual(updated["summary"]["manual_evidence_count"], 1)
        self.assertEqual(updated["summary"]["manual_metric_count"], 1)
        self.assertEqual(updated["summary"]["manual_retrieval_unit_count"], 1)
        self.assertEqual(fetched["manual_evidence"][0]["title"], "Load Test")
        self.assertEqual(fetched["manual_metrics"][0]["metric_name"], "first_token_latency")
        self.assertEqual(fetched["manual_retrieval_units"][0]["supporting_refs"], ["manual-evidence-1", "manual-metric-1"])
        self.assertEqual(project_after["manual_evidence"][0]["title"], "Load Test")
        self.assertEqual(project_after["manual_retrieval_units"][0]["unit_type"], "performance_evidence")

    def test_library_project_authoring_pack_template_can_append_compiled_preview_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={
                    "name": "Agent Console",
                    "pitch_30": "Short pitch",
                    "pitch_90": "Long pitch",
                    "business_value": "Build agent workflows",
                    "architecture": "React + Python orchestrator",
                    "manual_evidence": [
                        {
                            "evidence_id": "manual-existing",
                            "title": "Existing Note",
                            "summary": "Keep this authored evidence.",
                        }
                    ],
                    "documents": [
                        {
                            "path": "README.md",
                            "content": "Latency dropped from 1.8s to 900ms while we simplified the retrieval path.",
                        }
                    ],
                    "code_files": [
                        {
                            "path": "src/workflow.py",
                            "content": "def run():\n    return 'ok'\n",
                        }
                    ],
                },
            ).json()

            client.post(f"/api/workspaces/{workspace['workspace_id']}/compile").json()
            preview = client.get(f"/api/library/projects/{project['project_id']}/compiled-preview").json()
            selected_unit = preview["retrieval_units"][0]
            template = client.post(
                f"/api/library/projects/{project['project_id']}/authoring-pack/template",
                json={
                    "source": "compiled_preview",
                    "mode": "append",
                    "retrieval_unit_ids": [selected_unit["unit_id"]],
                },
            ).json()

        self.assertTrue(template["validation"]["valid"])
        self.assertIn("manual-existing", {item["evidence_id"] for item in template["manual_evidence"]})
        self.assertIn(selected_unit["unit_id"], {item["unit_id"] for item in template["manual_retrieval_units"]})
        generated_ref_ids = {item["evidence_id"] for item in template["manual_evidence"]}
        generated_ref_ids.update(item["evidence_id"] for item in template["manual_metrics"])
        self.assertTrue(set(selected_unit["supporting_refs"]).issubset(generated_ref_ids))

    def test_library_project_authoring_pack_template_requires_compiled_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = TestClient(create_app(workspace_storage_root=Path(tmpdir)))
            workspace = client.post("/api/library/workspaces", json={"name": "Library"}).json()
            project = client.post(
                f"/api/library/workspaces/{workspace['workspace_id']}/projects",
                json={"name": "Agent Console"},
            ).json()

            response = client.post(
                f"/api/library/projects/{project['project_id']}/authoring-pack/template",
                json={"source": "compiled_preview", "mode": "replace"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("compile", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
