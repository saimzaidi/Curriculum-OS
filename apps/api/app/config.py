from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    secret: str = os.getenv("APP_SECRET", "development-only-change-this-secret-32")
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "100"))
    cors_origins: tuple[str, ...] = tuple(origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip())
    rag_anything_enabled: bool = os.getenv("RAG_ANYTHING_ENABLED", "false").lower() == "true"
    rag_anything_workdir: str = os.getenv("RAG_ANYTHING_WORKDIR", "data/rag-anything")
    rag_anything_api_key: str = os.getenv("RAG_ANYTHING_API_KEY", "")
    rag_anything_base_url: str = os.getenv("RAG_ANYTHING_BASE_URL", "")
    rag_anything_llm_model: str = os.getenv("RAG_ANYTHING_LLM_MODEL", "gpt-4o-mini")
    rag_anything_embedding_model: str = os.getenv("RAG_ANYTHING_EMBEDDING_MODEL", "text-embedding-3-large")


settings = Settings()


def validate_settings(current: Settings = settings) -> None:
    """Fail closed for the two settings that are unsafe outside local development."""
    if current.environment == "production" and (current.secret == "development-only-change-this-secret-32" or len(current.secret) < 32):
        raise RuntimeError("APP_SECRET must be a unique value of at least 32 characters in production.")
