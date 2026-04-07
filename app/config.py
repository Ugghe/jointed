import os
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Render uses postgres://; SQLAlchemy + psycopg3 expect postgresql+psycopg://."""
    if url.startswith("sqlite"):
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOINTED_", extra="ignore")

    database_url: str = "sqlite:///./data/jointed.db"
    puzzle_max_attempts: int = 5000
    min_words_per_tag: int = 4

    @model_validator(mode="after")
    def resolve_database_url(self) -> Self:
        raw = os.environ.get("DATABASE_URL") or self.database_url
        object.__setattr__(self, "database_url", normalize_database_url(raw))
        return self


settings = Settings()
