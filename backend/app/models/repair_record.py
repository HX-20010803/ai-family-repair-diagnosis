from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class RepairRecord(Base):
    __tablename__ = "repair_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anonymous_token: Mapped[str | None] = mapped_column(String(128), index=True)
    diagnosis_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnosis_results.id"))
    house_area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actual_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reminder_status: Mapped[str] = mapped_column(String(32), default="none")
    is_resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_recurred: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
