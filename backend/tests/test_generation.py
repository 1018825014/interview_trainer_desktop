import unittest

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
