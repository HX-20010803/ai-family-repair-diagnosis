from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repair_record import RepairRecord


class RecordService:
    def __init__(self, db: Session):
        self.db = db

    def create_record(
        self,
        anonymous_token: str,
        diagnosis_result_id: str,
        house_area: str | None = None,
        actual_solution: str | None = None,
        actual_cost: float | None = None,
        provider_name: str | None = None,
    ) -> RepairRecord:
        row = RepairRecord(
            anonymous_token=anonymous_token,
            diagnosis_result_id=diagnosis_result_id,
            house_area=house_area,
            actual_solution=actual_solution,
            actual_cost=actual_cost,
            provider_name=provider_name,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_records(self, anonymous_token: str) -> list[RepairRecord]:
        stmt = (
            select(RepairRecord)
            .where(RepairRecord.anonymous_token == anonymous_token)
            .order_by(RepairRecord.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_record(self, record_id: str) -> RepairRecord | None:
        return self.db.get(RepairRecord, record_id)

    def patch_record(self, record_id: str, **updates) -> RepairRecord | None:
        row = self.get_record(record_id)
        if row is None:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

