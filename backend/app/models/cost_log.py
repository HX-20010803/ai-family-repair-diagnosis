from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class CostLog(Base):
    __tablename__ = "cost_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64))
    capability: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_count: Mapped[int] = mapped_column(Integer, default=1)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="success")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
