from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://prefect:password@localhost:5433/prefect"
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
    EVOLVE_TEMPLATE_PATH: str = "E:\\projects\\template-base"
    EVOLVE_AUTO_APPLY: bool = False
    EVOLVE_MIN_CONFIDENCE: float = 0.7
    LEARNING_EMIT_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
