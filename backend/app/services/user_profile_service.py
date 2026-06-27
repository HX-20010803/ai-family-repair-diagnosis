from __future__ import annotations

from sqlalchemy import select

from app.repositories.diagnosis_repository import DiagnosisRepository


class UserProfileService:
    """阶段 2：聚合用户的房屋/房间/城市能级 + 历史诊断，生成画像摘要注入 LLM，
    让 AI 能"记住"用户（「这位用户住深圳一线，上次修过热水器」）。"""

    def __init__(self, repository: DiagnosisRepository | None = None):
        self.repository = repository

    def build_profile(self, anonymous_token: str) -> str:
        """返回一段用户画像文本（无数据返回空串）。"""
        if not self.repository or not anonymous_token:
            return ""
        from app.models.house import House, Room
        from app.models.diagnosis import DiagnosisResult, DiagnosisSession

        parts: list[str] = []

        # 房屋 + 房间 + 城市能级
        houses = list(self.repository.db.execute(
            select(House).where(House.anonymous_token == anonymous_token)
        ).scalars().all())
        for h in houses[:2]:
            tier = "一线城市" if h.city_tier == "tier1" else "其他城市"
            rooms = list(self.repository.db.execute(
                select(Room.room_name).where(Room.house_id == h.id)
            ).scalars().all())
            room_text = "、".join(rooms[:5]) if rooms else ""
            line = f"住在{h.city}（{tier}）"
            if h.community_name:
                line += f"·{h.community_name}"
            if room_text:
                line += f"，房间有{room_text}"
            parts.append(line)

        # 历史诊断（最近 3 条，按时间倒序）
        rows = list(self.repository.db.execute(
            select(DiagnosisResult.secondary_category, DiagnosisResult.urgency_level)
            .join(DiagnosisSession, DiagnosisResult.session_id == DiagnosisSession.id)
            .where(DiagnosisSession.anonymous_token == anonymous_token)
            .order_by(DiagnosisResult.created_at.desc())
            .limit(3)
        ))
        for r in rows:
            parts.append(f"曾诊断过{r.secondary_category}（{r.urgency_level}级）")

        if not parts:
            return ""
        return "【用户画像】这位用户" + "；".join(parts) + "。可据此个性化沟通和给针对性建议。"
