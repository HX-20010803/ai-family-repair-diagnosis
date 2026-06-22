from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4


UrgencyLevel = Literal["S", "A", "B", "C"]
ResponseType = Literal["questions", "result", "blocked"]


@dataclass(slots=True)
class FaultType:
    primary: str
    secondary: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RiskAssessment:
    triggered: bool
    risk_type: str | None = None
    level: UrgencyLevel | None = None
    action: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    explicitly_negated: bool = False


@dataclass(slots=True)
class Urgency:
    level: UrgencyLevel
    reason: str


@dataclass(slots=True)
class PriceReference:
    range: str
    disclaimer: str
    has_reliable_price: bool
    city_tier: str
    version: str


@dataclass(slots=True)
class DiagnosisResult:
    id: str
    session_id: str
    fault_type: FaultType
    urgency: Urgency
    possible_causes: list[str]
    recommended_actions: list[str]
    forbidden_actions: list[str]
    self_check_steps: list[str]
    need_professional: Literal["yes", "no", "conditional"]
    need_professional_reason: str
    price_reference: PriceReference | None
    uncertainty_note: str | None
    model_provider: str
    model_version: str
    prompt_version: str
    knowledge_version: str
    cost_total: float


@dataclass(slots=True)
class DiagnosisSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    anonymous_token: str = ""
    original_input_json: dict = field(default_factory=dict)
    question_round_count: int = 0
    status: Literal["diagnosing", "completed", "cancelled"] = "diagnosing"
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class DiagnosisResponse:
    type: ResponseType
    session: DiagnosisSession
    questions: list[str] = field(default_factory=list)
    result: DiagnosisResult | None = None
    safety_notice: str | None = None
    error_code: str | None = None

