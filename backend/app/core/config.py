"""Configuration settings for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Apify
    APIFY_API_TOKEN: str

    # Anthropic Claude (optional - not used for OpenAI-based orchestrator)
    ANTHROPIC_API_KEY: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None

    # Serper (for web search - optional)
    SERPER_API_KEY: Optional[str] = None

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 10
    MAX_TOKENS_PER_REQUEST: int = 2048

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Production
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list in production

    # ==========================================================================
    # MODEL CONFIGURATION - Change models in ONE place!
    # ==========================================================================
    # Agent model - used for orchestrator agent reasoning (needs strong reasoning)
    AGENT_MODEL: str = "gpt-4o-mini"  # gpt-5-mini doesn't work well for agentic tasks
    AGENT_TEMPERATURE: float = 0.3

    # Tool model - used for tool LLM calls (structured outputs)
    TOOL_MODEL: str = "gpt-4o-mini"  # Same as agent - reliable structured outputs
    TOOL_TEMPERATURE: float = 0.2

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
