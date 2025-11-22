"""Configuration settings for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Apify
    APIFY_API_TOKEN: str

    # Anthropic Claude
    ANTHROPIC_API_KEY: str

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 10
    MAX_TOKENS_PER_REQUEST: int = 2048

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
