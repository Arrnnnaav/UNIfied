from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    jwt_secret_key: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    operator_bootstrap_token: str | None = None

    # SQLite keeps the vertical slice runnable without Docker; production uses Postgres + pgvector.
    database_url: str = "sqlite:///./learning_platform.db"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str | None = "http://localhost:9000"
    storage_backend: str = "local"
    s3_bucket: str = "learning-platform"
    s3_access_key: str = "lpminio"
    s3_secret_key: str = "lpminiopass"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    local_embedding_model: str | None = None
    use_local_embeddings: bool = False
    embedding_dimension: int = 384

    curriculum_model: str | None = None
    enrichment_model: str | None = None
    concept_model: str | None = None
    assessment_model: str | None = None
    tutor_model: str | None = None
    local_llm_base_url: str | None = None
    local_llm_model: str = "llama3.1:8b"
    local_vision_model: str | None = None
    llm_timeout_seconds: float = 12.0
    label_model: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    max_upload_mb: int = 50
    async_ingestion: bool = False

    feature_tutor: bool = True
    feature_github_ingestion: bool = True
    feature_youtube_ingestion: bool = False
    feature_knowledge_map: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
