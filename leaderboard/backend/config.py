"""Configuration for EPB leaderboard backend."""

import os
from typing import List


class Settings:
    """Leaderboard settings."""

    # API keys for submission
    API_KEYS: List[str] = os.getenv("EPB_API_KEYS", "").split(",")

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://epb.coursecorrect.org",
    ]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Database
    DATABASE_PATH: str = os.getenv("EPB_DB_PATH", "leaderboard/data/epb_leaderboard.db")

    @classmethod
    def validate_api_key(cls, api_key: str) -> bool:
        """Validate an API key."""
        if not cls.API_KEYS or cls.API_KEYS == [""]:
            # No API keys configured, allow all (for development)
            return True
        return api_key in cls.API_KEYS


settings = Settings()
