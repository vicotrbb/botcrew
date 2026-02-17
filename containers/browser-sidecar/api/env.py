"""Browser sidecar configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Browser sidecar settings.

    All settings can be overridden via environment variables with the
    BROWSER_ prefix. For example, BROWSER_PORT=8001.
    """

    port: int = 8001
    browser_headless: bool = True
    default_timeout: int = 30000  # milliseconds for Playwright operations
    viewport_width: int = 1280
    viewport_height: int = 720

    model_config = {"env_prefix": "BROWSER_"}


settings = Settings()
