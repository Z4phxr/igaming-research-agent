"""Application configuration loaded from environment.

TODO: Add stricter validation for required API keys in production.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    frontend_origin: str = "http://localhost:3000"

    scheduler_hour: int = 7
    scheduler_minute: int = 0

    serper_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
