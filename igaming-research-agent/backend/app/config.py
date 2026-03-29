"""Application configuration loaded from environment.

TODO: Add stricter validation for required API keys in production.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_log_level: str = "INFO"
    database_url: str
    frontend_origin: str = "http://localhost:3000"

    scheduler_hour: int = 7
    scheduler_minute: int = 0

    serper_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    release_recent_window_hours: int = 72
    release_listing_fetch_timeout_seconds: int = 20
    release_fetch_timeout_seconds: int = 15
    release_fetch_max_retries: int = 2
    release_fetch_backoff_seconds: float = 1.0
    release_max_links_per_source: int = 40
    release_max_fetches_per_source: int = 80
    release_fetch_user_agent: str = "Mozilla/5.0 (compatible; iGamingResearchAgent/1.0)"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
