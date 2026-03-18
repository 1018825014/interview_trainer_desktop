import unittest
from unittest import mock

from interview_trainer.config import GenerationLaneSettings, GenerationSettings
from interview_trainer.generation import OpenAIChatProvider, TemplateLLMProvider, build_dual_draft_composer
from interview_trainer.prompts import PromptBuilder


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

    def test_generate_includes_enable_thinking_when_configured(self) -> None:
        provider = OpenAIChatProvider(
            endpoint=GenerationLaneSettings(
                provider="openai",
                api_key="test-key",
                model="qwen3.5-flash",
                enable_thinking=False,
            ),
            prompt_builder=PromptBuilder(),
            level="starter",
        )
        pack = mock.Mock(
            profile_refs=[],
            project_refs=[],
            module_refs=[],
            code_refs=[],
            role_refs=[],
        )
        with (
            mock.patch.object(provider.prompt_builder, "build_messages", return_value=[]),
            mock.patch.object(
                provider,
                "_call_chat_completions",
                return_value='{"text":"ok","bullets":[]}',
            ) as call_chat,
        ):
            provider.full(
                turn_id="turn-1",
                question="test question",
                route=mock.Mock(),
                pack=pack,
                briefing=mock.Mock(),
                candidate_history=[],
            )

        payload = call_chat.call_args.args[0]
        self.assertIn("enable_thinking", payload)
        self.assertFalse(payload["enable_thinking"])

    def test_generate_omits_enable_thinking_when_unset(self) -> None:
        provider = OpenAIChatProvider(
            endpoint=GenerationLaneSettings(provider="openai", api_key="test-key", model="qwen-flash"),
            prompt_builder=PromptBuilder(),
            level="starter",
        )
        pack = mock.Mock(
            profile_refs=[],
            project_refs=[],
            module_refs=[],
            code_refs=[],
            role_refs=[],
        )
        with (
            mock.patch.object(provider.prompt_builder, "build_messages", return_value=[]),
            mock.patch.object(
                provider,
                "_call_chat_completions",
                return_value='{"text":"ok","bullets":[]}',
            ) as call_chat,
        ):
            provider.full(
                turn_id="turn-1",
                question="test question",
                route=mock.Mock(),
                pack=pack,
                briefing=mock.Mock(),
                candidate_history=[],
            )

        payload = call_chat.call_args.args[0]
        self.assertNotIn("enable_thinking", payload)

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


if __name__ == "__main__":
    unittest.main()
