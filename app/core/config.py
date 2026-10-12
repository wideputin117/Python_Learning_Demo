"""Application settings, loaded from environment variables / .env.

Node equivalent: `dotenv` + a validated config object (e.g. with Zod).
Pydantic validates types at startup, so a bad value fails fast instead of at request time.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TriageDesk"
    environment: str = "development"
    debug: bool = False

    # Used from later milestones on (M2 database, M4 auth, M6 AI).
    database_url: str = "sqlite+aiosqlite:///./triagedesk.db"
    jwt_secret: str = "change-me"
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return one cached Settings instance (built on first call, then reused)."""
    return Settings()
