from __future__ import annotations

import os
import unittest
from unittest import mock

from interview_trainer.config import GenerationSettings, TranscriptionSettings


class GenerationSettingsTests(unittest.TestCase):
    def test_generation_settings_prefer_llm_specific_env_vars(self) -> None:
        env = {
            "INTERVIEW_TRAINER_LLM_PROVIDER": "openai",
            "INTERVIEW_TRAINER_LLM_API_KEY": "llm-key",
            "INTERVIEW_TRAINER_LLM_BASE_URL": "https://example.com/v1",
            "OPENAI_API_KEY": "shared-key",
            "OPENAI_BASE_URL": "https://shared.example/v1",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            settings = GenerationSettings.from_env()

        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.openai_api_key, "llm-key")
        self.assertEqual(settings.openai_base_url, "https://example.com/v1")
        self.assertEqual(settings.fast_provider, "openai")
        self.assertEqual(settings.smart_provider, "openai")
        self.assertEqual(settings.fast_api_key, "llm-key")
        self.assertEqual(settings.smart_api_key, "llm-key")

    def test_generation_settings_fallback_to_shared_openai_env_vars(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "INTERVIEW_TRAINER_LLM_API_KEY": "",
                "INTERVIEW_TRAINER_LLM_BASE_URL": "",
                "OPENAI_API_KEY": "shared-key",
                "OPENAI_BASE_URL": "https://shared.example/v1",
            },
            clear=False,
        ):
            settings = GenerationSettings.from_env()

        self.assertEqual(settings.openai_api_key, "shared-key")
        self.assertEqual(settings.openai_base_url, "https://shared.example/v1")

    def test_generation_settings_allow_lane_specific_overrides(self) -> None:
        env = {
            "INTERVIEW_TRAINER_LLM_PROVIDER": "openai",
            "INTERVIEW_TRAINER_LLM_API_KEY": "shared-key",
            "INTERVIEW_TRAINER_LLM_BASE_URL": "https://shared.example/v1",
            "INTERVIEW_TRAINER_REQUEST_TIMEOUT_S": "30",
            "INTERVIEW_TRAINER_FAST_PROVIDER": "template",
            "INTERVIEW_TRAINER_FAST_MODEL": "template-fast",
            "INTERVIEW_TRAINER_SMART_PROVIDER": "openai",
            "INTERVIEW_TRAINER_SMART_API_KEY": "smart-key",
            "INTERVIEW_TRAINER_SMART_BASE_URL": "https://smart.example/v1",
            "INTERVIEW_TRAINER_SMART_TIMEOUT_S": "45",
            "INTERVIEW_TRAINER_SMART_MODEL": "smart-model",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            settings = GenerationSettings.from_env()

        self.assertEqual(settings.fast_provider, "template")
        self.assertEqual(settings.fast_api_key, "shared-key")
        self.assertEqual(settings.fast_lane.provider, "template")
        self.assertFalse(settings.fast_lane.use_openai)
        self.assertEqual(settings.smart_provider, "openai")
        self.assertEqual(settings.smart_api_key, "smart-key")
        self.assertEqual(settings.smart_base_url, "https://smart.example/v1")
        self.assertEqual(settings.smart_request_timeout_s, 45.0)
        self.assertTrue(settings.smart_lane.use_openai)


class TranscriptionSettingsTests(unittest.TestCase):
    def test_transcription_settings_read_alibaba_realtime_env_vars(self) -> None:
        env = {
            "INTERVIEW_TRAINER_ASR_PROVIDER": "alibaba_realtime",
            "INTERVIEW_TRAINER_ASR_MODEL": "fun-asr-realtime-2026-02-28",
            "INTERVIEW_TRAINER_ASR_LANGUAGE": "zh",
            "INTERVIEW_TRAINER_ALIBABA_API_KEY": "dash-key",
            "INTERVIEW_TRAINER_ALIBABA_WS_URL": "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
            "INTERVIEW_TRAINER_ALIBABA_APP_KEY": "app-key",
            "INTERVIEW_TRAINER_ALIBABA_VOCABULARY_ID": "vocab-agent-terms",
            "INTERVIEW_TRAINER_ALIBABA_HOTWORDS": "RAG,MCP,embedding,reranker,tool calling",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            settings = TranscriptionSettings.from_env()

        self.assertEqual(settings.provider, "alibaba_realtime")
        self.assertEqual(settings.model, "fun-asr-realtime-2026-02-28")
        self.assertEqual(settings.language, "zh")
        self.assertEqual(settings.alibaba_api_key, "dash-key")
        self.assertEqual(settings.alibaba_ws_url, "wss://dashscope.aliyuncs.com/api-ws/v1/inference")
        self.assertEqual(settings.alibaba_app_key, "app-key")
        self.assertEqual(settings.alibaba_vocabulary_id, "vocab-agent-terms")
        self.assertEqual(
            settings.alibaba_hotwords,
            ["RAG", "MCP", "embedding", "reranker", "tool calling"],
        )
        self.assertTrue(settings.use_alibaba_realtime)
        self.assertTrue(settings.use_realtime_stream)


if __name__ == "__main__":
    unittest.main()
