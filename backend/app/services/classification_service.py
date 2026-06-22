from __future__ import annotations

from app.ai.llm_adapter import LLMAdapter
from app.ai.output_parser import OutputParseError, parse_json_object
from app.domain import FaultType
from app.services.cost_service import CostLog, CostService
from app.services.taxonomy import CLASSIFICATION_KEYWORDS, SECONDARY_NAMES, SECONDARY_TO_PRIMARY, primary_for_secondary


class ClassificationService:
    HIGH_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, llm_adapter: LLMAdapter | None = None):
        self.llm_adapter = llm_adapter
        self.cost_service = CostService()
        self.last_cost_log: CostLog | None = None
        self.last_model_version: str | None = None
        self.last_tokens: int | None = None
        self.last_latency_ms: int | None = None
        self.llm_call_count = 0

    def classify(self, text: str) -> FaultType:
        self._reset_trace()
        rule_result = self._classify_by_keywords(text)
        if rule_result.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return rule_result

        if self.llm_adapter is None:
            return rule_result

        try:
            return self._confirm_with_llm(text, rule_result)
        except (RuntimeError, OSError, OutputParseError, KeyError, ValueError, TypeError):
            self._reset_trace()
            return rule_result

    def _classify_by_keywords(self, text: str) -> FaultType:
        best_secondary = "water_leak"
        best_hits: list[str] = []
        best_score = 0
        for secondary, keywords in CLASSIFICATION_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in text]
            score = sum(max(1, len(keyword) // 2) for keyword in hits)
            if score > best_score:
                best_secondary = secondary
                best_hits = hits
                best_score = score

        confidence = min(0.95, 0.55 + best_score * 0.07)
        primary = primary_for_secondary(best_secondary)
        if SECONDARY_TO_PRIMARY.get(best_secondary) != primary:
            confidence = min(confidence, 0.5)

        return FaultType(
            primary=primary,
            secondary=best_secondary,
            confidence=confidence,
            evidence=best_hits or ["根据用户描述做初步分类"],
        )

    def _confirm_with_llm(self, text: str, rule_result: FaultType) -> FaultType:
        if self.llm_adapter is None:
            return rule_result

        messages = [
            {
                "role": "system",
                "content": (
                    "你是家庭维修分类器。只能从给定二级分类 code 中选择一个。\n"
                    f"合法二级分类：{SECONDARY_NAMES}\n"
                    "仅输出 JSON："
                    '{"secondary_category":"...","confidence":0.0,"evidence":["..."],"reason":"..."}'
                ),
            },
            {
                "role": "user",
                "content": f"用户描述：{text}\n关键词初判：{rule_result.secondary}，置信度：{rule_result.confidence}",
            },
        ]
        chat_result = self.llm_adapter.chat(messages, schema={"type": "object"}, options={"temperature": 0.1})
        payload = parse_json_object(chat_result.content)
        secondary = payload["secondary_category"]
        if secondary not in SECONDARY_TO_PRIMARY:
            raise OutputParseError(f"Unknown secondary category: {secondary}")

        confidence = float(payload.get("confidence") or rule_result.confidence)
        evidence = payload.get("evidence") or rule_result.evidence
        if not isinstance(evidence, list):
            evidence = [str(evidence)]

        cost_log = self.cost_service.from_chat_result(chat_result)
        cost_log.capability = "classification"
        self.last_cost_log = cost_log
        self.last_model_version = chat_result.model_version
        self.last_tokens = int(chat_result.usage.get("total_tokens") or 0)
        self.last_latency_ms = chat_result.latency_ms
        self.llm_call_count += 1

        return FaultType(
            primary=primary_for_secondary(secondary),
            secondary=secondary,
            confidence=max(0.0, min(0.99, confidence)),
            evidence=[str(item) for item in evidence],
        )

    def _reset_trace(self) -> None:
        self.last_cost_log = None
        self.last_model_version = None
        self.last_tokens = None
        self.last_latency_ms = None
