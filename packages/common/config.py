from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "local-slack-rag-bot"
    environment: str = "local"
    log_level: str = "INFO"

    slack_bot_token: str | None = None
    slack_app_token: str | None = None
    slack_signing_secret: str | None = None
    slack_monitored_channel_ids: list[str] = Field(default_factory=list)

    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "gpt-oss-120b"
    lmstudio_api_key: str = "lm-studio"
    lmstudio_timeout_seconds: float = 300.0

    database_url: str = (
        "postgresql+psycopg://local_rag:local_rag_dev_password@localhost:5432/local_slack_rag"
    )
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "rag_chunks"

    embedding_base_url: str = "http://localhost:1234/v1"
    embedding_model: str = "Qwen3-Embedding-8B"
    reranker_base_url: str = "http://localhost:1234/v1"
    reranker_model: str = "Qwen3-Reranker-8B"
    reranker_fallback_model: str = "Qwen3-Reranker-4B"

    rag_top_k: int = 12
    rag_chunk_min_tokens: int = 500
    rag_chunk_max_tokens: int = 900
    rag_conceptual_chunk_max_tokens: int = 1500

    crawler_user_agent: str = "LocalRAGBot/1.0"
    crawler_respect_robots_txt: bool = True
    crawler_rate_limit_per_host_per_minute: int = 30
    crawler_max_concurrent_requests_per_host: int = 2
    crawler_max_pages_per_sync: int = 10000

    @field_validator("slack_monitored_channel_ids", mode="before")
    @classmethod
    def parse_csv_list(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
