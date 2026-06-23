from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.services.diagnosis_service import DiagnosisService


router = APIRouter()


class CreateSessionRequest(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    city_tier: str | None = None


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    city_tier: str | None = None


class CompleteRequest(BaseModel):
    city_tier: str | None = None


class FeedbackRequest(BaseModel):
    rating: Literal["useful", "neutral", "not_useful"]
    reason_tags: list[str] = Field(default_factory=list, max_length=8)
    comment: str | None = Field(default=None, max_length=500)


@router.post("/sessions")
def create_session(
    payload: CreateSessionRequest,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db: Session = Depends(get_db),
) -> dict:
    diagnosis_service = DiagnosisService(repository=DiagnosisRepository(db))
    response = diagnosis_service.handle_message(
        anonymous_token=x_anonymous_token,
        text=payload.text,
        city_tier=payload.city_tier,
    )
    return _response_to_dict(response)


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: str,
    payload: MessageRequest,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db: Session = Depends(get_db),
) -> dict:
    diagnosis_service = DiagnosisService(repository=DiagnosisRepository(db))
    response = diagnosis_service.handle_message(
        anonymous_token=x_anonymous_token,
        text=payload.text,
        session_id=session_id,
        city_tier=payload.city_tier,
    )
    return _response_to_dict(response)


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: str,
    payload: CompleteRequest | None = None,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db: Session = Depends(get_db),
) -> dict:
    repository = DiagnosisRepository(db)
    session = repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND"})
    messages = repository.list_messages(session_id)
    merged_text = " ".join(message.content for message in messages if message.role == "user")
    diagnosis_service = DiagnosisService(repository=repository)
    response = diagnosis_service.handle_message(
        anonymous_token=x_anonymous_token,
        text=merged_text or "用户要求生成诊断结果",
        session_id=session_id,
        city_tier=payload.city_tier if payload else None,
    )
    return _response_to_dict(response)


@router.get("/results/{result_id}")
def get_result(result_id: str, db: Session = Depends(get_db)) -> dict:
    result = DiagnosisRepository(db).get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "RESULT_NOT_FOUND"})
    return result.result_json


@router.post("/results/{result_id}/feedback")
def submit_feedback(
    result_id: str,
    payload: FeedbackRequest,
    x_anonymous_token: str = Header(default="anonymous-demo"),
    db: Session = Depends(get_db),
) -> dict:
    repository = DiagnosisRepository(db)
    result = repository.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "RESULT_NOT_FOUND"})
    feedback = repository.upsert_feedback(
        result_id=result.id,
        session_id=result.session_id,
        anonymous_token=x_anonymous_token,
        rating=payload.rating,
        reason_tags=payload.reason_tags,
        comment=payload.comment,
    )
    repository.commit()
    return {
        "id": feedback.id,
        "result_id": feedback.result_id,
        "rating": feedback.rating,
        "reason_tags": feedback.reason_tags,
        "comment": feedback.comment,
    }


def _response_to_dict(response) -> dict:
    payload = asdict(response)
    if response.type == "blocked":
        status_code = 451
        if response.error_code == "QUOTA_EXCEEDED":
            status_code = 429
        if response.error_code == "CONTENT_SAFETY_UNAVAILABLE":
            status_code = 503
        raise HTTPException(status_code=status_code, detail={"code": response.error_code, "message": response.safety_notice})
    return payload
