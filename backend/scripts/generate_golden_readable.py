"""Regenerate eval/golden_set_v0.1.1_200_readable.md from the current golden set.

Run after any golden-set label change so the human-readable view stays in sync.
Distributions are computed dynamically (no hardcoded counts).
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1] / "eval"
GOLDEN = EVAL / "golden_set_v0.1.1_200.jsonl"
OUT = EVAL / "golden_set_v0.1.1_200_readable.md"


def _esc(x: object) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    samples = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    order: list[str] = []
    groups: dict[str, list[dict]] = collections.OrderedDict()
    for s in samples:
        sc = s["meta"]["scenario_name"]
        if sc not in groups:
            groups[sc] = []
            order.append(sc)
        groups[sc].append(s)

    hr = sum(1 for s in samples if s["expected"].get("is_high_risk"))
    urg = collections.Counter(s["expected"]["urgency"] for s in samples)
    review = collections.Counter(s["meta"].get("review_status", "?") for s in samples)

    lines = [
        "# 黄金评测集 v0.1.1 可读版（200 条）",
        "",
        f"- 总计 {len(samples)} 条",
        f"- 高风险 {hr} 条（⚠️ 标记），紧急分布：" + " / ".join(f"{k} {v}" for k, v in sorted(urg.items())),
        f"- 审核状态：" + " / ".join(f"{k} {v}" for k, v in review.items()),
        "",
    ]
    for sc in order:
        items = groups[sc]
        sec = items[0]["expected"]["secondary"]
        lines += [
            f"## {sc}（{sec}）{len(items)} 条",
            "",
            "| ID | 输入 | 紧急 | 高风险 | 推荐处理路径 |",
            "|---|---|:-:|:-:|---|",
        ]
        for s in items:
            e = s["expected"]
            hr_mark = "⚠️" if e.get("is_high_risk") else ""
            lines.append(f"| {s['id']} | {_esc(s['input'])} | {e['urgency']} | {hr_mark} | {_esc(e.get('expected_path', ''))} |")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(samples)} samples, review={dict(review)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
