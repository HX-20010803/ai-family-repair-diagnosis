from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    openid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    unionid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_realname_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

