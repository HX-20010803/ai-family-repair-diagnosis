from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Device(Base):
    """家庭设备档案（PRD §17.7）：空调/热水器/门锁等的品牌、年限、保修。

    用于诊断时注入用户画像（「这台热水器用了 8 年」），让 AI 更了解用户。
    """

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    anonymous_token: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    house_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("houses.id"), nullable=True)
    room_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("rooms.id"), nullable=True)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 空调/热水器/门锁/油烟机...
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purchase_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 购买日期/年限文本
    warranty_until: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 保修到期
    note: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
