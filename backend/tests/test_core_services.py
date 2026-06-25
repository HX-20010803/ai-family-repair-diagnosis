import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.diagnosis_service import DiagnosisService
from app.services.content_safety_service import ContentSafetyProviderError, ContentSafetyService, LocalKeywordProvider
from app.services.price_service import PriceService
from app.services.risk_service import RiskService
from app.api.v1.diagnosis import _response_to_dict
from app.ai.llm_adapter import ChatResult
from app.domain import DiagnosisResponse, DiagnosisSession
from fastapi import HTTPException


class FakeLLMAdapter:
    def chat(self, messages, schema=None, options=None):
        return ChatResult(
            content="""{
              "possible_causes": ["线路短路", "插座老化"],
              "recommended_actions": ["关闭空气开关", "联系专业电工"],
              "forbidden_actions": ["不要继续通电"],
              "self_check_steps": [],
              "need_professional": "yes",
              "need_professional_reason": "涉及电气安全",
              "uncertainty_note": null
            }""",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=12,
            provider="fake-llm",
            model_version="fake-model",
            cost_estimate=0.06,
        )


class FailingLLMAdapter:
    def chat(self, messages, schema=None, options=None):
        raise OSError("network unavailable")


class FailingContentSafetyService:
    provider_name = "tencent"

    def check_text(self, text):
        raise ContentSafetyProviderError("Tencent content safety failed: AuthFailure.UnauthorizedOperation")


def local_content_safety_service():
    return ContentSafetyService(LocalKeywordProvider())


class RiskServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = RiskService()

    def test_gas_smell_is_forced_to_s_level(self):
        risk = self.service.assess("燃气灶打不着火，还有明显燃气味")

        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "gas")
        self.assertFalse(risk.requires_confirmation)

    def test_explicit_real_risk_without_uncertain_word_does_not_require_confirmation(self):
        risk = self.service.assess("插座冒烟了")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "electric_smoke")
        self.assertFalse(risk.requires_confirmation)

    def test_explicit_negation_does_not_raise_to_s_level(self):
        risk = self.service.assess("热水器不出热水，但是没有燃气味")

        self.assertFalse(risk.triggered)
        self.assertIsNone(risk.level)

    def test_uncertain_risk_keeps_high_risk_prompt(self):
        risk = self.service.assess("我担心是不是燃气泄漏")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertTrue(risk.requires_confirmation)

    def test_water_reaching_socket_is_high_risk(self):
        risk = self.service.assess("阳台漏水流到插座下面了，现在墙上都是湿的")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "water_near_electric")

    def test_trapped_child_is_high_risk(self):
        risk = self.service.assess("指纹锁坏了，小孩一个人在家出不来")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "locked_in")

    def test_gas_appliance_with_generic_smell_is_high_risk(self):
        risk = self.service.assess("燃气灶关了以后还有气味")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "gas")

    def test_high_floor_broken_window_is_high_risk(self):
        risk = self.service.assess("阳台窗户玻璃裂了，高层会不会掉")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "falling_object")

    def test_appliance_tripping_breaker_is_high_risk(self):
        risk = self.service.assess("空调开机后跳闸，重新开又跳")

        self.assertTrue(risk.triggered)
        self.assertEqual(risk.level, "S")
        self.assertEqual(risk.risk_type, "electric")


class PriceServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = PriceService()

    def test_missing_city_tier_defaults_to_other(self):
        price = self.service.match("water_leak", city_tier=None)

        self.assertTrue(price.has_reliable_price)
        self.assertEqual(price.city_tier, "other")
        self.assertIn("50-150", price.range)


class DiagnosisServiceTest(unittest.TestCase):
    def setUp(self):
        # 用 FakeLLMAdapter 避免本地有 DeepSeek key 时 build 出真实 LLM，
        # 导致 conversation_service 走真实模型（慢/花钱/不稳）。
        # FakeLLM 的 content 是结构化 JSON（无 reply 字段）→ conversation 自动 fallback 到硬编码追问。
        self.service = DiagnosisService(llm_adapter=FakeLLMAdapter(), content_safety_service=local_content_safety_service())

    def test_short_low_context_input_returns_followup(self):
        """短输入触发追问：LLM chat 或兜底 questions 都算追问。"""
        response = self.service.handle_message(
            anonymous_token="demo-token",
            text="空调不制冷",
        )

        self.assertIn(response.type, {"chat", "questions"})
        self.assertEqual(response.session.question_round_count, 1)

    def test_toilet_blocked_routes_to_drain_followup(self):
        """马桶 → drain_blocked 分类，追问内容含"堵塞"不含"漏水"（water_leak）。"""
        response = self.service.handle_message(
            anonymous_token="demo-token",
            text="马桶堵了水下不去，应该怎么办",
        )
        self.assertIn(response.type, {"chat", "questions"})
        content = (response.message or "") + "\n".join(response.questions)
        self.assertIn("堵塞", content)
        self.assertNotIn("漏水", content)

    def test_followup_does_not_get_stuck(self):
        """多轮不会卡住：第二轮一定有响应（chat/questions/result 之一），不返回空。"""
        first = self.service.handle_message(
            anonymous_token="demo-token",
            text="马桶堵了水下不去，应该怎么办",
        )
        self.assertIn(first.type, {"chat", "questions"})
        self.assertEqual(first.session.question_round_count, 1)

        second = self.service.handle_message(
            anonymous_token="demo-token",
            text="马桶堵了水下不去，应该怎么办",
            session_id=first.session.id,
        )
        self.assertIn(second.type, {"chat", "questions", "result"})

    def test_second_round_short_answer_does_not_get_stuck(self):
        """外测 bug 修复：第一轮追问后用户短回答（如"电热水器"），
        第二轮一定有响应（不卡住），且不返回空 questions。"""
        first = self.service.handle_message(
            anonymous_token="demo-token",
            text="热水器不出热水",
        )
        self.assertIn(first.type, {"chat", "questions"})

        second = self.service.handle_message(
            anonymous_token="demo-token",
            text="电热水器",
            session_id=first.session.id,
        )
        self.assertIn(second.type, {"chat", "questions", "result"}, "第二轮不应卡住")

    def test_session_restore_recovers_asked_history(self):
        """Messages restored from the DB carry joined question strings without a
        `type` marker; `_collect_asked` must still recover them via pool
        matching, and ignore non-question assistant text (e.g. a stored id)."""
        session = DiagnosisSession(
            anonymous_token="demo-token",
            original_input_json={},
            question_round_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.messages.append(
            {"role": "assistant", "content": "堵塞位置在哪里？\n是否有返水或完全不下水？"}
        )
        session.messages.append({"role": "user", "content": "马桶"})
        session.messages.append({"role": "assistant", "content": "diag_result_abc"})

        asked = self.service._collect_asked(session)

        self.assertIn("堵塞位置在哪里？", asked)
        self.assertIn("是否有返水或完全不下水？", asked)
        self.assertNotIn("diag_result_abc", asked)

    def test_classifier_handles_common_v011_boundary_phrases(self):
        cases = [
            ("家里配电箱有焦味，还嗡嗡响", "circuit_trip"),
            ("门把手松了，开关门很费劲", "lock_failure"),
            ("墙面霉味很重但看不到明显霉斑", "wall_mold"),
            ("厨房下水道反味，开窗也散不掉", "floor_drain_smell"),
            ("推拉门很难推，轨道像卡住了", "window_hardware"),
            ("燃气管附近有刺鼻味，能不能自己拧紧", "range_hood_gas_stove"),
        ]

        for text, expected_secondary in cases:
            with self.subTest(text=text):
                self.assertEqual(self.service._classify(text).secondary, expected_secondary)

    def test_high_risk_input_returns_structured_result(self):
        response = self.service.handle_message(
            anonymous_token="demo-token",
            text="插座发黑还冒烟了，现在还能继续用吗",
        )

        self.assertEqual(response.type, "result")
        self.assertEqual(response.result.urgency.level, "S")
        self.assertGreaterEqual(len(response.result.forbidden_actions), 1)
        self.assertEqual(response.result.fault_type.secondary, "circuit_trip")

    def test_configured_llm_adapter_overrides_template_sections(self):
        service = DiagnosisService(llm_adapter=FakeLLMAdapter(), content_safety_service=local_content_safety_service())

        response = service.handle_message(
            anonymous_token="demo-token",
            text="插座发黑还冒烟了，现在还能继续用吗",
        )

        self.assertEqual(response.result.model_provider, "fake-llm")
        self.assertEqual(response.result.model_version, "fake-model")
        self.assertEqual(response.result.possible_causes[0], "线路短路")
        self.assertEqual(response.result.cost_total, 0.06)

    def test_failed_llm_call_falls_back_to_local_template(self):
        service = DiagnosisService(llm_adapter=FailingLLMAdapter(), content_safety_service=local_content_safety_service())

        response = service.handle_message(
            anonymous_token="demo-token",
            text="插座发黑还冒烟了，现在还能继续用吗",
        )

        self.assertEqual(response.type, "result")
        self.assertEqual(response.result.model_provider, "local-template")
        self.assertEqual(response.result.model_version, "rules-template-v1")

    def test_content_safety_provider_failure_returns_controlled_blocked_response(self):
        service = DiagnosisService(llm_adapter=None, content_safety_service=local_content_safety_service())
        service.content_safety_service = FailingContentSafetyService()

        response = service.handle_message(
            anonymous_token="demo-token",
            text="toilet blocked and water is not draining",
        )

        self.assertEqual(response.type, "blocked")
        self.assertEqual(response.error_code, "CONTENT_SAFETY_UNAVAILABLE")

    def test_content_safety_unavailable_maps_to_http_503(self):
        response = DiagnosisResponse(
            type="blocked",
            session=DiagnosisSession(),
            error_code="CONTENT_SAFETY_UNAVAILABLE",
            safety_notice="content safety unavailable",
        )

        with self.assertRaises(HTTPException) as ctx:
            _response_to_dict(response)

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail["code"], "CONTENT_SAFETY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
