from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiagnosisFeedback(Base):
    __tablename__ = "diagnosis_feedback"
    __table_args__ = (
        UniqueConstraint("result_id", "anonymous_token", name="uq_feedback_result_anonymous"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    result_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnosis_results.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnosis_sessions.id"), index=True)
    anonymous_token: Mapped[str] = mapped_column(String(128), index=True)
    rating: Mapped[str] = mapped_column(String(32))
    reason_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
