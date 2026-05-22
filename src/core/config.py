from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Relational Database
    DATABASE_URL: str = "postgresql+psycopg://prefect:password@localhost:5433/prefect"

    # Vector Database
    QDRANT_URL: str = "http://localhost:6333"

    # Object Storage
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # LLM Providers
    NVIDIA_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GITHUB_TOKEN: str | None = None
    OPENCODE_API_KEY: str | None = None

    # App Config
    PROJECT_NAME: str = "ai-data-project"
    PHOENIX_URL: str = "http://localhost:6006"
    NIM_BRIDGE_URL: str = "http://localhost:8081/v1/chat/completions"
    OLLAMA_URL: str = "http://localhost:11434/v1"

    # MCP Server URLs
    MCP_POSTGRES_URL: str | None = None
    MCP_QDRANT_URL: str | None = None
    MCP_GITHUB_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
