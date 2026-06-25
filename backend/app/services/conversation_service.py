from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from app.ai.llm_adapter import LLMAdapter
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
    - LLM 成功 → 自然追问/complete
    - LLM 偶发失败 → 重试一次
    - 仍失败 → 基于未确认字段生成「自然语言单问」（绝不再返回固定 3 问）
    """

    def __init__(self, llm_adapter: LLMAdapter, question_service=None):
        self.llm_adapter = llm_adapter
        # 用于「自然语言单问」兜底时挑字段；可选
        self.question_service = question_service

    def next_reply(self, session, fault_type, risk, required_fields: list[str]) -> ConversationReply:
        # 高风险：规则直接 complete，不追问（安全优先，PRD §8.4 / §18.6）
        if risk.triggered:
            return ConversationReply(
                type="complete",
                text=risk.action or "检测到安全风险，建议优先确保人身安全并联系专业人员。",
            )

        # 组装 system prompt：注入初步故障分类 + 关键字段清单
        fields_line = "、".join(required_fields) if required_fields else "（按用户描述判断，无特定字段要求）"
        system = (
            f"初步故障分类：{fault_type.primary} / {fault_type.secondary}\n\n"
            + CONVERSATION_SYSTEM_PROMPT.replace("{required_fields}", fields_line)
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for m in session.messages:
            role = m.get("role")
            content = m.get("content")
            if role not in ("user", "assistant") or not content:
                continue
            text = "\n".join(content) if isinstance(content, list) else str(content)
            if role == "assistant" and text.startswith(("diag_", "QUOTA")):
                continue
            messages.append({"role": role, "content": text})

        # 调 LLM（失败重试一次）
        payload = self._call_llm_with_retry(messages)
        if payload is not None:
            reply_text = str(payload.get("reply", "")).strip()
            if reply_text:
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

        # LLM 彻底失败 → 自然语言单问兜底（基于未确认字段，绝不返回固定 3 问）
        return self._natural_fallback_reply(session, fault_type, required_fields)

    def _call_llm_with_retry(self, messages) -> dict | None:
        for attempt in (1, 2):
            try:
                chat_result = self.llm_adapter.chat(
                    messages, schema={"type": "object"}, options={"temperature": 0.5}
                )
                return parse_json_object(chat_result.content)
            except (RuntimeError, OSError, OutputParseError, KeyError, ValueError, TypeError) as exc:
                logger.warning("conversation LLM call failed (attempt %d): %s", attempt, exc)
                if attempt == 2:
                    return None
        return None

    def _natural_fallback_reply(
        self, session, fault_type, required_fields: list[str]
    ) -> ConversationReply:
        """LLM 不可用时，基于未确认字段生成一句自然追问（不暴露规则感）。"""
        # 从历史里粗略判断哪些字段已被提到
        history_text = " ".join(
            str(m.get("content", ""))
            for m in session.messages
            if m.get("role") in ("user", "assistant")
        )
        # 挑一个字段名里历史没出现的关键字，组成一句温和的追问
        for field_name in required_fields:
            # 取字段名里的核心词（如"热水器类型(燃气/电/太阳能)"→"热水器类型"）
            key = field_name.split("(")[0].strip()
            if key and key not in history_text:
                return ConversationReply(
                    type="chat",
                    text=f"对了，方便再跟我说一下「{key}」吗？这样我能判断得更准。",
                )
        # 字段都聊过了 → 出结果
        return ConversationReply(
            type="complete",
            text="信息差不多了，我整理一下给你。",
        )
