from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"

    jwt_secret_key: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    operator_bootstrap_token: str | None = None

    # Browser origins allowed to call the API (React app on Vite dev server / Amplify). Comma separated.
    web_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Where `/` redirects to once the React app is hosted (e.g. https://main.xxx.amplifyapp.com).
    web_app_url: str | None = None

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

    # Spatial Context (Point & Ask) provider chain; see app/core/spatial/config.py and docs/SPATIAL_CONTEXT.md
    spatial_providers: str = "bedrock,nvidia,ollama,openrouter,openai,anthropic"
    bedrock_enabled: bool = False
    aws_region: str | None = None
    bedrock_model: str = "amazon.nova-lite-v1:0"
    bedrock_vision_model: str | None = "amazon.nova-lite-v1:0"
    openrouter_api_key: str | None = None
    openrouter_model: str = "qwen/qwen3-4b:free"
    openrouter_vision_model: str | None = "qwen/qwen2.5-vl-72b-instruct:free"
    nvidia_api_key: str | None = None
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_vision_model: str | None = "meta/llama-3.2-11b-vision-instruct"
    openai_vision_model: str | None = "gpt-4o-mini"
    anthropic_vision_model: str | None = "claude-sonnet-5"
    spatial_ocr: bool = True
    spatial_timeout_seconds: float = (
        30.0  # per provider; a slow cloud provider falls through to the next one
    )
    # Zero-install B2C guardrails
    spatial_anonymous_daily_limit: int = 20
    spatial_user_daily_limit: int = 200
    spatial_daily_cost_cap_usd: float = 0.10
    spatial_max_image_bytes: int = 4_000_000
    spatial_burst_per_minute: int = 10
    spatial_anonymous_retention_days: int = 30
    # Optional CPU speech ("Power mode" / self-host); browser Web Speech is the default in the extension
    spatial_stt_model: str = "base"
    spatial_stt_device: str = "cpu"
    spatial_tts: bool = True
    spatial_tts_voice: str = "alba"
    spatial_audio_idle_unload_seconds: int = 300
    spatial_force_ipv4: bool = False
    # When set, /api/audio/* is proxied to the audio-worker container instead of running torch in the API process.
    spatial_audio_url: str | None = None

    max_upload_mb: int = 50
    async_ingestion: bool = False

    feature_tutor: bool = True
    feature_github_ingestion: bool = True
    feature_youtube_ingestion: bool = False
    feature_knowledge_map: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
