from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.ai.llm_adapter import LLMAdapter
from app.ai.output_parser import OutputParseError, parse_json_object
from app.ai.prompt_templates import CONVERSATION_SYSTEM_PROMPT


@dataclass
class ConversationReply:
    """LLM 对话追问的回复。

    type="chat"     → 继续追问，text 是给用户看的自然语言
    type="complete" → 信息够了，落到 _build_result 出结构化结果
    """

    type: Literal["chat", "complete"]
    text: str
    extracted_fields: dict = field(default_factory=dict)


class ConversationFallback(Exception):
    """LLM 对话追问失败（超时/解析错/空回复），调用方应回退 question_service 兜底。"""


class ConversationService:
    """阶段 1：用 LLM 主导多轮对话追问，替代硬编码固定问题。"""

    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter

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

        # 注入历史对话（session.messages 已含当前用户消息）
        for m in session.messages:
            role = m.get("role")
            content = m.get("content")
            if role not in ("user", "assistant") or not content:
                continue
            text = "\n".join(content) if isinstance(content, list) else str(content)
            # 跳过结果 id 等非对话内容
            if role == "assistant" and text.startswith(("diag_", "QUOTA")):
                continue
            messages.append({"role": role, "content": text})

        try:
            chat_result = self.llm_adapter.chat(
                messages, schema={"type": "object"}, options={"temperature": 0.4}
            )
            payload = parse_json_object(chat_result.content)
        except (RuntimeError, OSError, OutputParseError, KeyError, ValueError, TypeError) as exc:
            raise ConversationFallback(str(exc)) from exc

        reply_text = str(payload.get("reply", "")).strip()
        if not reply_text:
            raise ConversationFallback("LLM 返回空回复")

        complete = bool(payload.get("complete", False))
        raw_fields = payload.get("fields")
        fields = {str(k): str(v) for k, v in raw_fields.items()} if isinstance(raw_fields, dict) else {}

        return ConversationReply(
            type="complete" if complete else "chat",
            text=reply_text,
            extracted_fields=fields,
        )
