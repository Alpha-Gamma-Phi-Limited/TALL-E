import json
from dataclasses import dataclass
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


@dataclass
class CacheResult:
    hit: bool
    value: Any | None


class CacheClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._fallback: dict[str, str] = {}
        self._redis: Redis | None = None
        if self.settings.cache_enabled:
            try:
                self._redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
                self._redis.ping()
            except RedisError:
                self._redis = None

    def get_json(self, key: str) -> CacheResult:
        value: str | None = None
        try:
            if self._redis:
                value = self._redis.get(key)
            else:
                value = self._fallback.get(key)
        except RedisError:
            value = self._fallback.get(key)
        if value is None:
            return CacheResult(hit=False, value=None)
        return CacheResult(hit=True, value=json.loads(value))

    def set_json(self, key: str, payload: Any, ttl_seconds: int) -> None:
        encoded = json.dumps(payload, default=str)
        try:
            if self._redis:
                self._redis.setex(key, ttl_seconds, encoded)
            else:
                self._fallback[key] = encoded
        except RedisError:
            self._fallback[key] = encoded


cache_client = CacheClient()
