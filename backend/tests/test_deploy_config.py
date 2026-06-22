import unittest
from pathlib import Path

import yaml


PROJECT_DIR = Path(__file__).resolve().parents[2]


class DeployConfigTest(unittest.TestCase):
    def test_compose_backend_uses_postgres_service_hostname(self):
        env_text = (PROJECT_DIR / "deploy" / "env.example").read_text(encoding="utf-8")

        self.assertIn("DATABASE_URL=postgresql+psycopg://repair:repair@postgres:5432/repair_ai", env_text)
        self.assertNotIn("DATABASE_URL=postgresql+psycopg://repair:repair@localhost:5432/repair_ai", env_text)

    def test_compose_waits_for_postgres_healthcheck(self):
        compose = yaml.safe_load((PROJECT_DIR / "deploy" / "docker-compose.yml").read_text(encoding="utf-8"))
        services = compose["services"]

        self.assertIn("healthcheck", services["postgres"])
        self.assertEqual(services["backend"]["depends_on"]["postgres"]["condition"], "service_healthy")


if __name__ == "__main__":
    unittest.main()
