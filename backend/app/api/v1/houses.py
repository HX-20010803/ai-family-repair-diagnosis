from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app.api.deps import get_db
from app.models.house import House, Room
from app.services.house_service import HouseService


router = APIRouter()


class HouseCreate(BaseModel):
    city: str = Field(min_length=1, max_length=64)
    city_tier: Literal["tier1", "other"] = "other"
    community_name: str | None = Field(default=None, max_length=128)


class RoomCreate(BaseModel):
    room_name: str = Field(min_length=1, max_length=64)


class HouseUpdate(BaseModel):
    city: str | None = Field(default=None, min_length=1, max_length=64)
    city_tier: Literal["tier1", "other"] | None = None
    community_name: str | None = Field(default=None, max_length=128)


class RoomUpdate(BaseModel):
    room_name: str | None = Field(default=None, min_length=1, max_length=64)


@router.get("")
def list_houses(x_anonymous_token: str = Header(default="anonymous-demo"), db=Depends(get_db)) -> dict:
    service = HouseService(db)
    houses = service.list_houses(anonymous_token=x_anonymous_token)
    return {"items": [_house_with_rooms(service, house) for house in houses], "total": len(houses)}


@router.post("")
def create_house(
    payload: HouseCreate,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    house = service.create_house(
        anonymous_token=x_anonymous_token,
        city=payload.city,
        city_tier=payload.city_tier,
        community_name=payload.community_name,
    )
    return _house_to_dict(house, rooms=[])


@router.delete("/{house_id}")
def delete_house(
    house_id: str,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    deleted = service.delete_house(house_id=house_id, anonymous_token=x_anonymous_token)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "HOUSE_NOT_FOUND"})
    return {"deleted": True}


@router.patch("/{house_id}")
def update_house(
    house_id: str,
    payload: HouseUpdate,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    house = service.update_house(
        house_id=house_id,
        anonymous_token=x_anonymous_token,
        city=payload.city,
        city_tier=payload.city_tier,
        community_name=payload.community_name,
    )
    if house is None:
        raise HTTPException(status_code=404, detail={"code": "HOUSE_NOT_FOUND"})
    return _house_with_rooms(service, house)


@router.post("/{house_id}/rooms")
def create_room(
    house_id: str,
    payload: RoomCreate,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    room = service.create_room(house_id=house_id, room_name=payload.room_name)
    if room is None:
        raise HTTPException(status_code=404, detail={"code": "HOUSE_NOT_FOUND"})
    return _room_to_dict(room)


@router.delete("/{house_id}/rooms/{room_id}")
def delete_room(
    house_id: str,
    room_id: str,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    deleted = service.delete_room(room_id=room_id, anonymous_token=x_anonymous_token)
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})
    return {"deleted": True}


@router.patch("/{house_id}/rooms/{room_id}")
def update_room(
    house_id: str,
    room_id: str,
    payload: RoomUpdate,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db=Depends(get_db),
) -> dict:
    service = HouseService(db)
    room = service.update_room(room_id=room_id, anonymous_token=x_anonymous_token, room_name=payload.room_name)
    if room is None:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})
    return _room_to_dict(room)


def _room_to_dict(room: Room) -> dict:
    return {
        "id": room.id,
        "house_id": room.house_id,
        "room_name": room.room_name,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


def _house_to_dict(house: House, rooms: list[Room]) -> dict:
    return {
        "id": house.id,
        "city": house.city,
        "city_tier": house.city_tier,
        "community_name": house.community_name,
        "created_at": house.created_at.isoformat() if house.created_at else None,
        "rooms": [_room_to_dict(room) for room in rooms],
    }


def _house_with_rooms(service: HouseService, house: House) -> dict:
    rooms = service.list_rooms(house.id)
    return _house_to_dict(house, rooms)
