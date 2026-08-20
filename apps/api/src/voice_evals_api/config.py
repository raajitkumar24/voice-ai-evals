from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOICE_EVALS_", env_file=".env", extra="ignore", case_sensitive=False
    )

    env: str = "development"
    database_url: str = "sqlite:///./voice-evals.db"
    redis_url: str = "redis://localhost:6379/0"
    public_api_url: str = "http://localhost:8000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    bootstrap_email: str = "admin@example.com"
    bootstrap_password: str = "change-me-before-production"
    encryption_key: str | None = None
    enable_test_provider: bool = False
    session_ttl_hours: int = 24
    max_conversations_per_run: int = 10_000
    max_evaluator_calls_per_run: int = 50_000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
