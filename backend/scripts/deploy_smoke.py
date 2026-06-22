from __future__ import annotations

import json
import sys
from uuid import uuid4
from urllib.request import Request, urlopen


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ANONYMOUS_TOKEN = f"deploy-smoke-{uuid4()}"


def request(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json", "X-Anonymous-Token": ANONYMOUS_TOKEN},
        method="GET" if payload is None else "POST",
    )
    with urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


health = request("/api/v1/health")
diagnosis = request("/api/v1/diagnosis/sessions", {"text": "插座发黑还冒烟了，现在还能继续用吗"})
result = diagnosis["result"]

assert health["status"] == "ok", health
assert diagnosis["type"] == "result", diagnosis
assert result["urgency"]["level"] == "S", diagnosis

print(
    json.dumps(
        {
            "health": health,
            "diagnosis_type": diagnosis["type"],
            "urgency": "S",
            "model_provider": result.get("model_provider"),
            "model_version": result.get("model_version"),
        },
        ensure_ascii=False,
    )
)
