import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
RUN_EVAL_PATH = PROJECT_DIR / "backend" / "scripts" / "run_eval.py"
GOLDEN_SET_PATH = PROJECT_DIR / "backend" / "eval" / "golden_set.jsonl"
GOLDEN_SET_200_PATH = PROJECT_DIR / "backend" / "eval" / "golden_set_v0.1.1_200.jsonl"


def load_run_eval_module():
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EvalScriptTest(unittest.TestCase):
    def test_golden_set_has_30_seed_samples_and_high_risk_coverage(self):
        run_eval = load_run_eval_module()

        samples = run_eval.load_golden_set(GOLDEN_SET_PATH)

        self.assertEqual(len(samples), 30)
        self.assertEqual(len({sample["expected"]["secondary"] for sample in samples}), 10)
        self.assertGreaterEqual(sum(1 for sample in samples if sample["expected"]["is_high_risk"]), 6)

    def test_evaluate_returns_core_metrics_without_http(self):
        run_eval = load_run_eval_module()

        samples = run_eval.load_golden_set(GOLDEN_SET_PATH)
        result = run_eval.evaluate(samples)

        self.assertIn("classification_acc", result)
        self.assertIn("urgency_acc", result)
        self.assertIn("high_risk_recall", result)
        self.assertIn("confusion_matrix", result)

    def test_v011_golden_set_has_200_samples_and_required_distribution(self):
        run_eval = load_run_eval_module()

        samples = run_eval.load_golden_set(GOLDEN_SET_200_PATH)
        counts_by_secondary: dict[str, int] = {}
        samples_by_id = {sample["id"]: sample for sample in samples}
        for sample in samples:
            secondary = sample["expected"]["secondary"]
            counts_by_secondary[secondary] = counts_by_secondary.get(secondary, 0) + 1
            self.assertIn("expected_path", sample["expected"])

        self.assertEqual(len(samples), 200)
        self.assertEqual(
            counts_by_secondary,
            {
                "water_leak": 22,
                "drain_blocked": 22,
                "ac_not_cooling": 20,
                "circuit_trip": 20,
                "lock_failure": 20,
                "wall_mold": 18,
                "water_heater_failure": 20,
                "range_hood_gas_stove": 20,
                "floor_drain_smell": 18,
                "window_hardware": 20,
            },
        )
        self.assertGreaterEqual(sum(1 for sample in samples if sample["expected"]["is_high_risk"]), 50)
        self.assertEqual(
            {
                sample_id: (
                    samples_by_id[sample_id]["expected"]["secondary"],
                    samples_by_id[sample_id]["meta"]["review_status"],
                )
                for sample_id in ("gold_v011_164", "gold_v011_105", "gold_v011_173", "gold_v011_116")
            },
            {
                "gold_v011_164": ("drain_blocked", "human_reviewed"),
                "gold_v011_105": ("water_leak", "human_reviewed"),
                "gold_v011_173": ("drain_blocked", "human_reviewed"),
                "gold_v011_116": ("water_leak", "human_reviewed"),
            },
        )

    def test_write_report_emits_v011_failure_artifacts(self):
        run_eval = load_run_eval_module()
        result = {
            "total": 1,
            "classification_acc": 0.0,
            "urgency_acc": 0.0,
            "high_risk_recall": 0.0,
            "high_risk_false_positive_rate": 0.0,
            "high_risk_hits": 0,
            "high_risk_total": 1,
            "predicted_high_risk_total": 0,
            "llm_call_count": 0,
            "llm_call_rate": 0.0,
            "confusion_matrix": {"circuit_trip": {"water_leak": 1}},
            "rows": [
                {
                    "id": "case_001",
                    "input": "插座冒烟了",
                    "expected_secondary": "circuit_trip",
                    "predicted_secondary": "water_leak",
                    "expected_urgency": "S",
                    "predicted_urgency": "A",
                    "expected_high_risk": True,
                    "predicted_high_risk": False,
                    "classification_ok": False,
                    "urgency_ok": False,
                    "evidence": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "baseline_v0.1.1.md"

            run_eval.write_report(result, report_path)

            misclassified = Path(tmpdir) / "misclassified_v0.1.1.jsonl"
            high_risk_errors = Path(tmpdir) / "high_risk_errors_v0.1.1.jsonl"
            self.assertTrue(misclassified.exists())
            self.assertTrue(high_risk_errors.exists())
            self.assertEqual(json.loads(misclassified.read_text(encoding="utf-8").strip())["id"], "case_001")
            self.assertEqual(json.loads(high_risk_errors.read_text(encoding="utf-8").strip())["id"], "case_001")


if __name__ == "__main__":
    unittest.main()
