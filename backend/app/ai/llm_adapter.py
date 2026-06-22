from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass(slots=True)
class ChatResult:
    content: str
    usage: dict[str, int]
    latency_ms: int
    provider: str
    model_version: str
    cost_estimate: float


class LLMAdapter:
    """Provider abstraction.

    The MVP keeps this adapter as an explicit seam. Without API credentials it
    raises a clear error and callers should fall back to rules/templates.
    """

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None, options: dict | None = None) -> ChatResult:
        raise RuntimeError("LLM provider is not configured; use rules/template fallback.")


class OpenAICompatibleLLMAdapter(LLMAdapter):
    def __init__(self, provider: str, api_key: str, base_url: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None, options: dict | None = None) -> ChatResult:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": (options or {}).get("temperature", 0.2),
        }
        if schema is not None:
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        choice = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        total_tokens = int(usage.get("total_tokens") or usage.get("total_token_count") or 0)
        return ChatResult(
            content=choice.get("content", ""),
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": total_tokens,
            },
            latency_ms=int((time.perf_counter() - started) * 1000),
            provider=self.provider,
            model_version=data.get("model") or self.model,
            cost_estimate=estimate_llm_cost(total_tokens),
        )


def estimate_llm_cost(total_tokens: int) -> float:
    return round((total_tokens / 1000) * 0.002, 6)


def build_llm_adapter_from_env() -> LLMAdapter | None:
    if settings.primary_llm_provider == "deepseek" and settings.deepseek_api_key:
        return OpenAICompatibleLLMAdapter(
            provider="deepseek",
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
    if settings.primary_llm_provider == "qwen" and settings.qwen_api_key:
        return OpenAICompatibleLLMAdapter(
            provider="qwen",
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
        )
    if settings.fallback_llm_provider == "qwen" and settings.qwen_api_key:
        return OpenAICompatibleLLMAdapter(
            provider="qwen",
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
        )
    return None


def get_llm_runtime_status(
    primary_provider: str | None = None,
    fallback_provider: str | None = None,
    deepseek_api_key: str | None = None,
    qwen_api_key: str | None = None,
) -> dict:
    primary = primary_provider if primary_provider is not None else settings.primary_llm_provider
    fallback = fallback_provider if fallback_provider is not None else settings.fallback_llm_provider
    deepseek_key = deepseek_api_key if deepseek_api_key is not None else settings.deepseek_api_key
    qwen_key = qwen_api_key if qwen_api_key is not None else settings.qwen_api_key

    active_provider = None
    if primary == "deepseek" and deepseek_key:
        active_provider = "deepseek"
    elif primary == "qwen" and qwen_key:
        active_provider = "qwen"
    elif fallback == "qwen" and qwen_key:
        active_provider = "qwen"

    return {
        "llm_configured": active_provider is not None,
        "llm_active_provider": active_provider,
    }
