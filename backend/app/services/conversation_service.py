from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from app.ai.llm_adapter import ChatResult, LLMAdapter
from app.ai.output_parser import OutputParseError, parse_json_object
from app.ai.prompt_templates import CONVERSATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class ConversationReply:
    """LLM 对话追问的回复。

    type="chat"     → 继续追问，text 是给用户看的自然语言
    type="complete" → 信息够了，落到 _build_result 出结构化结果
    """

    type: Literal["chat", "complete"]
    text: str
    extracted_fields: dict = field(default_factory=dict)


class ConversationService:
    """阶段 1：用 LLM 主导多轮对话追问，替代硬编码固定问题。

    设计原则：用户看到的永远是 LLM 自然语言，规则只做兜底（不外露）。
    - LLM 返回 JSON（含 reply/complete/fields）→ 按结构化处理
    - LLM 直接返回自然语言（没按 JSON 格式）→ 直接当 chat 追问文字（更自然，接受）
    - LLM 调用失败/空 → 重试 → 仍失败用「自然语言单问」兜底
    """

    def __init__(self, llm_adapter: LLMAdapter, question_service=None):
        self.llm_adapter = llm_adapter
        self.question_service = question_service

    def next_reply(self, session, fault_type, risk, required_fields: list[str]) -> ConversationReply:
        # 高风险：规则直接 complete，不追问（安全优先，PRD §8.4 / §18.6）
        if risk.triggered:
            return ConversationReply(
                type="complete",
                text=risk.action or "检测到安全风险，建议优先确保人身安全并联系专业人员。",
            )

        # 组装 system prompt：注入初步故障分类 + 关键字段清单 + 当前进度
        fields_line = "、".join(required_fields) if required_fields else "（按用户描述判断，无特定字段要求）"
        round_num = session.question_round_count
        system = (
            f"初步故障分类：{fault_type.primary} / {fault_type.secondary}\n"
            f"当前进度：已对话 {round_num} 轮（上限 4 轮）。\n\n"
            + CONVERSATION_SYSTEM_PROMPT.replace("{required_fields}", fields_line)
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        # 只取最近 4 条对话历史（避免 prompt 过长）
        history = [
            m for m in session.messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        for m in history[-4:]:
            role = m["role"]
            content = m["content"]
            text = "\n".join(content) if isinstance(content, list) else str(content)
            if role == "assistant" and text.startswith(("diag_", "QUOTA")):
                continue
            messages.append({"role": role, "content": text})

        # 调 LLM（失败重试一次）。不用 schema=json_object：DeepSeek 在该模式下偶发返回空。
        chat_result = self._call_with_retry(messages)
        if chat_result is None:
            return self._natural_fallback_reply(session, fault_type, required_fields)

        content = (chat_result.content or "").strip()
        if not content:
            logger.warning("conversation LLM returned empty content")
            return self._natural_fallback_reply(session, fault_type, required_fields)

        # 区分三种情况：JSON 有 reply / JSON 无 reply / 非 JSON 自然语言
        try:
            payload = parse_json_object(content)
        except OutputParseError:
            # 非 JSON → LLM 直接返回自然语言，当 chat 追问（最自然的对话形态）
            logger.info("conversation LLM returned natural language (non-JSON), using as-is")
            return ConversationReply(type="chat", text=content, extracted_fields={})

        reply_text = str(payload.get("reply", "")).strip()
        if not reply_text:
            # 是 JSON 但无 reply 字段（如结构化结果 JSON 误入）→ 不当回复，走字段兜底
            return self._natural_fallback_reply(session, fault_type, required_fields)
        complete = bool(payload.get("complete", False))
        raw_fields = payload.get("fields")
        fields = (
            {str(k): str(v) for k, v in raw_fields.items()}
            if isinstance(raw_fields, dict)
            else {}
        )
        return ConversationReply(
            type="complete" if complete else "chat",
            text=reply_text,
            extracted_fields=fields,
        )

    def _call_with_retry(self, messages) -> ChatResult | None:
        for attempt in (1, 2):
            try:
                return self.llm_adapter.chat(
                    messages, schema=None, options={"temperature": 0.6}
                )
            except (RuntimeError, OSError, KeyError, ValueError, TypeError) as exc:
                logger.warning("conversation LLM call failed (attempt %d): %s", attempt, exc)
                if attempt == 2:
                    return None
        return None

    def _natural_fallback_reply(
        self, session, fault_type, required_fields: list[str]
    ) -> ConversationReply:
        """LLM 不可用时，基于未确认字段生成一句自然追问（不暴露规则感）。"""
        history_text = " ".join(
            str(m.get("content", ""))
            for m in session.messages
            if m.get("role") in ("user", "assistant")
        )
        for field_name in required_fields:
            key = field_name.split("(")[0].strip()
            if key and key not in history_text:
                return ConversationReply(
                    type="chat",
                    text=f"对了，方便再跟我说一下「{key}」吗？这样我能判断得更准。",
                )
        return ConversationReply(
            type="complete",
            text="信息差不多了，我整理一下给你。",
        )
