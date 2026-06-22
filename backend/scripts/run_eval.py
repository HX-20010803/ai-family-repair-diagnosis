from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.diagnosis_service import DiagnosisService  # noqa: E402


GOLDEN_SET_PATH = BACKEND_DIR / "eval" / "golden_set.jsonl"
BASELINE_REPORT_PATH = BACKEND_DIR / "eval" / "baseline_v0.1.md"


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[dict]:
    samples: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        sample = json.loads(line)
        if not {"id", "input", "expected"}.issubset(sample):
            raise ValueError(f"Invalid sample at line {line_number}: missing required fields")
        samples.append(sample)
    return samples


def evaluate(samples: list[dict]) -> dict:
    service = DiagnosisService(llm_adapter=None)
    classification_hits = 0
    urgency_hits = 0
    high_risk_total = 0
    high_risk_hits = 0
    predicted_high_risk_total = 0
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows: list[dict] = []

    for sample in samples:
        text = sample["input"]
        expected = sample["expected"]
        normalized = service._normalize(text)
        fault = service._classify(normalized)
        risk = service.risk_service.assess(normalized)
        predicted_urgency = risk.level if risk.triggered and risk.level else service._default_urgency(fault.secondary, normalized)
        predicted_high_risk = bool(risk.triggered)

        classification_ok = fault.secondary == expected["secondary"]
        urgency_ok = predicted_urgency == expected["urgency"]
        high_risk_expected = bool(expected["is_high_risk"])

        classification_hits += int(classification_ok)
        urgency_hits += int(urgency_ok)
        high_risk_total += int(high_risk_expected)
        high_risk_hits += int(high_risk_expected and predicted_high_risk)
        predicted_high_risk_total += int(predicted_high_risk)
        confusion[expected["secondary"]][fault.secondary] += 1

        rows.append(
            {
                "id": sample["id"],
                "input": text,
                "expected_secondary": expected["secondary"],
                "predicted_secondary": fault.secondary,
                "expected_urgency": expected["urgency"],
                "predicted_urgency": predicted_urgency,
                "expected_high_risk": high_risk_expected,
                "predicted_high_risk": predicted_high_risk,
                "classification_ok": classification_ok,
                "urgency_ok": urgency_ok,
                "evidence": fault.evidence,
            }
        )

    total = len(samples)
    false_positive_count = max(0, predicted_high_risk_total - high_risk_hits)
    actual_negative_count = total - high_risk_total

    return {
        "total": total,
        "classification_acc": _ratio(classification_hits, total),
        "urgency_acc": _ratio(urgency_hits, total),
        "high_risk_recall": _ratio(high_risk_hits, high_risk_total),
        "high_risk_false_positive_rate": _ratio(false_positive_count, actual_negative_count),
        "high_risk_hits": high_risk_hits,
        "high_risk_total": high_risk_total,
        "predicted_high_risk_total": predicted_high_risk_total,
        "llm_call_count": 0,
        "llm_call_rate": 0.0,
        "confusion_matrix": {key: dict(value) for key, value in sorted(confusion.items())},
        "rows": rows,
    }


def write_report(result: dict, path: Path = BASELINE_REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI 家庭维修诊断助手评测 baseline v0.1",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Samples: {result['total']}",
        f"- Classification accuracy: {_percent(result['classification_acc'])}",
        f"- Urgency accuracy: {_percent(result['urgency_acc'])}",
        f"- High-risk recall: {_percent(result['high_risk_recall'])} ({result['high_risk_hits']}/{result['high_risk_total']})",
        f"- High-risk false-positive rate: {_percent(result['high_risk_false_positive_rate'])}",
        f"- LLM call rate: {_percent(result['llm_call_rate'])} ({result['llm_call_count']}/{result['total']})",
        "",
        "## Confusion Matrix",
        "",
        "Expected | Predicted counts",
        "--- | ---",
    ]
    for expected, predicted_counts in result["confusion_matrix"].items():
        counts = ", ".join(f"{predicted}: {count}" for predicted, count in sorted(predicted_counts.items()))
        lines.append(f"{expected} | {counts}")

    lines.extend(
        [
            "",
            "## Failed Samples",
            "",
            "ID | Expected | Predicted | Expected urgency | Predicted urgency | Evidence",
            "--- | --- | --- | --- | --- | ---",
        ]
    )
    for row in result["rows"]:
        if row["classification_ok"] and row["urgency_ok"] and row["expected_high_risk"] == row["predicted_high_risk"]:
            continue
        evidence = ", ".join(row["evidence"])
        lines.append(
            f"{row['id']} | {row['expected_secondary']} | {row['predicted_secondary']} | "
            f"{row['expected_urgency']} | {row['predicted_urgency']} | {evidence}"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_failure_artifacts(result, path)


def write_failure_artifacts(result: dict, report_path: Path) -> None:
    suffix = _version_suffix(report_path)
    misclassified_path = report_path.with_name(f"misclassified_{suffix}.jsonl")
    high_risk_errors_path = report_path.with_name(f"high_risk_errors_{suffix}.jsonl")

    misclassified_rows = [
        row for row in result["rows"] if not row["classification_ok"] or not row["urgency_ok"]
    ]
    high_risk_error_rows = [
        row
        for row in result["rows"]
        if row["expected_high_risk"] != row["predicted_high_risk"]
    ]
    _write_jsonl(misclassified_path, misclassified_rows)
    _write_jsonl(high_risk_errors_path, high_risk_error_rows)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _version_suffix(path: Path) -> str:
    stem = path.stem
    if stem.startswith("baseline_"):
        return stem.removeprefix("baseline_")
    return stem


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    input_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else GOLDEN_SET_PATH
    report_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else BASELINE_REPORT_PATH
    samples = load_golden_set(input_path)
    result = evaluate(samples)
    write_report(result, report_path)
    print(
        json.dumps(
            {
                "samples": result["total"],
                "classification_acc": result["classification_acc"],
                "urgency_acc": result["urgency_acc"],
                "high_risk_recall": result["high_risk_recall"],
                "high_risk_false_positive_rate": result["high_risk_false_positive_rate"],
                "llm_call_rate": result["llm_call_rate"],
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
