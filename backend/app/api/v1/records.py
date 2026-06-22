from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.repair_record import RepairRecord
from app.services.record_service import RecordService


router = APIRouter()


class RepairRecordCreate(BaseModel):
    diagnosis_result_id: str
    house_area: str | None = None
    actual_solution: str | None = None
    actual_cost: float | None = Field(default=None, ge=0)
    provider_name: str | None = None


class RepairRecordPatch(BaseModel):
    actual_solution: str | None = None
    actual_cost: float | None = Field(default=None, ge=0)
    provider_name: str | None = None
    is_resolved: bool | None = None
    is_recurred: bool | None = None


@router.post("")
def create_record(
    payload: RepairRecordCreate,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db: Session = Depends(get_db),
) -> dict:
    service = RecordService(db)
    record = service.create_record(
        anonymous_token=x_anonymous_token,
        diagnosis_result_id=payload.diagnosis_result_id,
        house_area=payload.house_area,
        actual_solution=payload.actual_solution,
        actual_cost=payload.actual_cost,
        provider_name=payload.provider_name,
    )
    return _record_to_dict(record)


@router.get("")
def list_records(x_anonymous_token: str = Header(default="anonymous-demo"), db: Session = Depends(get_db)) -> dict:
    service = RecordService(db)
    records = service.list_records(anonymous_token=x_anonymous_token)
    return {"items": [_record_to_dict(record) for record in records], "total": len(records)}


@router.get("/{record_id}")
def get_record(record_id: str, db: Session = Depends(get_db)) -> dict:
    service = RecordService(db)
    record = service.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "RECORD_NOT_FOUND"})
    return _record_to_dict(record)


@router.patch("/{record_id}")
def patch_record(record_id: str, payload: RepairRecordPatch, db: Session = Depends(get_db)) -> dict:
    service = RecordService(db)
    record = service.patch_record(record_id, **payload.model_dump(exclude_unset=True))
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "RECORD_NOT_FOUND"})
    return _record_to_dict(record)


def _record_to_dict(record: RepairRecord) -> dict:
    return {
        "id": record.id,
        "anonymous_token": record.anonymous_token,
        "diagnosis_result_id": record.diagnosis_result_id,
        "house_area": record.house_area,
        "actual_solution": record.actual_solution,
        "actual_cost": float(record.actual_cost) if record.actual_cost is not None else None,
        "provider_name": record.provider_name,
        "reminder_status": record.reminder_status,
        "is_resolved": record.is_resolved,
        "is_recurred": record.is_recurred,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
