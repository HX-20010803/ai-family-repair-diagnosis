from __future__ import annotations

import json
import sys
from uuid import uuid4
from urllib.request import Request, urlopen


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ANONYMOUS_TOKEN = f"llm-smoke-{uuid4()}"


def request(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Anonymous-Token": ANONYMOUS_TOKEN,
        },
        method="GET" if payload is None else "POST",
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = request("/api/v1/health")
diagnosis = request("/api/v1/diagnosis/sessions", {"text": "插座发黑还冒烟了，现在还能继续用吗"})
result = diagnosis.get("result") or {}

summary = {
    "health_database": health.get("database"),
    "llm_configured": health.get("llm_configured"),
    "llm_active_provider": health.get("llm_active_provider"),
    "diagnosis_type": diagnosis.get("type"),
    "model_provider": result.get("model_provider"),
    "model_version": result.get("model_version"),
    "urgency": (result.get("urgency") or {}).get("level"),
}

print(json.dumps(summary, ensure_ascii=False, indent=2))

assert health.get("database") == "ok", health
assert health.get("llm_configured") is True, "LLM API key is not visible to the running backend process."
assert diagnosis.get("type") == "result", diagnosis
assert result.get("model_provider") in {"deepseek", "qwen"}, "Diagnosis fell back to local-template instead of real LLM."
