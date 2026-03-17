from __future__ import annotations

import os
import unittest
from unittest import mock

from interview_trainer.config import GenerationSettings


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


if __name__ == "__main__":
    unittest.main()
