"""Configuration for the AI Memory Layer service."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_", env_file=".env", extra="ignore")

    app_name: str = "AI Memory Layer"
    environment: str = Field(default="local", description="Deployment environment name")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./memory_layer.db", alias="DATABASE_URL"
    )
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    embedding_provider: Literal["mock", "openai", "azure_openai"] = Field(
        default="mock", alias="EMBEDDING_PROVIDER"
    )
    max_results: int = Field(default=8, alias="MAX_RESULTS")
    importance_weights: ImportanceWeights = Field(
        default_factory=ImportanceWeights, alias="IMPORTANCE_WEIGHTS"
    )

    retention_max_age_days: int = Field(default=30, alias="RETENTION_MAX_AGE_DAYS")
    retention_importance_threshold: float = Field(
        default=0.35, alias="RETENTION_IMPORTANCE_THRESHOLD"
    )
    retention_delete_after_days: int = Field(default=90, alias="RETENTION_DELETE_AFTER_DAYS")

    healthcheck_timeout_seconds: float = Field(
        default=2.0, alias="HEALTHCHECK_TIMEOUT_SECONDS"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
