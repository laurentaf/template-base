from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _default_template_path() -> str:
    """Auto-detect template-base path: env var > git root > this file's parent."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return str(_PROJECT_ROOT)


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379"
    QDRANT_URL: str = "http://localhost:6333"
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    NVIDIA_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GITHUB_TOKEN: str | None = None
    OPENCODE_API_KEY: str | None = None
    PROJECT_NAME: str = "ai-data-project"
    EXECUTION_TIER: str = "development"
    SERVICE_MODE: str = "full"
    PHOENIX_URL: str = "http://localhost:6006"
    NIM_BRIDGE_URL: str = "http://localhost:8081/v1/chat/completions"
    MCP_POSTGRES_URL: str | None = None
    MCP_QDRANT_URL: str | None = None
    MCP_GITHUB_URL: str | None = None
    AUTO_GIT: bool = True
    AUTO_DOC: bool = True
    CONFIDENCE_THRESHOLD_CRITICAL: float = 0.98
    CONFIDENCE_THRESHOLD_IMPORTANT: float = 0.95
    CONFIDENCE_THRESHOLD_STANDARD: float = 0.90
    CONFIDENCE_THRESHOLD_ADVISORY: float = 0.80
    MAX_CONFIDENCE_RESEARCH_ROUNDS: int = 3
    EVOLVE_ENABLED: bool = True
    LTADE_TEMPLATE_PATH: str = ""
    EVOLVE_AUTO_APPLY: bool = False
    EVOLVE_MIN_CONFIDENCE: float = 0.7
    LEARNING_EMIT_ENABLED: bool = True
    EVOLVE_DAEMON_INTERVAL: int = 300
    EVOLVE_DAEMON_AUTO_ANALYZE: bool = True
    EVOLVE_DAEMON_AUTO_APPLY: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def template_path(self) -> str:
        return self.LTADE_TEMPLATE_PATH or _default_template_path()


settings = Settings()
