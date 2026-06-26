from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisResult
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
        # 同一个诊断结果只建一条记录：complete 时已自动建过，前端再点"保存"或补充信息时 update
        existing = self.db.execute(
            select(RepairRecord).where(RepairRecord.diagnosis_result_id == diagnosis_result_id)
        ).scalars().first()
        if existing:
            changed = False
            if house_area is not None and existing.house_area is None:
                existing.house_area = house_area
                changed = True
            if actual_solution is not None and existing.actual_solution is None:
                existing.actual_solution = actual_solution
                changed = True
            if actual_cost is not None and existing.actual_cost is None:
                existing.actual_cost = actual_cost
                changed = True
            if provider_name is not None and existing.provider_name is None:
                existing.provider_name = provider_name
                changed = True
            if changed:
                self.db.commit()
                self.db.refresh(existing)
            return existing
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

    def list_records(self, anonymous_token: str) -> list[tuple[RepairRecord, DiagnosisResult | None]]:
        stmt = (
            select(RepairRecord, DiagnosisResult)
            .join(DiagnosisResult, RepairRecord.diagnosis_result_id == DiagnosisResult.id, isouter=True)
            .where(RepairRecord.anonymous_token == anonymous_token)
            .order_by(RepairRecord.created_at.desc())
        )
        return [(record, result) for record, result in self.db.execute(stmt).all()]

    def get_record(self, record_id: str) -> RepairRecord | None:
        return self.db.get(RepairRecord, record_id)

    def get_record_with_result(self, record_id: str) -> tuple[RepairRecord | None, DiagnosisResult | None]:
        stmt = (
            select(RepairRecord, DiagnosisResult)
            .join(DiagnosisResult, RepairRecord.diagnosis_result_id == DiagnosisResult.id, isouter=True)
            .where(RepairRecord.id == record_id)
        )
        row = self.db.execute(stmt).first()
        if row is None:
            return None, None
        return row[0], row[1]

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

