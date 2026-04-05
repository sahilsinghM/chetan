"""
Central configuration for ATOS.

Secrets are loaded from .env via pydantic-settings.
Non-secret trading parameters live in config/params.yaml.

Usage:
    from config.settings import settings
    print(settings.database_url)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://atos:secret@localhost:5432/atos_db"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Dhan API ──────────────────────────────────────────────
    dhan_client_id: str = ""
    dhan_access_token: str = ""

    # ── Anthropic (Phase 3) ───────────────────────────────────
    anthropic_api_key: str = ""

    # ── Telegram ──────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── TradingView (Phase 3) ─────────────────────────────────
    tradingview_username: str = ""
    tradingview_password: str = ""

    # ── App ───────────────────────────────────────────────────
    paper_trade_mode: bool = True
    environment: str = "development"
    log_level: str = "INFO"

    @field_validator("paper_trade_mode", mode="before")
    @classmethod
    def coerce_bool(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "no")
        return bool(v)


@lru_cache(maxsize=1)
def settings() -> Settings:
    """Return a cached Settings singleton. Import and call: settings()."""
    return Settings()


def load_params() -> dict:
    """Load non-secret trading parameters from config/params.yaml."""
    params_path = ROOT_DIR / "config" / "params.yaml"
    with open(params_path) as f:
        return yaml.safe_load(f)
