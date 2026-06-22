from __future__ import annotations

import json


class OutputParseError(ValueError):
    pass


def parse_json_object(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OutputParseError(str(exc)) from exc
    if not isinstance(value, dict):
        raise OutputParseError("LLM output must be a JSON object.")
    return value

