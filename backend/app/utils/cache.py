"""LRU + TTL 缓存工具，用于查询结果缓存与 Embedding 缓存"""
import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional

from ..config import get_settings

settings = get_settings()


class TTLCache:
    """线程安全的带 TTL 的 LRU 缓存"""

    def __init__(self, maxsize: int = 1024, default_ttl: int = 3600):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: "OrderedDict[str, tuple[Any, float]]" = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            value, expire_at = item
            if expire_at < time.time():
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            expire_at = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (value, expire_at)
            while len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# 全局单例
query_cache = TTLCache(maxsize=settings.QUERY_CACHE_MAXSIZE, default_ttl=settings.QUERY_CACHE_TTL_SECONDS)
embed_cache = TTLCache(maxsize=settings.EMBED_CACHE_MAXSIZE, default_ttl=86400 * 7)


def make_query_key(question: str, kb_ids: Optional[list[int]] = None) -> str:
    raw = f"{question}|{sorted(kb_ids) if kb_ids else 'all'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_embed_key(text: str, model: str) -> str:
    raw = f"{model}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
