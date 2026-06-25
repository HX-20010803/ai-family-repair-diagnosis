import unittest
from pathlib import Path
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.llm_adapter import ChatResult
from app.domain import DiagnosisSession, FaultType
from app.services.conversation_service import ConversationService, ConversationFallback


class FakeLLM:
    def __init__(self, content="", raise_exc=None):
        self._content = content
        self._raise = raise_exc

    def chat(self, messages, schema=None, options=None):
        if self._raise:
            raise self._raise
        return ChatResult(
            content=self._content,
            usage={"total_tokens": 30},
            latency_ms=100,
            provider="fake",
            model_version="fake-v1",
            cost_estimate=0.01,
        )


def _session():
    s = DiagnosisSession(
        anonymous_token="t",
        original_input_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return s


def _fault():
    return FaultType(primary="家电维修", secondary="water_heater_failure", confidence=0.9)


class _Risk:
    def __init__(self, triggered=False, action=None):
        self.triggered = triggered
        self.action = action


class ConversationServiceTest(unittest.TestCase):
    def test_chat_reply_when_not_complete(self):
        llm = FakeLLM(
            '{"reply":"电热水器是吧，那通电后指示灯亮吗？","complete":false,"fields":{"热水器类型":"电"}}'
        )
        reply = ConversationService(llm).next_reply(
            _session_with("热水器不出热水"), _fault(), _Risk(),
            ["热水器类型(燃气/电/太阳能)", "是否有故障码", "是否有燃气味或焦味", "使用年限"],
        )
        self.assertEqual(reply.type, "chat")
        self.assertIn("指示灯", reply.text)
        self.assertEqual(reply.extracted_fields.get("热水器类型"), "电")

    def test_complete_reply_when_fields_satisfied(self):
        llm = FakeLLM(
            '{"reply":"初步看是温控器老化，建议找师傅。","complete":true,"fields":{"热水器类型":"电","使用年限":"5年"}}'
        )
        reply = ConversationService(llm).next_reply(
            _session_with("电热水器用了5年不出热水"), _fault(), _Risk(),
            ["热水器类型(燃气/电/太阳能)", "使用年限"],
        )
        self.assertEqual(reply.type, "complete")

    def test_high_risk_skips_llm_and_completes(self):
        called = {"n": 0}

        class LLM:
            def chat(self, *a, **k):
                called["n"] += 1
                raise AssertionError("高风险不应调 LLM")

        reply = ConversationService(LLM()).next_reply(
            _session_with("好像有燃气味"), _fault(),
            _Risk(triggered=True, action="立即开窗通风，关闭燃气阀门，撤离并联系燃气公司。"),
            ["热水器类型"],
        )
        self.assertEqual(reply.type, "complete")
        self.assertIn("通风", reply.text)
        self.assertEqual(called["n"], 0)

    def test_fallback_on_llm_failure(self):
        llm = FakeLLM("", raise_exc=RuntimeError("timeout"))
        with self.assertRaises(ConversationFallback):
            ConversationService(llm).next_reply(
                _session_with("热水器不出热水"), _fault(), _Risk(), ["热水器类型"]
            )

    def test_fallback_on_empty_reply(self):
        llm = FakeLLM('{"reply":"   ","complete":false,"fields":{}}')
        with self.assertRaises(ConversationFallback):
            ConversationService(llm).next_reply(
                _session_with("热水器不出热水"), _fault(), _Risk(), ["热水器类型"]
            )

    def test_fallback_on_bad_json(self):
        llm = FakeLLM("这不是JSON")
        with self.assertRaises(ConversationFallback):
            ConversationService(llm).next_reply(
                _session_with("热水器不出热水"), _fault(), _Risk(), ["热水器类型"]
            )


def _session_with(text):
    s = _session()
    s.messages.append({"role": "user", "content": text})
    return s


if __name__ == "__main__":
    unittest.main()
