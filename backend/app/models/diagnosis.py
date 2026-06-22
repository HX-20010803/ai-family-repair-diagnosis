from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class DiagnosisSession(Base):
    __tablename__ = "diagnosis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anonymous_token: Mapped[str] = mapped_column(String(128), index=True)
    original_input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    input_type: Mapped[str] = mapped_column(String(32), default="text")
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_round_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="diagnosing")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DiagnosisMessage(Base):
    __tablename__ = "diagnosis_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnosis_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiagnosisResult(Base):
    __tablename__ = "diagnosis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnosis_sessions.id"), index=True)
    primary_category: Mapped[str] = mapped_column(String(64))
    secondary_category: Mapped[str] = mapped_column(String(64))
    urgency_level: Mapped[str] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))
    result_json: Mapped[dict] = mapped_column(JSON)
    model_provider: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    knowledge_version: Mapped[str] = mapped_column(String(128))
    cost_total: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
