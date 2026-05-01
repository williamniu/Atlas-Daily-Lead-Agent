"""Application configuration helpers."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Atlas Daily Lead Agent"
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    use_mock_data: bool = Field(default=True, validation_alias="USE_MOCK_DATA")

    insforge_database_url: Optional[str] = Field(
        default=None,
        validation_alias="INSFORGE_DATABASE_URL",
    )
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")

    x_bearer_token: Optional[str] = Field(default=None, validation_alias="X_BEARER_TOKEN")

    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="LLM_BASE_URL",
    )
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")

    alert_score_threshold: float = Field(
        default=75.0,
        validation_alias="ALERT_SCORE_THRESHOLD",
    )

    @property
    def effective_database_url(self) -> str:
        """Return the preferred database URL for the current runtime."""
        if self.insforge_database_url:
            return self.insforge_database_url
        if self.database_url:
            return self.database_url
        return "sqlite:///./local_dev.db"

    @property
    def has_x_api(self) -> bool:
        """Return whether X API credentials are configured."""
        return bool(self.x_bearer_token)

    @property
    def has_llm(self) -> bool:
        """Return whether LLM credentials are configured."""
        return bool(self.llm_api_key and self.llm_base_url and self.llm_model)

    @property
    def is_production(self) -> bool:
        """Return whether the app is running in production mode."""
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for application modules."""
    return Settings()


settings = get_settings()
