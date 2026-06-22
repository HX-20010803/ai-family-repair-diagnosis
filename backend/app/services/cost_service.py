from __future__ import annotations

from dataclasses import dataclass

from app.ai.llm_adapter import ChatResult


@dataclass(slots=True)
class CostLog:
    capability: str
    provider: str
    cost_estimate: float
    estimated: bool
    status: str


class CostService:
    TEXT_DIAGNOSIS_ESTIMATE = 0.03

    def estimate_template_call(self, capability: str = "rules_template") -> CostLog:
        return CostLog(
            capability=capability,
            provider="local",
            cost_estimate=self.TEXT_DIAGNOSIS_ESTIMATE,
            estimated=True,
            status="degraded",
        )

    def from_chat_result(self, result: ChatResult) -> CostLog:
        return CostLog(
            capability="llm_chat",
            provider=result.provider,
            cost_estimate=result.cost_estimate,
            estimated=True,
            status="success",
        )
