"""
Redis client and typed helpers.

Usage:
    from atos.core.cache import cache

    cache.set("key", "value", ttl=300)
    val = cache.get("key")
    cache.set_killswitch()
    cache.is_killswitch_active()
"""

from __future__ import annotations

import json
from typing import Any

import redis

from config.settings import settings

KILLSWITCH_KEY = "atos:killswitch"


class CacheClient:
    def __init__(self) -> None:
        self._client: redis.Redis = redis.from_url(
            settings().redis_url,
            decode_responses=True,
        )

    def ping(self) -> bool:
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._client.set(key, value, ex=ttl)

    def get_json(self, key: str) -> Any:
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._client.set(key, json.dumps(value), ex=ttl)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    # ── Killswitch ────────────────────────────────────────────

    def set_killswitch(self) -> None:
        """Activate the killswitch. Persists until manually cleared."""
        self._client.set(KILLSWITCH_KEY, "1")

    def clear_killswitch(self) -> None:
        """Deactivate the killswitch."""
        self._client.delete(KILLSWITCH_KEY)

    def is_killswitch_active(self) -> bool:
        """Return True if the killswitch has been activated."""
        return self._client.get(KILLSWITCH_KEY) == "1"


cache = CacheClient()
