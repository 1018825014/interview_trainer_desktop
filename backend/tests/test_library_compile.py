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


if __name__ == "__main__":
    unittest.main()
