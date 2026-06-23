from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import diagnosis, health, houses, records


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(records.router, prefix="/repair-records", tags=["repair-records"])
api_router.include_router(houses.router, prefix="/houses", tags=["houses"])

