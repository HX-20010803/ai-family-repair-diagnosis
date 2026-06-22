import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import discover_dotenv_paths


class ConfigTest(unittest.TestCase):
    def test_dotenv_discovery_includes_backend_project_deploy_and_workspace_files(self):
        project_dir = Path(__file__).resolve().parents[2]
        workspace_dir = project_dir.parent
        config_path = project_dir / "backend" / "app" / "core" / "config.py"

        paths = discover_dotenv_paths(config_path)

        self.assertIn(project_dir / "backend" / ".env", paths)
        self.assertIn(project_dir / ".env", paths)
        self.assertIn(project_dir / "deploy" / ".env", paths)
        self.assertIn(workspace_dir / ".env", paths)


if __name__ == "__main__":
    unittest.main()
