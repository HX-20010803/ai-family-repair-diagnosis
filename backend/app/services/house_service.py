from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.house import House, Room

VALID_CITY_TIERS = {"tier1", "other"}


class HouseService:
    def __init__(self, db: Session):
        self.db = db

    def list_houses(self, anonymous_token: str) -> list[House]:
        stmt = (
            select(House)
            .where(House.anonymous_token == anonymous_token)
            .order_by(House.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def create_house(
        self,
        anonymous_token: str,
        city: str,
        city_tier: str,
        community_name: str | None = None,
    ) -> House:
        row = House(
            anonymous_token=anonymous_token,
            city=city,
            city_tier=city_tier if city_tier in VALID_CITY_TIERS else "other",
            community_name=community_name,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_house(self, house_id: str, anonymous_token: str) -> bool:
        row = self.db.get(House, house_id)
        if row is None or row.anonymous_token != anonymous_token:
            return False
        # Delete owned rooms first to avoid orphaned rows.
        rooms = self.db.scalars(select(Room).where(Room.house_id == house_id)).all()
        for room in rooms:
            self.db.delete(room)
        self.db.delete(row)
        self.db.commit()
        return True

    def list_rooms(self, house_id: str) -> list[Room]:
        stmt = select(Room).where(Room.house_id == house_id).order_by(Room.created_at.asc())
        return list(self.db.scalars(stmt))

    def create_room(self, house_id: str, room_name: str) -> Room | None:
        if self.db.get(House, house_id) is None:
            return None
        row = Room(house_id=house_id, room_name=room_name)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_room(self, room_id: str, anonymous_token: str) -> bool:
        row = self.db.get(Room, room_id)
        if row is None:
            return False
        house = self.db.get(House, row.house_id)
        if house is None or house.anonymous_token != anonymous_token:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
