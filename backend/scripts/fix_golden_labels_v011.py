"""One-shot audit script: apply human review decisions to 4 disputed golden-set samples.

Decisions (product-side, 2026-06-22):
  gold_v011_164 "厨房下水返水把插排泡了"   floor_drain_smell -> drain_blocked (返水泡插排与反味无关)
  gold_v011_105 "墙面渗水流到开关下面了"   wall_mold          -> water_leak    (渗水是漏水核心词)
  gold_v011_173 "厨房下水慢还反味"         floor_drain_smell -> drain_blocked (下水慢更可操作)
  gold_v011_116 "墙面有水痕但已经干了"     wall_mold          -> water_leak    (水痕偏漏水)

urgency / is_high_risk / risk_type / expected_path 保持不变（仅纠正分类标签）。
review_status -> human_reviewed（仅这 4 条；其余 196 条仍 pending_human_review）。
"""
from __future__ import annotations

import json
from pathlib import Path

GOLDEN = Path(__file__).resolve().parents[1] / "eval" / "golden_set_v0.1.1_200.jsonl"

CHANGES = {
    "gold_v011_164": ("water", "drain_blocked", "马桶/下水堵塞"),
    "gold_v011_105": ("water", "water_leak", "漏水渗水"),
    "gold_v011_173": ("water", "drain_blocked", "马桶/下水堵塞"),
    "gold_v011_116": ("water", "water_leak", "漏水渗水"),
}


def main() -> int:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    changed: list[str] = []
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        d = json.loads(line)
        if d["id"] in CHANGES:
            primary, secondary, scenario = CHANGES[d["id"]]
            d["expected"]["primary"] = primary
            d["expected"]["secondary"] = secondary
            d["meta"]["scenario_name"] = scenario
            d["meta"]["review_status"] = "human_reviewed"
            changed.append(d["id"])
        out.append(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    GOLDEN.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"changed {len(changed)}: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
