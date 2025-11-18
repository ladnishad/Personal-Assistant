"""Application configuration management."""

from functools import lru_cache
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Environment variables take precedence over .env file
        env_prefix="",
    )

    # Application
    app_name: str = Field(default="LifeOS", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")

    # Security
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # MongoDB
    mongodb_url: str = Field(..., alias="MONGODB_URL")
    mongodb_db_name: str = Field(default="lifeos", alias="MONGODB_DB_NAME")
    mongodb_min_pool_size: int = Field(default=10, alias="MONGODB_MIN_POOL_SIZE")
    mongodb_max_pool_size: int = Field(default=50, alias="MONGODB_MAX_POOL_SIZE")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    # Google OAuth
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/integrations/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    # Microsoft OAuth
    microsoft_client_id: str = Field(default="", alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str = Field(default="", alias="MICROSOFT_CLIENT_SECRET")
    microsoft_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/integrations/microsoft/callback",
        alias="MICROSOFT_REDIRECT_URI",
    )
    microsoft_tenant_id: str = Field(default="common", alias="MICROSOFT_TENANT_ID")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_max_tokens: int = Field(default=4096, alias="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, alias="OPENAI_TEMPERATURE")

    # AgentMail
    agentmail_api_key: str = Field(default="", alias="AGENTMAIL_API_KEY")
    agentmail_webhook_secret: str = Field(default="", alias="AGENTMAIL_WEBHOOK_SECRET")

    # Background Jobs
    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    email_sync_interval_minutes: int = Field(
        default=15, alias="EMAIL_SYNC_INTERVAL_MINUTES"
    )
    calendar_sync_interval_minutes: int = Field(
        default=30, alias="CALENDAR_SYNC_INTERVAL_MINUTES"
    )
    reminder_check_interval_minutes: int = Field(
        default=5, alias="REMINDER_CHECK_INTERVAL_MINUTES"
    )

    # CORS
    cors_origins: Union[List[str], str] = Field(
        default="http://localhost:3000,http://localhost:5173", alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
