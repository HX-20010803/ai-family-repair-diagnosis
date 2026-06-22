import json
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.llm_adapter import OpenAICompatibleLLMAdapter, get_llm_runtime_status


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LLMAdapterTest(unittest.TestCase):
    def test_openai_compatible_response_is_normalized(self):
        payload = {
            "choices": [{"message": {"content": "{\"ok\": true}"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            "model": "deepseek-chat",
        }

        with patch("app.ai.llm_adapter.urlopen", return_value=FakeResponse(payload)) as urlopen:
            adapter = OpenAICompatibleLLMAdapter(
                provider="deepseek",
                api_key="test-key",
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat",
            )
            result = adapter.chat([{"role": "user", "content": "hi"}], schema={"type": "object"})

        self.assertEqual(result.content, "{\"ok\": true}")
        self.assertEqual(result.usage["total_tokens"], 20)
        self.assertEqual(result.provider, "deepseek")
        self.assertEqual(result.model_version, "deepseek-chat")
        self.assertGreaterEqual(result.latency_ms, 0)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer test-key")

    def test_llm_runtime_status_reports_unconfigured_without_keys(self):
        status = get_llm_runtime_status(
            primary_provider="deepseek",
            fallback_provider="qwen",
            deepseek_api_key="",
            qwen_api_key="",
        )

        self.assertFalse(status["llm_configured"])
        self.assertIsNone(status["llm_active_provider"])

    def test_llm_runtime_status_reports_primary_provider_when_key_exists(self):
        status = get_llm_runtime_status(
            primary_provider="deepseek",
            fallback_provider="qwen",
            deepseek_api_key="sk-test",
            qwen_api_key="",
        )

        self.assertTrue(status["llm_configured"])
        self.assertEqual(status["llm_active_provider"], "deepseek")


if __name__ == "__main__":
    unittest.main()
