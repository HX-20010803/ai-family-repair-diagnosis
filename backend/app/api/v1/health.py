from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.ai.llm_adapter import get_llm_runtime_status
from app.core.config import settings
from app.db.session import engine
from app.services.content_safety_service import get_content_safety_runtime_status
from app.services.rag_service import RagService


router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except Exception:
        database = "error"
    return {
        "status": "ok",
        "database": database,
        "llm_primary": settings.primary_llm_provider,
        **get_llm_runtime_status(),
        **get_content_safety_runtime_status(),
        "deployment_mode": settings.deployment_mode,
        "rules_version": "2026.06",
        "knowledge_version": RagService.KNOWLEDGE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
