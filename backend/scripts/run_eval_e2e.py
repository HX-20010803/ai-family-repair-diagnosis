"""End-to-end golden-set evaluation through real DiagnosisService.handle_message.

Unlike run_eval.py (which tests the template classifier + risk rules in isolation
with llm_adapter=None), this script drives the full orchestration: real LLM
adapter, real classification path, real urgency and risk wiring.

Design choices (why):
- Content safety is replaced with a passthrough provider. The eval measures
  diagnosis quality, not TMS availability — TMS is exercised by deploy_smoke.
- Follow-up questions are disabled, otherwise the `questions` branch yields no
  fault_type and samples cannot be compared on classification.
- High-risk is taken from risk_service.assess().triggered to match run_eval.py.
- LLM usage is split into two independent rates:
  * cls_llm_call_rate — classification stage actually called DeepSeek
    (the prod vs llm_full differentiator; template-first returns rule_result
    without touching the LLM, so last_cost_log stays None).
  * gen_llm_call_rate — result-generation stage used the LLM
    (model_provider != 'local-template'); both modes attempt this, so it mostly
    reflects DeepSeek availability/降级 under load.

Modes:
  prod     - real production path (template-first, DeepSeek only when confidence < 0.7)
  llm_full - force every sample through DeepSeek classification (bypass template-first)

Usage:
  python scripts/run_eval_e2e.py [golden_path] [--limit N] [--mode both|prod|llm_full]
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.content_safety_service import ContentSafetyProvider, ContentSafetyService  # noqa: E402
from app.services.diagnosis_service import DiagnosisService  # noqa: E402


GOLDEN_SET_PATH = BACKEND_DIR / "eval" / "golden_set_v0.1.1_200.jsonl"
EVAL_DIR = BACKEND_DIR / "eval"


class _PassthroughSafety(ContentSafetyProvider):
    name = "eval-passthrough"

    def check(self, text: str) -> tuple[bool, list[str]]:
        return True, []


@dataclass
class ModeConfig:
    name: str
    title: str
    force_full_llm: bool


MODES = [
    ModeConfig("prod", "production path (template-first + DeepSeek fallback)", False),
    ModeConfig("llm_full", "full DeepSeek (every sample bypasses template-first)", True),
]


def load_samples(path: Path) -> list[dict]:
    samples: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        sample = json.loads(line)
        if not {"id", "input", "expected"}.issubset(sample):
            raise ValueError(f"invalid sample at line {line_no}: missing id/input/expected")
        samples.append(sample)
    return samples


def build_service(mode: ModeConfig) -> DiagnosisService:
    service = DiagnosisService(content_safety_service=ContentSafetyService(provider=_PassthroughSafety()))
    # disable follow-up questions so every sample yields a comparable result
    service.question_service.should_ask = lambda *a, **k: False
    if mode.force_full_llm:
        # bypass template-first (confidence >= threshold short-circuits to template);
        # raising the threshold above any achievable confidence forces DeepSeek on every sample
        service.classification_service.HIGH_CONFIDENCE_THRESHOLD = 1.1
    return service


def evaluate(samples: list[dict], mode: ModeConfig) -> dict:
    service = build_service(mode)
    cls_hits = urg_hits = hr_hits = hr_total = pred_hr_total = 0
    cls_llm_calls = gen_llm_calls = crash_count = 0
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows: list[dict] = []

    for idx, sample in enumerate(samples):
        if idx > 0 and idx % 20 == 0:
            print(f"[{mode.name}] {idx}/{len(samples)} processed", file=sys.stderr)
        text = sample["input"]
        expected = sample["expected"]
        exp_secondary = expected["secondary"]
        exp_urgency = expected["urgency"]
        exp_hr = bool(expected.get("is_high_risk", False))

        try:
            resp = service.handle_message(anonymous_token=f"eval-{mode.name}-{idx}", text=text)
        except Exception as exc:
            # isolate per-sample crashes (e.g. DeepSeek httpx errors outside
            # handle_message's catch list) so one bad sample can't sink the whole run
            crash_count += 1
            print(f"[{mode.name}] sample {idx} {sample['id']} CRASHED: {type(exc).__name__}: {exc}", file=sys.stderr)
            rows.append({
                "id": sample["id"], "input": text,
                "expected_secondary": exp_secondary, "predicted_secondary": None,
                "expected_urgency": exp_urgency, "predicted_urgency": None,
                "model_provider": None, "cls_used_llm": False,
                "classification_ok": False, "urgency_ok": False,
                "expected_high_risk": exp_hr, "predicted_high_risk": False,
                "error": f"handle_message crashed: {type(exc).__name__}: {exc}",
            })
            continue
        if resp.type != "result" or resp.result is None:
            rows.append({
                "id": sample["id"], "input": text,
                "expected_secondary": exp_secondary, "predicted_secondary": None,
                "expected_urgency": exp_urgency, "predicted_urgency": None,
                "model_provider": None, "cls_used_llm": False,
                "classification_ok": False, "urgency_ok": False,
                "expected_high_risk": exp_hr, "predicted_high_risk": False,
                "error": f"unexpected response type={resp.type}",
            })
            continue

        result = resp.result
        pred_secondary = result.fault_type.secondary
        pred_urgency = result.urgency.level
        pred_hr = bool(service.risk_service.assess(service._normalize(text)).triggered)
        provider = result.model_provider or "unknown"
        # classification stage: classify() resets last_cost_log at entry, then sets it
        # only when _confirm_with_llm succeeds. So non-None means DeepSeek classified.
        cls_used_llm = service.classification_service.last_cost_log is not None
        gen_used_llm = provider != "local-template"

        c_ok = pred_secondary == exp_secondary
        u_ok = pred_urgency == exp_urgency
        cls_hits += int(c_ok)
        urg_hits += int(u_ok)
        hr_total += int(exp_hr)
        hr_hits += int(exp_hr and pred_hr)
        pred_hr_total += int(pred_hr)
        cls_llm_calls += int(cls_used_llm)
        gen_llm_calls += int(gen_used_llm)
        confusion[exp_secondary][pred_secondary] += 1

        rows.append({
            "id": sample["id"], "input": text,
            "expected_secondary": exp_secondary, "predicted_secondary": pred_secondary,
            "expected_urgency": exp_urgency, "predicted_urgency": pred_urgency,
            "model_provider": provider, "cls_used_llm": cls_used_llm,
            "classification_ok": c_ok, "urgency_ok": u_ok,
            "expected_high_risk": exp_hr, "predicted_high_risk": pred_hr,
        })

    total = len(samples)
    fp = max(0, pred_hr_total - hr_hits)
    neg = total - hr_total
    return {
        "mode": mode.name, "mode_title": mode.title, "total": total,
        "classification_acc": _ratio(cls_hits, total),
        "urgency_acc": _ratio(urg_hits, total),
        "high_risk_recall": _ratio(hr_hits, hr_total),
        "high_risk_false_positive_rate": _ratio(fp, neg),
        "high_risk_hits": hr_hits, "high_risk_total": hr_total,
        "predicted_high_risk_total": pred_hr_total,
        "cls_llm_call_count": cls_llm_calls, "cls_llm_call_rate": _ratio(cls_llm_calls, total),
        "gen_llm_call_count": gen_llm_calls, "gen_llm_call_rate": _ratio(gen_llm_calls, total),
        "crash_count": crash_count,
        "confusion_matrix": {k: dict(v) for k, v in sorted(confusion.items())},
        "rows": rows,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_report(result: dict, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# AI 家庭维修诊断助手评测 baseline v0.1.1 — {result['mode']}",
        "",
        f"- Mode: {result['mode_title']}",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Samples: {result['total']}",
        f"- Classification accuracy: {_percent(result['classification_acc'])}",
        f"- Urgency accuracy: {_percent(result['urgency_acc'])}",
        f"- High-risk recall: {_percent(result['high_risk_recall'])} ({result['high_risk_hits']}/{result['high_risk_total']})",
        f"- High-risk false-positive rate: {_percent(result['high_risk_false_positive_rate'])}",
        f"- Classification LLM call rate: {_percent(result['cls_llm_call_rate'])} ({result['cls_llm_call_count']}/{result['total']})",
        f"- Generation LLM call rate: {_percent(result['gen_llm_call_rate'])} ({result['gen_llm_call_count']}/{result['total']})",
        f"- Crashed samples (handle_message raised): {result['crash_count']}/{result['total']}",
        "",
        "## Confusion Matrix",
        "",
        "Expected | Predicted counts",
        "--- | ---",
    ]
    for expected, predicted_counts in result["confusion_matrix"].items():
        counts = ", ".join(f"{p}: {c}" for p, c in sorted(predicted_counts.items()))
        lines.append(f"{expected} | {counts}")

    lines.extend([
        "",
        "## Failed Samples",
        "",
        "ID | Expected | Predicted | Exp urgency | Pred urgency | Provider | Cls LLM",
        "--- | --- | --- | --- | --- | --- | ---",
    ])
    for row in result["rows"]:
        if row.get("error"):
            lines.append(f"{row['id']} | {row['expected_secondary']} | ERROR | {row['expected_urgency']} | - | {row['error']} | -")
            continue
        if row["classification_ok"] and row["urgency_ok"] and row["expected_high_risk"] == row["predicted_high_risk"]:
            continue
        cls_llm = "yes" if row["cls_used_llm"] else "no"
        lines.append(
            f"{row['id']} | {row['expected_secondary']} | {row['predicted_secondary']} | "
            f"{row['expected_urgency']} | {row['predicted_urgency']} | {row['model_provider']} | {cls_llm}"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_failure_artifacts(result, report_path)


def _write_failure_artifacts(result: dict, report_path: Path) -> None:
    stem = report_path.stem  # baseline_v0.1.1_<mode>
    suffix = stem.removeprefix("baseline_")
    mis_path = report_path.with_name(f"misclassified_{suffix}.jsonl")
    hr_path = report_path.with_name(f"high_risk_errors_{suffix}.jsonl")
    mis_rows = [r for r in result["rows"] if not r.get("error") and (not r["classification_ok"] or not r["urgency_ok"])]
    hr_rows = [r for r in result["rows"] if not r.get("error") and r["expected_high_risk"] != r["predicted_high_risk"]]
    _write_jsonl(mis_path, mis_rows)
    _write_jsonl(hr_path, hr_rows)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("golden_path", nargs="?", default=str(GOLDEN_SET_PATH))
    parser.add_argument("--limit", type=int, default=0, help="limit samples (0 = all)")
    parser.add_argument("--mode", choices=["both", "prod", "llm_full"], default="both")
    args = parser.parse_args()

    samples = load_samples(Path(args.golden_path))
    if args.limit > 0:
        samples = samples[: args.limit]

    selected = MODES if args.mode == "both" else [m for m in MODES if m.name == args.mode]
    summaries: list[dict] = []
    for mode in selected:
        result = evaluate(samples, mode)
        report_path = EVAL_DIR / f"baseline_v0.1.1_{mode.name}.md"
        write_report(result, report_path)
        summaries.append({
            "mode": result["mode"], "samples": result["total"],
            "classification_acc": result["classification_acc"],
            "urgency_acc": result["urgency_acc"],
            "high_risk_recall": result["high_risk_recall"],
            "high_risk_false_positive_rate": result["high_risk_false_positive_rate"],
            "cls_llm_call_rate": result["cls_llm_call_rate"],
            "gen_llm_call_rate": result["gen_llm_call_rate"],
            "crashes": result["crash_count"],
            "report": str(report_path),
        })

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
