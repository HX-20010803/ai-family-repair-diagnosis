from __future__ import annotations

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class ContentSafetyLog(Base):
    __tablename__ = "content_safety_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    content_source: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(32))
    hit_categories: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="local")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

