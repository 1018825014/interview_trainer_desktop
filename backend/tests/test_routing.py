import unittest

from interview_trainer.answer_control import AnswerPlan, AnswerState
from interview_trainer.briefing import BriefingBuilder
from interview_trainer.knowledge import KnowledgeCompiler
from interview_trainer.library_compile import LibraryCompiler
from interview_trainer.routing import ContextRouter
from interview_trainer.types import ContextMode


def _knowledge():
    compiler = KnowledgeCompiler()
    return compiler.compile(
        {
            "projects": [
                {
                    "name": "AgentOps Console",
                    "business_value": "给业务同学配置 Agent 工作流。",
                    "documents": [{"content": "项目核心是 Agent 编排、检索和 tracing。"}],
                    "code_files": [
                        {"path": "src/orchestrator/workflow.py", "content": "def run():\n    pass\n"},
                        {"path": "src/retrieval/reranker.py", "content": "def rerank():\n    pass\n"},
                    ],
                }
            ]
        }
    )


class ContextRouterTests(unittest.TestCase):
    def test_detects_project_question(self) -> None:
        knowledge = _knowledge()
        route = ContextRouter().route("介绍一下 AgentOps Console 的架构和关键模块。", knowledge)
        self.assertEqual(route.mode, ContextMode.PROJECT)

    def test_detects_role_question(self) -> None:
        knowledge = _knowledge()
        route = ContextRouter().route("你如何平衡 Agent 系统的 latency 和 evaluation？", knowledge)
        self.assertEqual(route.mode, ContextMode.ROLE)

    def test_detects_hybrid_question(self) -> None:
        knowledge = _knowledge()
        briefing = BriefingBuilder().build(
            company="Test",
            business_context="做 AI Agent 平台",
            job_description="需要熟悉 agent, latency, evaluation",
            knowledge=knowledge,
        )
        route = ContextRouter().route(
            "结合 AgentOps Console 讲讲你怎么做 latency 和 evaluation 的取舍？",
            knowledge,
            briefing,
        )
        self.assertEqual(route.mode, ContextMode.HYBRID)

    def test_tradeoff_question_prefers_retrieval_unit_and_evidence_before_code(self) -> None:
        bundle = LibraryCompiler().compile_workspace(
            {
                "projects": [
                    {
                        "name": "AgentOps Console",
                        "business_value": "Build agent workflows",
                        "pitch_30": "Short pitch",
                        "tradeoffs": ["Chose modular orchestration over one giant workflow"],
                        "documents": [{"path": "README.md", "content": "Latency dropped from 1.8s to 900ms."}],
                        "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run():\n    pass\n"}],
                    }
                ]
            }
        )
        plan = AnswerPlan(
            intent="tradeoff_reasoning",
            retrieve_priority=["RetrievalUnit", "EvidenceCard", "ModuleCard", "CodeChunk"],
            answer_template=["conclusion", "tradeoff", "reason", "upgrade"],
            max_sentences=6,
            need_metrics=False,
            need_code_evidence=False,
            allow_hook=True,
        )

        pack = ContextRouter().build_pack_for_plan(
            question="这个方案最大的 tradeoff 是什么？",
            plan=plan,
            compiled_bundle=bundle,
        )

        self.assertGreaterEqual(len(pack.project_refs), 1)
        self.assertGreaterEqual(len(pack.retrieval_refs), 1)
        self.assertGreaterEqual(len(pack.evidence_refs), 1)
        self.assertLessEqual(len(pack.code_refs), 1)

    def test_hook_aware_retrieval_prefers_unused_hook_unit(self) -> None:
        bundle = LibraryCompiler().compile_workspace(
            {
                "projects": [
                    {
                        "name": "AgentOps Console",
                        "business_value": "Build agent workflows",
                        "pitch_30": "Short pitch",
                        "manual_retrieval_units": [
                            {
                                "unit_id": "manual-ru-1",
                                "unit_type": "tradeoff_reasoning",
                                "question_forms": ["为什么这样设计"],
                                "short_answer": "我先优化可调试性。",
                                "long_answer": "我先把系统拆小，优先保证排障效率。",
                                "key_points": ["调试", "架构"],
                                "supporting_refs": [],
                                "hooks": ["最难的其实是 retrieval router 的误判率。"],
                                "safe_claims": ["系统是为了可调试性设计的。"],
                            },
                            {
                                "unit_id": "manual-ru-2",
                                "unit_type": "tradeoff_reasoning",
                                "question_forms": ["为什么这样设计"],
                                "short_answer": "我优先压住本地检索延迟。",
                                "long_answer": "我当时更在意面试现场的响应速度，所以先做轻量索引。",
                                "key_points": ["延迟", "检索"],
                                "supporting_refs": [],
                                "hooks": ["另一个亮点是 bundle 复用把切换成本降得很低。"],
                                "safe_claims": ["系统优先考虑响应速度。"],
                            },
                        ],
                        "documents": [{"path": "README.md", "content": "Latency dropped from 1.8s to 900ms."}],
                    }
                ]
            }
        )
        plan = AnswerPlan(
            intent="tradeoff_reasoning",
            retrieve_priority=["RetrievalUnit", "EvidenceCard", "Project"],
            answer_template=["conclusion", "tradeoff", "reason", "hook"],
            max_sentences=6,
            need_metrics=False,
            need_code_evidence=False,
            allow_hook=True,
        )

        pack = ContextRouter().build_pack_for_plan(
            question="为什么这样设计？",
            plan=plan,
            compiled_bundle=bundle,
            answer_state=AnswerState(used_hook_ids=["manual-ru-1"]),
        )

        self.assertGreaterEqual(len(pack.hook_refs), 1)
        self.assertEqual(pack.retrieval_refs[0].ref_id, "manual-ru-2")
        self.assertEqual(pack.hook_refs[0].ref_id, "manual-ru-2")


if __name__ == "__main__":
    unittest.main()
