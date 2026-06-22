from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import DiagnosisResult as DomainDiagnosisResult
from app.domain import DiagnosisSession as DomainDiagnosisSession
from app.services.cost_service import CostLog as DomainCostLog
from app.models.content_safety import ContentSafetyLog
from app.models.cost_log import CostLog
from app.models.diagnosis import DiagnosisMessage, DiagnosisResult, DiagnosisSession
from app.models.feedback import DiagnosisFeedback
from app.models.quota import QuotaUsage


class DiagnosisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_session(self, session_id: str) -> DiagnosisSession | None:
        return self.db.get(DiagnosisSession, session_id)

    def create_session(self, session: DomainDiagnosisSession) -> DiagnosisSession:
        row = DiagnosisSession(
            id=session.id,
            anonymous_token=session.anonymous_token,
            original_input_json=session.original_input_json,
            input_type=session.original_input_json.get("type", "text"),
            question_round_count=session.question_round_count,
            status=session.status,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def update_session(self, session: DomainDiagnosisSession) -> DiagnosisSession:
        row = self.get_session(session.id)
        if row is None:
            row = self.create_session(session)
        row.question_round_count = session.question_round_count
        row.status = session.status
        self.db.flush()
        return row

    def add_message(self, session_id: str, role: str, content: str) -> DiagnosisMessage:
        row = DiagnosisMessage(session_id=session_id, role=role, content=content)
        self.db.add(row)
        self.db.flush()
        return row

    def list_messages(self, session_id: str) -> list[DiagnosisMessage]:
        stmt = select(DiagnosisMessage).where(DiagnosisMessage.session_id == session_id).order_by(DiagnosisMessage.created_at.asc())
        return list(self.db.scalars(stmt))

    def save_result(self, result: DomainDiagnosisResult) -> DiagnosisResult:
        payload = asdict(result)
        row = DiagnosisResult(
            id=result.id,
            session_id=result.session_id,
            primary_category=result.fault_type.primary,
            secondary_category=result.fault_type.secondary,
            urgency_level=result.urgency.level,
            confidence=result.fault_type.confidence,
            result_json=payload,
            model_provider=result.model_provider,
            model_version=result.model_version,
            prompt_version=result.prompt_version,
            knowledge_version=result.knowledge_version,
            cost_total=result.cost_total,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_result(self, result_id: str) -> DiagnosisResult | None:
        return self.db.get(DiagnosisResult, result_id)

    def upsert_feedback(
        self,
        result_id: str,
        session_id: str,
        anonymous_token: str,
        rating: str,
        reason_tags: list[str] | None = None,
        comment: str | None = None,
    ) -> DiagnosisFeedback:
        stmt = select(DiagnosisFeedback).where(
            DiagnosisFeedback.result_id == result_id,
            DiagnosisFeedback.anonymous_token == anonymous_token,
        )
        row = self.db.scalar(stmt)
        if row is None:
            row = DiagnosisFeedback(
                result_id=result_id,
                session_id=session_id,
                anonymous_token=anonymous_token,
                rating=rating,
                reason_tags=reason_tags or [],
                comment=comment,
            )
            self.db.add(row)
        else:
            row.rating = rating
            row.reason_tags = reason_tags or []
            row.comment = comment
        self.db.flush()
        return row

    def list_feedback(self, result_id: str) -> list[DiagnosisFeedback]:
        stmt = select(DiagnosisFeedback).where(DiagnosisFeedback.result_id == result_id).order_by(DiagnosisFeedback.created_at.asc())
        return list(self.db.scalars(stmt))

    def add_cost_log(
        self,
        session_id: str,
        cost_log: DomainCostLog,
        model_version: str | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> CostLog:
        row = CostLog(
            session_id=session_id,
            provider=cost_log.provider,
            capability=cost_log.capability,
            model_version=model_version,
            tokens=tokens,
            call_count=1,
            latency_ms=latency_ms,
            cost_estimate=cost_log.cost_estimate,
            estimated=cost_log.estimated,
            status=cost_log.status,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_cost_logs(self, session_id: str) -> list[CostLog]:
        return list(self.db.scalars(select(CostLog).where(CostLog.session_id == session_id)))

    def add_content_safety_log(
        self,
        session_id: str | None,
        content_source: str,
        result: str,
        hit_categories: list[str] | None = None,
        provider: str = "local",
    ) -> ContentSafetyLog:
        row = ContentSafetyLog(
            session_id=session_id,
            content_source=content_source,
            result=result,
            hit_categories=",".join(hit_categories or []) or None,
            provider=provider,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_content_safety_logs(self, session_id: str) -> list[ContentSafetyLog]:
        stmt = select(ContentSafetyLog).where(ContentSafetyLog.session_id == session_id).order_by(ContentSafetyLog.created_at.asc())
        return list(self.db.scalars(stmt))

    def get_today_full_diagnosis_count(self, anonymous_token: str) -> int:
        row = self._get_or_create_quota_usage(anonymous_token)
        return row.full_diagnosis_count

    def increment_today_full_diagnosis_count(self, anonymous_token: str) -> QuotaUsage:
        row = self._get_or_create_quota_usage(anonymous_token)
        row.full_diagnosis_count += 1
        self.db.flush()
        return row

    def _get_or_create_quota_usage(self, anonymous_token: str) -> QuotaUsage:
        today = date.today()
        stmt = select(QuotaUsage).where(
            QuotaUsage.subject_type == "anonymous_token",
            QuotaUsage.subject_id == anonymous_token,
            QuotaUsage.quota_date == today,
        )
        row = self.db.scalar(stmt)
        if row is None:
            row = QuotaUsage(
                subject_type="anonymous_token",
                subject_id=anonymous_token,
                quota_date=today,
                full_diagnosis_count=0,
            )
            self.db.add(row)
            self.db.flush()
        return row

    def commit(self) -> None:
        self.db.commit()


def numeric_to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return value
