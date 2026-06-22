import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.llm_adapter import ChatResult
from app.services.classification_service import ClassificationService


class CountingClassificationLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, schema=None, options=None):
        self.calls += 1
        return ChatResult(
            content="""{
              "secondary_category": "wall_mold",
              "confidence": 0.88,
              "evidence": ["墙面起皮"],
              "reason": "墙面起皮更接近墙面返潮或发霉场景"
            }""",
            usage={"prompt_tokens": 11, "completion_tokens": 13, "total_tokens": 24},
            latency_ms=9,
            provider="fake-llm",
            model_version="fake-classifier",
            cost_estimate=0.048,
        )


class FailingClassificationLLM:
    def chat(self, messages, schema=None, options=None):
        raise OSError("classifier unavailable")


class ClassificationServiceTest(unittest.TestCase):
    def test_high_confidence_keyword_result_does_not_call_llm(self):
        llm = CountingClassificationLLM()
        service = ClassificationService(llm_adapter=llm)

        fault = service.classify("空调开了半小时还是不制冷，外机不怎么转")

        self.assertEqual(fault.secondary, "ac_not_cooling")
        self.assertEqual(llm.calls, 0)
        self.assertIsNone(service.last_cost_log)

    def test_low_confidence_result_calls_llm_and_records_classification_cost(self):
        llm = CountingClassificationLLM()
        service = ClassificationService(llm_adapter=llm)

        fault = service.classify("墙面起皮了，靠近卫生间")

        self.assertEqual(fault.secondary, "wall_mold")
        self.assertEqual(fault.primary, "wall_floor")
        self.assertEqual(llm.calls, 1)
        self.assertIsNotNone(service.last_cost_log)
        self.assertEqual(service.last_cost_log.capability, "classification")
        self.assertEqual(service.last_model_version, "fake-classifier")
        self.assertEqual(service.last_tokens, 24)
        self.assertEqual(service.last_latency_ms, 9)

    def test_llm_failure_falls_back_to_keyword_result(self):
        service = ClassificationService(llm_adapter=FailingClassificationLLM())

        fault = service.classify("墙面起皮了，靠近卫生间")

        self.assertEqual(fault.secondary, "wall_mold")
        self.assertLess(fault.confidence, service.HIGH_CONFIDENCE_THRESHOLD)
        self.assertIsNone(service.last_cost_log)


if __name__ == "__main__":
    unittest.main()
