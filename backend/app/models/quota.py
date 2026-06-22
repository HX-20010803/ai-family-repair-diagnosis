from __future__ import annotations

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class QuotaUsage(Base):
    __tablename__ = "quota_usage"
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "quota_date", name="uq_quota_subject_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[str] = mapped_column(String(128))
    quota_date = mapped_column(Date)
    full_diagnosis_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
