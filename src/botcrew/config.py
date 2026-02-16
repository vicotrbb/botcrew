from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with BOTCREW_ prefix."""

    # Database
    database_url: str = "postgresql+asyncpg://botcrew:botcrew@localhost:5432/botcrew"
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    # App
    debug: bool = False
    api_prefix: str = "/api/v1"
    # K8s
    k8s_namespace: str = "botcrew"

    model_config = SettingsConfigDict(env_prefix="BOTCREW_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
