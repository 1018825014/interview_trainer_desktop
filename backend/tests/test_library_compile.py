from __future__ import annotations

import unittest

from interview_trainer.library_compile import LibraryCompiler


class LibraryCompilerTests(unittest.TestCase):
    def test_compile_project_creates_retrieval_units_and_metric_evidence(self) -> None:
        compiler = LibraryCompiler()

        bundle = compiler.compile_workspace(
            {
                "profile": {"headline": "AI engineer"},
                "projects": [
                    {
                        "project_id": "project-agent-console",
                        "name": "Agent Console",
                        "business_value": "Help teams build agent workflows",
                        "architecture": "React UI + Python orchestrator + retrieval",
                        "pitch_30": "Agent Console is the project I use to explain orchestration tradeoffs.",
                        "tradeoffs": ["Chose modular orchestration over one giant workflow"],
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
                    }
                ],
            }
        )

        self.assertGreaterEqual(len(bundle.retrieval_units), 1)
        self.assertGreaterEqual(len(bundle.evidence_cards), 1)
        self.assertGreaterEqual(len(bundle.metric_evidence), 1)
        self.assertIn("project_intro", {item.unit_type for item in bundle.retrieval_units})
        self.assertEqual(bundle.metric_evidence[0].metric_name, "latency")
        self.assertEqual(bundle.metric_evidence[0].baseline, "1.8s")
        self.assertEqual(bundle.metric_evidence[0].metric_value, "900ms")

    def test_compile_project_merges_manual_authoring_materials(self) -> None:
        compiler = LibraryCompiler()

        bundle = compiler.compile_workspace(
            {
                "profile": {"headline": "AI engineer"},
                "projects": [
                    {
                        "project_id": "project-agent-console",
                        "name": "Agent Console",
                        "business_value": "Help teams build agent workflows",
                        "architecture": "React UI + Python orchestrator + retrieval",
                        "pitch_30": "Agent Console is the project I use to explain orchestration tradeoffs.",
                        "pitch_90": "Longer project pitch.",
                        "tradeoffs": ["Chose modular orchestration over one giant workflow"],
                        "manual_evidence": [
                            {
                                "evidence_id": "manual-evidence-1",
                                "evidence_type": "benchmark",
                                "title": "Load Test",
                                "summary": "Benchmarked 100 interview-style queries locally.",
                                "source_kind": "manual_note",
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
                                "confidence": "high",
                            }
                        ],
                        "manual_retrieval_units": [
                            {
                                "unit_id": "manual-ru-1",
                                "unit_type": "tradeoff_reasoning",
                                "question_forms": ["Why this architecture?"],
                                "short_answer": "I optimized for debuggability first.",
                                "long_answer": "I chose smaller components so I could reason about retrieval failures quickly.",
                                "key_points": ["debuggability", "latency", "incremental rollout"],
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
                    }
                ],
            }
        )

        self.assertIn("manual-evidence-1", {item.evidence_id for item in bundle.evidence_cards})
        self.assertIn("manual-metric-1", {item.evidence_id for item in bundle.metric_evidence})
        self.assertIn("manual-ru-1", {item.unit_id for item in bundle.retrieval_units})
        manual_unit = next(item for item in bundle.retrieval_units if item.unit_id == "manual-ru-1")
        self.assertEqual(manual_unit.supporting_refs, ["manual-evidence-1", "manual-metric-1"])
        self.assertIn("The retrieval router was the hardest part.", manual_unit.hooks)


if __name__ == "__main__":
    unittest.main()
