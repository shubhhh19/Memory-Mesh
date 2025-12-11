"""Configuration for the AI Memory Layer service."""

import logging
import os
from functools import lru_cache
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from pydantic_settings.sources import EnvSettingsSource
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL

_OVERRIDES: dict[str, Any] = {}


class ImportanceWeights(BaseModel):
    recency: float = 0.4
    role: float = 0.2
    explicit: float = 0.4

    @field_validator("*")
    @classmethod
    def non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Importance weights must be non-negative")
        return value

    def normalized(self) -> "ImportanceWeights":
        total = self.recency + self.role + self.explicit
        if total == 0:
            return self
        return ImportanceWeights(
            recency=self.recency / total,
            role=self.role / total,
            explicit=self.explicit / total,
        )


_LOGGER = logging.getLogger("ai_memory_layer.config")

# Only load .env if MEMORY_DATABASE_URL is not already set (e.g., in Docker)
if not os.environ.get("MEMORY_DATABASE_URL"):
    try:  # pragma: no cover - filesystem guard
        load_dotenv(".env", override=False)
    except PermissionError:
        _LOGGER.warning("env_file_unreadable", extra={"path": ".env"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "memorymesh"
    environment: str = Field(default="local", description="Deployment environment name")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./memory_layer.db"
    )
    read_replica_urls: list[str] = Field(default_factory=list, alias="READ_REPLICA_URLS")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_pool_recycle: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE")

    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    embedding_provider: Literal["mock", "sentence_transformer", "google_gemini"] = Field(
        default="mock", alias="EMBEDDING_PROVIDER"
    )
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME"
    )
    max_results: int = Field(default=8, alias="MAX_RESULTS")
    importance_weights: ImportanceWeights = Field(
        default_factory=ImportanceWeights, alias="IMPORTANCE_WEIGHTS"
    )
    async_embeddings: bool = Field(default=False)
    embedding_job_poll_seconds: float = Field(default=1.0, alias="EMBEDDING_JOB_POLL_SECONDS")
    embedding_job_batch_size: int = Field(default=10, alias="EMBEDDING_JOB_BATCH_SIZE")
    embedding_job_max_attempts: int = Field(default=3, alias="EMBEDDING_JOB_MAX_ATTEMPTS")
    embedding_job_retry_backoff_seconds: float = Field(
        default=5.0, alias="EMBEDDING_JOB_RETRY_BACKOFF_SECONDS"
    )

    retention_max_age_days: int = Field(default=30, alias="RETENTION_MAX_AGE_DAYS")
    retention_importance_threshold: float = Field(
        default=0.35, alias="RETENTION_IMPORTANCE_THRESHOLD"
    )
    retention_delete_after_days: int = Field(default=90, alias="RETENTION_DELETE_AFTER_DAYS")
    retention_schedule_seconds: int = Field(default=86400, alias="RETENTION_SCHEDULE_SECONDS")
    retention_tenants: list[str] = Field(default_factory=lambda: ["*"], alias="RETENTION_TENANTS")

    healthcheck_timeout_seconds: float = Field(
        default=2.0, alias="HEALTHCHECK_TIMEOUT_SECONDS"
    )
    metrics_enabled: bool = Field(default=True, alias="ENABLE_METRICS")
    api_keys: list[str] = Field(default_factory=list, alias="API_KEYS")
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"], alias="ALLOWED_ORIGINS")
    global_rate_limit: str = Field(default="200/minute", alias="GLOBAL_RATE_LIMIT")
    tenant_rate_limit: str = Field(default="120/minute", alias="TENANT_RATE_LIMIT")
    request_timeout_seconds: int = Field(default=15, alias="REQUEST_TIMEOUT_SECONDS")
    request_max_bytes: int = Field(default=1_048_576, alias="REQUEST_MAX_BYTES")
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_max_items: int = Field(default=2000, alias="CACHE_MAX_ITEMS")
    cache_search_ttl_seconds: int = Field(default=60, alias="CACHE_SEARCH_TTL_SECONDS")
    cache_embedding_ttl_seconds: int = Field(default=3600, alias="CACHE_EMBEDDING_TTL_SECONDS")
    circuit_failure_threshold: int = Field(default=5, alias="CIRCUIT_FAILURE_THRESHOLD")
    circuit_recovery_seconds: int = Field(default=30, alias="CIRCUIT_RECOVERY_SECONDS")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    require_redis_in_production: bool = Field(default=True, alias="REQUIRE_REDIS_IN_PRODUCTION")
    health_embed_check_enabled: bool = Field(default=False, alias="HEALTH_EMBED_CHECK_ENABLED")
    readiness_embed_timeout_seconds: float = Field(default=3.0, alias="READINESS_EMBED_TIMEOUT_SECONDS")

    # JWT Authentication
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # OAuth Configuration
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    github_client_id: str | None = Field(default=None, alias="GITHUB_CLIENT_ID")
    github_client_secret: str | None = Field(default=None, alias="GITHUB_CLIENT_SECRET")
    oauth_redirect_url: str = Field(
        default="http://localhost:3000/auth/callback",
        alias="OAUTH_REDIRECT_URL"
    )


    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        class LenientEnvSettingsSource(EnvSettingsSource):
            """Let simple strings through so validators can parse them."""

            def decode_complex_value(self, field_name, field, value):
                try:
                    return super().decode_complex_value(field_name, field, value)
                except Exception:
                    return value

        return (
            init_settings,
            LenientEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("importance_weights", mode="before")
    @classmethod
    def _parse_importance_weights(cls, value: ImportanceWeights | dict[str, Any] | str):
        """Support comma/colon strings from .env files."""
        if isinstance(value, str):
            weights: dict[str, float] = {}
            for part in value.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" not in part:
                    raise ValueError("importance_weights must use key:value pairs")
                key, raw = part.split(":", 1)
                try:
                    weights[key.strip()] = float(raw)
                except ValueError:
                    raise ValueError("importance_weights values must be numeric") from None
            return weights
        return value

    @field_validator("async_embeddings", mode="before")
    @classmethod
    def _parse_async_embeddings(cls, value: bool | str) -> bool:
        """Convert string boolean values to actual booleans."""
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return value

    @field_validator("api_keys", mode="before")
    @classmethod
    def _split_api_keys(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("read_replica_urls", mode="before")
    @classmethod
    def _split_replicas(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("retention_tenants", mode="before")
    @classmethod
    def _split_tenants(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def sync_database_url(self) -> str:
        """Return sync-compatible database URL for Alembic/migrations."""
        url: URL = make_url(self.database_url)
        if url.drivername.endswith("+asyncpg"):
            url = url.set(drivername=url.drivername.replace("+asyncpg", "+psycopg"))
        elif url.drivername.endswith("+aiosqlite"):
            url = url.set(drivername="sqlite")
        return url.render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    
    # Validate JWT secret key security in production/staging
    if settings.environment in ("production", "prod", "staging"):
        if settings.jwt_secret_key == "change-me-in-production" or len(settings.jwt_secret_key) < 32:
            raise ValueError(
                f"JWT_SECRET_KEY must be set to a secure random value (minimum 32 characters) "
                f"in {settings.environment} environment. "
                f"Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
    elif settings.jwt_secret_key == "change-me-in-production":
        import warnings
        warnings.warn(
            "Using default JWT_SECRET_KEY. This is insecure for production. "
            "Set JWT_SECRET_KEY environment variable to a secure random value (minimum 32 characters).",
            UserWarning,
            stacklevel=2
        )
    
    if _OVERRIDES:
        return settings.model_copy(update=_OVERRIDES)
    return settings


def override_settings(**overrides: Any) -> Settings:
    """Apply runtime overrides (primarily for testing)."""
    global _OVERRIDES
    _OVERRIDES = overrides
    get_settings.cache_clear()
    return get_settings()


def reset_overrides() -> None:
    """Reset any runtime overrides."""
    global _OVERRIDES
    _OVERRIDES = {}
    get_settings.cache_clear()
