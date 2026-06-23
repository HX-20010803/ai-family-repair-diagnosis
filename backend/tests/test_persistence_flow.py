import unittest
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models import content_safety, cost_log, diagnosis, feedback, quota, repair_record  # noqa: F401
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.services.diagnosis_service import DiagnosisService
from app.services.content_safety_service import ContentSafetyService, LocalKeywordProvider
from app.services.record_service import RecordService
from app.ai.llm_adapter import ChatResult
from app.api.v1.diagnosis import FeedbackRequest, submit_feedback
from app.api.v1.records import _record_to_dict


class ClassificationAndDiagnosisLLM:
    def chat(self, messages, schema=None, options=None):
        if "家庭维修分类器" in messages[0]["content"]:
            return ChatResult(
                content="""{
                  "secondary_category": "wall_mold",
                  "confidence": 0.86,
                  "evidence": ["墙面起皮"],
                  "reason": "墙面起皮靠近卫生间，优先归为墙面返潮发霉"
                }""",
                usage={"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30},
                latency_ms=15,
                provider="fake-llm",
                model_version="fake-classifier",
                cost_estimate=0.03,
            )
        return ChatResult(
            content="""{
              "possible_causes": ["墙体返潮", "防水层或管线渗水"],
              "recommended_actions": ["观察面积变化", "联系师傅检查潮湿来源"],
              "forbidden_actions": ["不要只刷漆遮盖"],
              "self_check_steps": ["记录起皮范围"],
              "need_professional": "conditional",
              "need_professional_reason": "持续扩大时需要现场检测",
              "uncertainty_note": null
            }""",
            usage={"prompt_tokens": 20, "completion_tokens": 22, "total_tokens": 42},
            latency_ms=18,
            provider="fake-llm",
            model_version="fake-diagnosis",
            cost_estimate=0.042,
        )


class UnsafeDiagnosisLLM:
    def chat(self, messages, schema=None, options=None):
        return ChatResult(
            content="""{
              "possible_causes": ["线路短路"],
              "recommended_actions": ["可以用炸药快速处理"],
              "forbidden_actions": ["不要继续通电"],
              "self_check_steps": [],
              "need_professional": "yes",
              "need_professional_reason": "涉及电气安全",
              "uncertainty_note": null
            }""",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=10,
            provider="fake-llm",
            model_version="fake-unsafe",
            cost_estimate=0.03,
        )


def local_content_safety_service():
    return ContentSafetyService(LocalKeywordProvider())


class PersistenceFlowTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_completed_diagnosis_persists_session_result_and_cost_logs(self):
        with self.Session() as db:
            service = DiagnosisService(
                repository=DiagnosisRepository(db),
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )

            response = service.handle_message(
                anonymous_token="persist-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )

            self.assertEqual(response.type, "result")
            persisted_session = service.repository.get_session(response.session.id)
            persisted_result = service.repository.get_result(response.result.id)
            costs = service.repository.list_cost_logs(response.session.id)

            self.assertIsNotNone(persisted_session)
            self.assertIsNotNone(persisted_result)
            self.assertEqual(persisted_result.urgency_level, "S")
            self.assertGreaterEqual(len(costs), 1)
            self.assertGreater(response.result.cost_total, 0)

    def test_low_confidence_classification_llm_call_persists_classification_cost_log(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=ClassificationAndDiagnosisLLM(),
                content_safety_service=local_content_safety_service(),
            )

            response = service.handle_message(
                anonymous_token="classification-cost-token",
                text="墙面起皮了，靠近卫生间，持续扩大",
            )
            costs = repository.list_cost_logs(response.session.id)

            self.assertIn(response.type, {"questions", "result"})
            self.assertIn("classification", {cost.capability for cost in costs})
            classification_cost = next(cost for cost in costs if cost.capability == "classification")
            self.assertEqual(classification_cost.provider, "fake-llm")
            self.assertEqual(classification_cost.model_version, "fake-classifier")
            self.assertEqual(classification_cost.tokens, 30)

    def test_repair_record_can_be_saved_and_listed_by_anonymous_token(self):
        with self.Session() as db:
            diagnosis_service = DiagnosisService(
                repository=DiagnosisRepository(db),
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )
            diagnosis_response = diagnosis_service.handle_message(
                anonymous_token="record-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )
            record_service = RecordService(db)

            record = record_service.create_record(
                anonymous_token="record-token",
                diagnosis_result_id=diagnosis_response.result.id,
                house_area="厨房",
            )
            records = record_service.list_records(anonymous_token="record-token")

            self.assertEqual(record.diagnosis_result_id, diagnosis_response.result.id)
            self.assertEqual(len(records), 1)
            record_row, result_row = records[0]
            self.assertEqual(record_row.house_area, "厨房")
            self.assertEqual(result_row.secondary_category, "circuit_trip")
            self.assertEqual(result_row.urgency_level, "S")

    def test_record_dict_includes_diagnosis_summary(self):
        with self.Session() as db:
            diagnosis_service = DiagnosisService(
                repository=DiagnosisRepository(db),
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )
            diagnosis_response = diagnosis_service.handle_message(
                anonymous_token="summary-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )
            record_service = RecordService(db)
            record_service.create_record(
                anonymous_token="summary-token",
                diagnosis_result_id=diagnosis_response.result.id,
                house_area="厨房",
            )
            record_row, result_row = record_service.list_records(anonymous_token="summary-token")[0]

            payload = _record_to_dict(record_row, result_row)

            self.assertEqual(payload["secondary_category"], "circuit_trip")
            self.assertEqual(payload["urgency_level"], "S")
            self.assertIsInstance(payload["possible_causes"], list)
            self.assertIsInstance(payload["price_range"], str)

    def test_unsafe_input_is_blocked_and_written_to_content_safety_log(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )

            response = service.handle_message(
                anonymous_token="safety-token",
                text="我想用炸药处理墙面裂缝",
            )
            logs = repository.list_content_safety_logs(response.session.id)

            self.assertEqual(response.type, "blocked")
            self.assertEqual(response.error_code, "CONTENT_UNSAFE")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].result, "blocked")
            self.assertIn("炸药", logs[0].hit_categories)

    def test_unsafe_ai_output_is_blocked_and_written_to_content_safety_log(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=UnsafeDiagnosisLLM(),
                content_safety_service=local_content_safety_service(),
            )

            response = service.handle_message(
                anonymous_token="unsafe-output-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )
            logs = repository.list_content_safety_logs(response.session.id)

            self.assertEqual(response.type, "blocked")
            self.assertEqual(response.error_code, "OUTPUT_UNSAFE")
            output_logs = [log for log in logs if log.content_source == "ai_output"]
            self.assertEqual(len(output_logs), 1)
            self.assertEqual(output_logs[0].result, "blocked")
            self.assertIn("炸药", output_logs[0].hit_categories)

    def test_daily_full_diagnosis_quota_blocks_fourth_result(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )

            for _ in range(3):
                response = service.handle_message(
                    anonymous_token="quota-token",
                    text="插座发黑还冒烟了，现在还能继续用吗",
                )
                self.assertEqual(response.type, "result")

            blocked = service.handle_message(
                anonymous_token="quota-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )

            self.assertEqual(blocked.type, "blocked")
            self.assertEqual(blocked.error_code, "QUOTA_EXCEEDED")
            self.assertEqual(repository.get_today_full_diagnosis_count("quota-token"), 3)

    def test_result_feedback_is_upserted_by_result_and_anonymous_token(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )
            diagnosis_response = service.handle_message(
                anonymous_token="feedback-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )

            first = repository.upsert_feedback(
                result_id=diagnosis_response.result.id,
                session_id=diagnosis_response.session.id,
                anonymous_token="feedback-token",
                rating="useful",
                reason_tags=["risk_helpful"],
                comment="安全提醒有用",
            )
            second = repository.upsert_feedback(
                result_id=diagnosis_response.result.id,
                session_id=diagnosis_response.session.id,
                anonymous_token="feedback-token",
                rating="not_useful",
                reason_tags=["too_generic"],
                comment="建议太泛",
            )
            db.commit()
            feedback_rows = repository.list_feedback(diagnosis_response.result.id)

            self.assertEqual(first.id, second.id)
            self.assertEqual(len(feedback_rows), 1)
            self.assertEqual(feedback_rows[0].rating, "not_useful")
            self.assertEqual(feedback_rows[0].reason_tags, ["too_generic"])

    def test_feedback_api_saves_result_feedback(self):
        with self.Session() as db:
            repository = DiagnosisRepository(db)
            service = DiagnosisService(
                repository=repository,
                llm_adapter=None,
                content_safety_service=local_content_safety_service(),
            )
            diagnosis_response = service.handle_message(
                anonymous_token="feedback-api-token",
                text="插座发黑还冒烟了，现在还能继续用吗",
            )

            payload = FeedbackRequest(
                rating="useful",
                reason_tags=["risk_helpful", "clear_next_step"],
                comment="知道要断电了",
            )
            response = submit_feedback(
                result_id=diagnosis_response.result.id,
                payload=payload,
                x_anonymous_token="feedback-api-token",
                db=db,
            )

            self.assertEqual(response["rating"], "useful")
            self.assertEqual(response["reason_tags"], ["risk_helpful", "clear_next_step"])


if __name__ == "__main__":
    unittest.main()
