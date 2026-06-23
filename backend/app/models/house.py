from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.db.base import Base


class House(Base):
    __tablename__ = "houses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    anonymous_token: Mapped[str] = mapped_column(String(128), index=True)
    city: Mapped[str] = mapped_column(String(64))
    city_tier: Mapped[str] = mapped_column(String(8), default="other")
    community_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    house_id: Mapped[str] = mapped_column(String(36), ForeignKey("houses.id"), index=True)
    room_name: Mapped[str] = mapped_column(String(64))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
