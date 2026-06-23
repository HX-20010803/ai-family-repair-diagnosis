import unittest
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models import content_safety, cost_log, diagnosis, feedback, house, quota, repair_record  # noqa: F401
from app.services.house_service import HouseService
from app.api.v1.houses import HouseCreate, RoomCreate, create_house, create_room, delete_house, delete_room, list_houses
from fastapi import HTTPException


class HousesApiTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_create_house_and_list_with_rooms(self):
        with self.Session() as db:
            house = create_house(
                payload=HouseCreate(city="深圳", city_tier="tier1", community_name="科技园"),
                x_anonymous_token="token-a",
                db=db,
            )
            self.assertEqual(house["city"], "深圳")
            self.assertEqual(house["city_tier"], "tier1")

            create_room(payload=RoomCreate(room_name="厨房"), house_id=house["id"], x_anonymous_token="token-a", db=db)
            create_room(payload=RoomCreate(room_name="卫生间"), house_id=house["id"], x_anonymous_token="token-a", db=db)

            listing = list_houses(x_anonymous_token="token-a", db=db)
            self.assertEqual(listing["total"], 1)
            self.assertEqual(len(listing["items"][0]["rooms"]), 2)
            self.assertEqual({r["room_name"] for r in listing["items"][0]["rooms"]}, {"厨房", "卫生间"})

    def test_invalid_city_tier_falls_back_to_other(self):
        # Pydantic Literal rejects unknown tiers at the schema layer; the service
        # also defends against any non-literal path by coercing to "other".
        with self.Session() as db:
            house = HouseService(db).create_house(
                anonymous_token="token-a", city="某城", city_tier="bogus-tier"
            )
            self.assertEqual(house.city_tier, "other")

    def test_house_isolation_by_anonymous_token(self):
        with self.Session() as db:
            create_house(payload=HouseCreate(city="深圳", city_tier="tier1"), x_anonymous_token="token-a", db=db)
            create_house(payload=HouseCreate(city="老家", city_tier="other"), x_anonymous_token="token-b", db=db)

            a = list_houses(x_anonymous_token="token-a", db=db)
            b = list_houses(x_anonymous_token="token-b", db=db)
            self.assertEqual(a["total"], 1)
            self.assertEqual(a["items"][0]["city"], "深圳")
            self.assertEqual(b["total"], 1)
            self.assertEqual(b["items"][0]["city"], "老家")

    def test_delete_house_removes_owned_rooms_and_blocks_cross_token(self):
        with self.Session() as db:
            house = create_house(payload=HouseCreate(city="深圳", city_tier="tier1"), x_anonymous_token="token-a", db=db)
            create_room(payload=RoomCreate(room_name="厨房"), house_id=house["id"], x_anonymous_token="token-a", db=db)

            with self.assertRaises(HTTPException):
                delete_house(house_id=house["id"], x_anonymous_token="token-b", db=db)

            delete_house(house_id=house["id"], x_anonymous_token="token-a", db=db)
            self.assertEqual(list_houses(x_anonymous_token="token-a", db=db)["total"], 0)
            self.assertEqual(HouseService(db).list_rooms(house["id"]), [])

    def test_delete_room_blocks_cross_token(self):
        with self.Session() as db:
            house = create_house(payload=HouseCreate(city="深圳", city_tier="tier1"), x_anonymous_token="token-a", db=db)
            room = create_room(payload=RoomCreate(room_name="厨房"), house_id=house["id"], x_anonymous_token="token-a", db=db)

            with self.assertRaises(HTTPException):
                delete_room(house_id=house["id"], room_id=room["id"], x_anonymous_token="token-b", db=db)

            delete_room(house_id=house["id"], room_id=room["id"], x_anonymous_token="token-a", db=db)
            self.assertEqual(len(list_houses(x_anonymous_token="token-a", db=db)["items"][0]["rooms"]), 0)


if __name__ == "__main__":
    unittest.main()
