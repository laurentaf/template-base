from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

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
    NVIDIA_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    OPENCODE_API_KEY: Optional[str] = None

    # App Config
    PROJECT_NAME: str = "ai-data-project"
    PHOENIX_URL: str = "http://localhost:6006"
    NIM_BRIDGE_URL: str = "http://localhost:8081/v1/chat/completions"

    # MCP Server URLs
    MCP_POSTGRES_URL: Optional[str] = None
    MCP_QDRANT_URL: Optional[str] = None
    MCP_GITHUB_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
