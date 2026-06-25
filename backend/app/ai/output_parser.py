from __future__ import annotations

import json
import re


class OutputParseError(ValueError):
    pass


def parse_json_object(raw: str) -> dict:
    """从 LLM 输出里解析 JSON 对象，容忍常见的脏格式：

    - ```json ... ``` markdown 代码块包裹
    - JSON 前后带说明文字（提取第一个 {...}）
    """
    text = (raw or "").strip()

    # 去 markdown 代码块包裹
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        # 提取第一个 {...}（LLM 可能在 JSON 前后带了说明文字）
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise OutputParseError(f"no JSON object found in LLM output: {raw[:120]!r}")
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise OutputParseError(str(exc)) from exc

    if not isinstance(value, dict):
        raise OutputParseError("LLM output must be a JSON object.")
    return value
