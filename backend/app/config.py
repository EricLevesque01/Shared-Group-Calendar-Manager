"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings loaded from .env or environment."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/group_calendar"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
