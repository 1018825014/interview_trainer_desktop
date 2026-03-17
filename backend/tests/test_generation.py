import unittest

from interview_trainer.answer_control import AnswerPlan, AnswerState
from interview_trainer.config import GenerationLaneSettings, GenerationSettings
from interview_trainer.generation import OpenAIChatProvider, TemplateLLMProvider, build_dual_draft_composer
from interview_trainer.prompts import PromptBuilder
from interview_trainer.types import ContextMode, ContextRoute, EvidenceRef, KnowledgePack, SessionBriefing


class OpenAIChatProviderTests(unittest.TestCase):
    def test_extract_partial_text_from_json_fragment(self) -> None:
        provider = OpenAIChatProvider(
            endpoint=GenerationLaneSettings(provider="openai", api_key="test-key", model="gpt-test"),
            prompt_builder=PromptBuilder(),
            level="starter",
        )

        partial = provider._extract_partial_text('{"text":"这是一个流式起手句')

        self.assertEqual(partial, "这是一个流式起手句")

    def test_extract_stream_delta_from_chunk_payload(self) -> None:
        delta = OpenAIChatProvider._extract_stream_delta(
            {
                "choices": [
                    {
                        "delta": {
                            "content": "hello",
                        }
                    }
                ]
            }
        )

        self.assertEqual(delta, "hello")

    def test_builder_supports_mixed_lane_providers(self) -> None:
        composer = build_dual_draft_composer(
            GenerationSettings(
                provider="template",
                fast_provider="template",
                fast_model="template-fast",
                smart_provider="openai",
                smart_api_key="smart-key",
                smart_base_url="https://example.com/v1",
                smart_model="smart-model",
            )
        )

        self.assertIsInstance(composer.fast_provider, TemplateLLMProvider)
        self.assertIsInstance(composer.smart_provider, OpenAIChatProvider)

    def test_prompt_builder_includes_retrieval_and_evidence_before_code(self) -> None:
        builder = PromptBuilder()
        messages = builder.build_messages(
            level="full",
            question="What is the main tradeoff?",
            route=ContextRoute(mode=ContextMode.PROJECT, reason="project question"),
            pack=KnowledgePack(
                retrieval_refs=[EvidenceRef(ref_id="ru-1", label="Tradeoff Unit", kind="retrieval", snippet="Modular orchestration")],
                evidence_refs=[EvidenceRef(ref_id="ev-1", label="README.md", kind="evidence", snippet="Latency dropped from 1.8s to 900ms")],
                code_refs=[EvidenceRef(ref_id="code-1", label="workflow.py", kind="code", snippet="def run(): pass")],
            ),
            briefing=SessionBriefing(
                company="Alibaba",
                business_context="agent platform",
                job_description="agent tradeoff",
                priority_projects=["AgentOps Console"],
                focus_topics=["agent", "tradeoff"],
                style_bias=["先结论后展开"],
                likely_questions=[],
            ),
            candidate_history=[],
            answer_plan=AnswerPlan(
                intent="tradeoff_reasoning",
                retrieve_priority=["RetrievalUnit", "EvidenceCard", "CodeChunk"],
                answer_template=["conclusion", "tradeoff", "reason", "upgrade"],
                max_sentences=6,
                need_metrics=False,
                need_code_evidence=False,
                allow_hook=True,
            ),
            answer_state=AnswerState(active_project_id="agentops-console", followup_thread="tradeoff_reasoning"),
        )
        user_message = messages[1]["content"]

        self.assertIn("[retrieval] Tradeoff Unit", user_message)
        self.assertIn("[evidence] README.md", user_message)
        self.assertIn("Allow hook: True", user_message)
        self.assertLess(user_message.index("[retrieval]"), user_message.index("[code]"))


if __name__ == "__main__":
    unittest.main()
