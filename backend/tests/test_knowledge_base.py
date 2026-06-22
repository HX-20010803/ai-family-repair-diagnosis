import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag_service import RagService
from app.services.taxonomy import SECONDARY_TO_PRIMARY


class KnowledgeBaseTest(unittest.TestCase):
    def test_all_mvp_categories_have_knowledge_entries(self):
        service = RagService()

        for secondary in SECONDARY_TO_PRIMARY:
            with self.subTest(secondary=secondary):
                knowledge = service.retrieve(secondary, "")
                self.assertEqual(knowledge["secondary_category"], secondary)
                self.assertGreaterEqual(len(knowledge["possible_causes"]), 1)
                self.assertIn("version", knowledge)


if __name__ == "__main__":
    unittest.main()
