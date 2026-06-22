import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.content_safety_service import (
    ContentSafetyConfigError,
    ContentSafetyProviderError,
    ContentSafetyService,
    TencentTextModerationProvider,
    get_content_safety_runtime_status,
)


class ContentSafetyServiceTest(unittest.TestCase):
    def test_internal_demo_allows_local_provider(self):
        status = get_content_safety_runtime_status(
            deployment_mode="internal_demo",
            provider_name="local",
            access_key="",
            secret_key="",
        )

        self.assertEqual(status["content_safety_status"], "ok")
        self.assertTrue(status["content_safety_configured"])

    def test_external_test_rejects_local_provider(self):
        status = get_content_safety_runtime_status(
            deployment_mode="external_test",
            provider_name="local",
            access_key="",
            secret_key="",
        )

        self.assertEqual(status["content_safety_status"], "error")
        self.assertFalse(status["content_safety_configured"])

    def test_external_test_rejects_remote_provider_without_keys(self):
        with self.assertRaises(ContentSafetyConfigError):
            ContentSafetyService.from_config(
                deployment_mode="external_test",
                provider_name="tencent",
                access_key="",
                secret_key="",
            )

    def test_internal_demo_remote_provider_without_keys_falls_back_to_local(self):
        service = ContentSafetyService.from_config(
            deployment_mode="internal_demo",
            provider_name="tencent",
            access_key="",
            secret_key="",
        )

        self.assertEqual(service.provider_name, "local")
        safe, hits = service.check_text("我想用炸药处理墙面裂缝")
        self.assertFalse(safe)
        self.assertIn("炸药", hits)

    def test_external_test_with_tencent_keys_uses_real_tencent_provider(self):
        service = ContentSafetyService.from_config(
            deployment_mode="external_test",
            provider_name="tencent",
            access_key="secret-id",
            secret_key="secret-key",
        )

        self.assertEqual(service.provider_name, "tencent")

    def test_unsupported_remote_provider_is_rejected_in_external_test(self):
        with self.assertRaises(ContentSafetyConfigError):
            ContentSafetyService.from_config(
                deployment_mode="external_test",
                provider_name="aliyun",
                access_key="access-key",
                secret_key="secret-key",
            )

    def test_tencent_provider_sends_signed_text_moderation_request_and_blocks_review(self):
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            captured["timeout"] = timeout
            return {
                "Response": {
                    "Suggestion": "Review",
                    "Label": "Illegal",
                    "DetailResults": [{"Label": "Illegal", "Suggestion": "Review"}],
                    "RequestId": "request-id",
                }
            }

        provider = TencentTextModerationProvider(
            secret_id="secret-id",
            secret_key="secret-key",
            region="ap-guangzhou",
            transport=fake_transport,
        )

        safe, hits = provider.check("测试文本")

        self.assertFalse(safe)
        self.assertIn("Illegal", hits)
        self.assertEqual(captured["url"], "https://tms.tencentcloudapi.com")
        self.assertEqual(captured["headers"]["X-TC-Action"], "TextModeration")
        self.assertEqual(captured["headers"]["X-TC-Version"], "2020-12-29")
        self.assertIn("TC3-HMAC-SHA256", captured["headers"]["Authorization"])
        self.assertIn("Content", captured["body"])

    def test_tencent_provider_retries_transient_transport_error_then_succeeds(self):
        # Transient network blips (timeout, connection reset) are recoverable —
        # the provider must retry and ultimately succeed.
        calls = {"n": 0}

        def flaky_transport(url, headers, body, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("simulated connection reset")
            return {"Response": {"Suggestion": "Pass", "Label": "", "RequestId": "r"}}

        provider = TencentTextModerationProvider(
            secret_id="secret-id",
            secret_key="secret-key",
            region="ap-guangzhou",
            transport=flaky_transport,
            max_retries=2,
        )

        safe, _hits = provider.check("测试文本")

        self.assertTrue(safe)
        self.assertEqual(calls["n"], 3)

    def test_tencent_provider_does_not_retry_tencent_business_error(self):
        # A successful HTTP round-trip carrying a Tencent business error
        # (AuthFailure, permission denied) is NOT retried — retrying won't help.
        calls = {"n": 0}

        def error_transport(url, headers, body, timeout):
            calls["n"] += 1
            return {"Response": {"Error": {"Code": "AuthFailure", "Message": "bad signature"}}}

        provider = TencentTextModerationProvider(
            secret_id="secret-id",
            secret_key="secret-key",
            region="ap-guangzhou",
            transport=error_transport,
            max_retries=2,
        )

        with self.assertRaises(ContentSafetyProviderError):
            provider.check("测试文本")
        self.assertEqual(calls["n"], 1)

    def test_tencent_provider_raises_after_exhausting_retries(self):
        # Persistent outage still surfaces as ContentSafetyProviderError, but
        # only after max_retries+1 attempts (so diagnosis can map it to 503).
        calls = {"n": 0}

        def always_failing_transport(url, headers, body, timeout):
            calls["n"] += 1
            raise OSError("persistent network down")

        provider = TencentTextModerationProvider(
            secret_id="secret-id",
            secret_key="secret-key",
            region="ap-guangzhou",
            transport=always_failing_transport,
            max_retries=2,
        )

        with self.assertRaises(ContentSafetyProviderError):
            provider.check("测试文本")
        self.assertEqual(calls["n"], 3)


if __name__ == "__main__":
    unittest.main()
