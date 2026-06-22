from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


def discover_dotenv_paths(config_file: Path | None = None) -> list[Path]:
    current = (config_file or Path(__file__)).resolve()
    backend_dir = current.parents[2]
    project_dir = current.parents[3]
    workspace_dir = current.parents[4]
    return [
        backend_dir / ".env",
        project_dir / ".env",
        project_dir / "deploy" / ".env",
        workspace_dir / ".env",
    ]


def load_dotenv_files() -> None:
    for path in discover_dotenv_paths():
        if path.exists():
            load_dotenv(path, override=False)


load_dotenv_files()


@dataclass(slots=True)
class Settings:
    app_name: str = "AI 家庭维修诊断助手"
    app_version: str = "0.1.0"
    deployment_mode: str = os.getenv("DEPLOYMENT_MODE", "internal_demo")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://repair:repair@localhost:5432/repair_ai")
    primary_llm_provider: str = os.getenv("PRIMARY_LLM_PROVIDER", "deepseek")
    fallback_llm_provider: str = os.getenv("FALLBACK_LLM_PROVIDER", "qwen")
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    qwen_api_key: str = os.getenv("QWEN_API_KEY", "")
    qwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen-plus")
    content_safety_provider: str = os.getenv("CONTENT_SAFETY_PROVIDER", "local")
    content_safety_access_key: str = os.getenv("CONTENT_SAFETY_ACCESS_KEY", "")
    content_safety_secret_key: str = os.getenv("CONTENT_SAFETY_SECRET_KEY", "")
    content_safety_region: str = os.getenv("CONTENT_SAFETY_REGION", "ap-guangzhou")
    content_safety_timeout_seconds: int = int(os.getenv("CONTENT_SAFETY_TIMEOUT_SECONDS", "30"))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))


settings = Settings()
