from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.domain import (
    DiagnosisResponse,
    DiagnosisResult,
    DiagnosisSession,
    FaultType,
    PriceReference,
    Urgency,
)
from app.ai.llm_adapter import LLMAdapter, build_llm_adapter_from_env
from app.ai.output_parser import OutputParseError, parse_json_object
from app.ai.prompt_templates import DIAGNOSIS_SYSTEM_PROMPT
from app.services.content_safety_service import ContentSafetyProviderError, ContentSafetyService
from app.services.classification_service import ClassificationService
from app.services.cost_service import CostService
from app.services.price_service import PriceService
from app.services.question_service import QuestionService
from app.services.rag_service import RagService
from app.services.risk_service import RiskService
from app.repositories.diagnosis_repository import DiagnosisRepository


class DiagnosisService:
    """In-memory MVP orchestration aligned to TECH §4.2.

    This service is intentionally dependency-light for the first development
    slice. Persistence and real LLM calls are attached through the same public
    API once database and provider credentials are available.
    """

    DAILY_FULL_DIAGNOSIS_LIMIT = 3

    def __init__(
        self,
        repository: DiagnosisRepository | None = None,
        llm_adapter: LLMAdapter | None = None,
        content_safety_service: ContentSafetyService | None = None,
    ):
        self.sessions: dict[str, DiagnosisSession] = {}
        self.repository = repository
        self.llm_adapter = llm_adapter if llm_adapter is not None else build_llm_adapter_from_env()
        self._last_cost_log = None
        self.classification_service = ClassificationService(self.llm_adapter)
        self.risk_service = RiskService()
        self.question_service = QuestionService()
        self.price_service = PriceService()
        self.rag_service = RagService()
        self.content_safety_service = content_safety_service or ContentSafetyService()
        self.cost_service = CostService()

    def handle_message(
        self,
        anonymous_token: str,
        text: str,
        session_id: str | None = None,
        city_tier: str | None = None,
    ) -> DiagnosisResponse:
        session = self._get_or_create_session(anonymous_token, text, session_id)
        session.messages.append({"role": "user", "content": text, "created_at": datetime.now(timezone.utc).isoformat()})
        session.updated_at = datetime.now(timezone.utc)
        self._persist_session_and_message(session, "user", text)

        try:
            safe, hits = self.content_safety_service.check_text(text)
        except ContentSafetyProviderError as exc:
            return self._content_safety_unavailable(session, "user_message", exc)
        if self.repository:
            self.repository.add_content_safety_log(
                session_id=session.id,
                content_source="user_message",
                result="passed" if safe else "blocked",
                hit_categories=hits,
                provider=self.content_safety_service.provider_name,
            )
        if not safe:
            if self.repository:
                self.repository.commit()
            return DiagnosisResponse(
                type="blocked",
                session=session,
                error_code="CONTENT_UNSAFE",
                safety_notice="输入内容未通过安全审核，请重新描述家庭维修问题。",
            )

        normalized = self._normalize(text)
        fault_type = self.classification_service.classify(normalized)
        risk = self.risk_service.assess(normalized)
        self._persist_classification_cost(session)

        asked = self._collect_asked(session)
        if self.question_service.should_ask(
            normalized,
            fault_type.secondary,
            session.question_round_count,
            high_risk=risk.triggered,
        ):
            questions = self.question_service.next_questions(fault_type.secondary, asked=asked)
            if questions:
                # 还有没问过的问题，继续追问
                session.question_round_count += 1
                session.messages.append({"role": "assistant", "type": "questions", "content": questions})
                if self.repository:
                    self.repository.update_session(session)
                    self.repository.add_message(session.id, "assistant", "\n".join(questions))
                    self.repository.commit()
                return DiagnosisResponse(type="questions", session=session, questions=questions)
            # 所有问题都问过了，信息足够，落到下方生成结果（避免空 questions 卡住前端）

        if self.repository and self.repository.get_today_full_diagnosis_count(anonymous_token) >= self.DAILY_FULL_DIAGNOSIS_LIMIT:
            session.status = "cancelled"
            self.repository.update_session(session)
            self.repository.add_message(session.id, "assistant", "QUOTA_EXCEEDED")
            self.repository.commit()
            return DiagnosisResponse(
                type="blocked",
                session=session,
                error_code="QUOTA_EXCEEDED",
                safety_notice="今日免费完整诊断次数已用完，请明天再试。",
            )

        result = self._build_result(session, normalized, fault_type, risk, city_tier)
        try:
            output_safe, output_hits = self.content_safety_service.check_text(self._result_text_for_safety(result))
        except ContentSafetyProviderError as exc:
            return self._content_safety_unavailable(session, "ai_output", exc)
        if self.repository:
            self.repository.add_content_safety_log(
                session_id=session.id,
                content_source="ai_output",
                result="passed" if output_safe else "blocked",
                hit_categories=output_hits,
                provider=self.content_safety_service.provider_name,
            )
        if not output_safe:
            if self.repository:
                self.repository.commit()
            return DiagnosisResponse(
                type="blocked",
                session=session,
                error_code="OUTPUT_UNSAFE",
                safety_notice="AI 输出未通过安全审核，请补充描述后重试或联系专业人员。",
            )
        session.status = "completed"
        session.messages.append({"role": "assistant", "type": "result", "content": result.id})
        if self.repository:
            self.repository.update_session(session)
            self.repository.save_result(result)
            self.repository.increment_today_full_diagnosis_count(anonymous_token)
            self.repository.add_cost_log(
                session.id,
                self._last_cost_log or self.cost_service.estimate_template_call(),
                model_version=result.model_version,
            )
            self.repository.add_message(session.id, "assistant", result.id)
            self.repository.commit()
        return DiagnosisResponse(type="result", session=session, result=result, safety_notice=risk.action)

    def _content_safety_unavailable(
        self,
        session: DiagnosisSession,
        content_source: str,
        exc: ContentSafetyProviderError,
    ) -> DiagnosisResponse:
        if self.repository:
            self.repository.add_content_safety_log(
                session_id=session.id,
                content_source=content_source,
                result="error",
                hit_categories=[str(exc)[:200]],
                provider=self.content_safety_service.provider_name,
            )
            self.repository.commit()
        return DiagnosisResponse(
            type="blocked",
            session=session,
            error_code="CONTENT_SAFETY_UNAVAILABLE",
            safety_notice="内容安全服务暂时不可用，请稍后重试或联系管理员检查供应商权限。",
        )

    def _get_or_create_session(self, anonymous_token: str, text: str, session_id: str | None) -> DiagnosisSession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        if session_id and self.repository:
            persisted = self.repository.get_session(session_id)
            if persisted:
                session = DiagnosisSession(
                    id=persisted.id,
                    anonymous_token=persisted.anonymous_token,
                    original_input_json=persisted.original_input_json,
                    question_round_count=persisted.question_round_count,
                    status=persisted.status,
                )
                # Restore message history so follow-up questions can deduplicate
                # against what was already asked. DiagnosisMessage rows only keep
                # role + content (no `type`); `_collect_asked` matches against the
                # QuestionService question pool to recover the asked set.
                for message in self.repository.list_messages(session_id):
                    session.messages.append({"role": message.role, "content": message.content})
                self.sessions[session.id] = session
                return session

        session = DiagnosisSession(
            anonymous_token=anonymous_token,
            original_input_json={"type": "text", "text": text},
        )
        self.sessions[session.id] = session
        if self.repository:
            self.repository.create_session(session)
        return session

    def _collect_asked(self, session: DiagnosisSession) -> list[str]:
        """Collect previously asked follow-up questions from session history.

        Works for both in-memory sessions (messages carry typed content lists)
        and sessions restored from the database (messages carry joined content
        strings without the `type` marker). Any assistant content that matches a
        question in the QuestionService pool is treated as already asked, so
        non-question assistant text (e.g. a stored result id) is ignored.
        """
        pool: set[str] = set()
        for questions in self.question_service.QUESTIONS.values():
            pool.update(questions)
        asked: list[str] = []
        for message in session.messages:
            if message.get("role") != "assistant":
                continue
            content = message.get("content")
            items = content if isinstance(content, list) else str(content).split("\n")
            asked.extend(q for q in items if q in pool)
        return asked

    def _persist_session_and_message(self, session: DiagnosisSession, role: str, content: str) -> None:
        if not self.repository:
            return
        self.repository.update_session(session)
        self.repository.add_message(session.id, role, content)
        self.repository.commit()

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().split())

    def _classify(self, text: str) -> FaultType:
        return self.classification_service._classify_by_keywords(text)

    def _persist_classification_cost(self, session: DiagnosisSession) -> None:
        if not self.repository or not self.classification_service.last_cost_log:
            return
        self.repository.add_cost_log(
            session.id,
            self.classification_service.last_cost_log,
            model_version=self.classification_service.last_model_version,
            tokens=self.classification_service.last_tokens,
            latency_ms=self.classification_service.last_latency_ms,
        )

    def _build_result(
        self,
        session: DiagnosisSession,
        text: str,
        fault_type: FaultType,
        risk,
        city_tier: str | None,
    ) -> DiagnosisResult:
        knowledge = self.rag_service.retrieve(fault_type.secondary, text)
        price: PriceReference = self.price_service.match(fault_type.secondary, city_tier)
        cost_log = self.cost_service.estimate_template_call()

        urgency_level = risk.level if risk.triggered and risk.level else self._default_urgency(fault_type.secondary, text)
        forbidden_actions = list(knowledge["risk_warnings"])
        if risk.action and risk.action not in forbidden_actions:
            forbidden_actions.insert(0, risk.action)

        need_professional = "yes" if urgency_level in ("S", "A") or knowledge["professional_required"] else "conditional"
        uncertainty_note = None if fault_type.confidence >= 0.6 else "当前信息不足，建议补充现场位置、持续时间和异常现象后再判断。"

        llm_sections = self._generate_llm_sections(text, fault_type, urgency_level, knowledge, risk)
        if llm_sections:
            cost_log = llm_sections["cost_log"]
            possible_causes = llm_sections["payload"].get("possible_causes") or knowledge["possible_causes"][:4]
            recommended_actions = llm_sections["payload"].get("recommended_actions") or self._recommended_actions(urgency_level, knowledge)
            forbidden_actions = llm_sections["payload"].get("forbidden_actions") or forbidden_actions
            self_check_steps = llm_sections["payload"].get("self_check_steps")
            need_professional = llm_sections["payload"].get("need_professional") or need_professional
            need_professional_reason = llm_sections["payload"].get("need_professional_reason") or (
                "涉及安全风险或需要现场检测，建议联系专业人员。" if need_professional == "yes" else "可先完成低风险自查，仍异常再联系专业人员。"
            )
            uncertainty_note = llm_sections["payload"].get("uncertainty_note")
            model_provider = llm_sections["provider"]
            model_version = llm_sections["model_version"]
            if urgency_level == "S":
                self_check_steps = []
        else:
            possible_causes = knowledge["possible_causes"][:4]
            recommended_actions = self._recommended_actions(urgency_level, knowledge)
            self_check_steps = [] if urgency_level == "S" else knowledge["safe_self_checks"][:3]
            need_professional_reason = "涉及安全风险或需要现场检测，建议联系专业人员。" if need_professional == "yes" else "可先完成低风险自查，仍异常再联系专业人员。"
            model_provider = "local-template"
            model_version = "rules-template-v1"

        self._last_cost_log = cost_log

        return DiagnosisResult(
            id=str(uuid4()),
            session_id=session.id,
            fault_type=fault_type,
            urgency=Urgency(level=urgency_level, reason=self._urgency_reason(urgency_level, risk.triggered)),
            possible_causes=possible_causes,
            recommended_actions=recommended_actions,
            forbidden_actions=forbidden_actions,
            self_check_steps=self_check_steps,
            need_professional=need_professional,
            need_professional_reason=need_professional_reason,
            price_reference=price,
            uncertainty_note=uncertainty_note,
            model_provider=model_provider,
            model_version=model_version,
            prompt_version="prompt:2026.06:v1",
            knowledge_version=self.rag_service.KNOWLEDGE_VERSION,
            cost_total=cost_log.cost_estimate,
        )

    def _generate_llm_sections(self, text: str, fault_type: FaultType, urgency_level: str, knowledge: dict, risk) -> dict | None:
        if self.llm_adapter is None:
            return None
        messages = [
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "请基于以下结构化信息生成诊断结果 JSON，仅输出 JSON：\n"
                    f"用户描述：{text}\n"
                    f"故障分类：{fault_type.primary}/{fault_type.secondary}\n"
                    f"紧急等级：{urgency_level}\n"
                    f"风险动作：{risk.action or ''}\n"
                    f"知识库：{knowledge}\n"
                    "字段：possible_causes, recommended_actions, forbidden_actions, self_check_steps, "
                    "need_professional, need_professional_reason, uncertainty_note"
                ),
            },
        ]
        try:
            chat_result = self.llm_adapter.chat(messages, schema={"type": "object"}, options={"temperature": 0.2})
            payload = parse_json_object(chat_result.content)
        except (RuntimeError, OSError, OutputParseError, KeyError, ValueError):
            return None
        return {
            "payload": payload,
            "provider": chat_result.provider,
            "model_version": chat_result.model_version,
            "cost_log": self.cost_service.from_chat_result(chat_result),
        }

    def _result_text_for_safety(self, result: DiagnosisResult) -> str:
        parts: list[str] = [
            result.urgency.reason,
            result.need_professional_reason,
            result.uncertainty_note or "",
        ]
        parts.extend(result.possible_causes)
        parts.extend(result.recommended_actions)
        parts.extend(result.forbidden_actions)
        parts.extend(result.self_check_steps)
        return "\n".join(part for part in parts if part)

    def _default_urgency(self, secondary: str, text: str = "") -> str:
        if secondary == "water_leak":
            if self._contains_any(text, ("偶尔", "水珠", "台面边缘", "不确定从哪来")):
                return "C"
            if self._contains_any(text, ("水龙头", "有点潮", "窗边", "没有一直流", "水印", "没滴水")):
                return "B"
            return "A"
        if secondary == "drain_blocked":
            if self._contains_any(text, ("头发", "水下得慢")):
                return "C"
            if self._contains_any(text, ("下水慢", "越来越慢", "偶尔", "还能慢慢", "不是完全", "冒泡", "咕噜", "冲水没劲")):
                return "B"
            return "A"
        if secondary == "ac_not_cooling":
            if self._contains_any(text, ("滤网", "尘满", "很久才凉", "异味", "杂物挡住")):
                return "C"
            return "B"
        if secondary == "circuit_trip":
            if self._contains_any(text, ("跳闸", "漏保")):
                return "A"
            if self._contains_any(text, ("灯不亮", "插座没电", "闪烁", "松了", "没电")):
                return "B"
            return "B"
        if secondary == "lock_failure":
            if self._contains_any(text, ("低电量", "密码能开", "应急供电")):
                return "C"
            if self._contains_any(text, ("人在门外", "钥匙断", "胶水", "进不了屋")):
                return "A"
            return "B"
        if secondary == "wall_mold":
            if self._contains_any(text, ("楼上是卫生间", "吊顶边缘")):
                return "A"
            if self._contains_any(text, ("衣柜后", "没有漏水痕迹", "墙砖", "起皮", "里面是干", "霉味")):
                return "C"
            return "B"
        if secondary == "water_heater_failure":
            if self._contains_any(text, ("太阳能", "遥控器", "刚开有冷水", "保养灯")):
                return "C"
            return "B"
        if secondary == "range_hood_gas_stove":
            if self._contains_any(text, ("排烟管掉",)):
                return "A"
            if self._contains_any(text, ("清洗", "油杯")):
                return "C"
            return "B"
        if secondary == "floor_drain_smell":
            if self._contains_any(text, ("长期不用", "平时很少用", "水封干", "地漏盖")):
                return "C"
            return "B"
        if secondary == "window_hardware":
            if self._contains_any(text, ("小裂纹",)):
                return "A"
            if self._contains_any(text, ("纱窗", "密封条", "合页异响")):
                return "C"
            return "B"
        if secondary in {"water_leak", "drain_blocked", "lock_failure"}:
            return "A"
        if secondary in {"ac_not_cooling", "wall_mold", "floor_drain_smell", "window_hardware", "water_heater_failure", "range_hood_gas_stove"}:
            return "B"
        return "C"

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _urgency_reason(self, level: str, high_risk: bool) -> str:
        if high_risk:
            return "命中高风险规则，按安全优先原则提升紧急等级。"
        return {
            "A": "问题可能持续扩大或影响正常生活，建议尽快处理。",
            "B": "问题不宜长期拖延，建议预约维修或先做低风险排查。",
            "C": "当前看更适合先自行排查或保养。",
        }.get(level, "存在人身或重大财产风险，应立即处理。")

    def _recommended_actions(self, level: str, knowledge: dict) -> list[str]:
        if level == "S":
            return ["先确保人身安全，停止继续使用相关设备。", "联系物业、燃气公司、电工、消防或专业维修人员现场处理。"]
        return knowledge["safe_self_checks"][:2] + ["如问题持续或无法确认原因，联系专业师傅现场检查。"]
