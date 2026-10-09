from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = "BeautyFlow AI"
    api_prefix: str = "/api"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///beautyflow_ai.db")
    business_timezone: str = os.getenv("BUSINESS_TIMEZONE", "America/Sao_Paulo")
    business_open_hour: int = _int_env("BUSINESS_OPEN_HOUR", 9)
    business_close_hour: int = _int_env("BUSINESS_CLOSE_HOUR", 19)
    slot_interval_minutes: int = _int_env("SLOT_INTERVAL_MINUTES", 30)
    cors_origins: tuple[str, ...] = (
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
