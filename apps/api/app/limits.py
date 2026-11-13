"""Per-client rate limiting behind one interface: in-memory sliding window, or Redis fixed window (REDIS_URL set)."""
from __future__ import annotations
import threading, time
from collections import defaultdict, deque
from typing import Protocol
from .config import settings

class RateLimiter(Protocol):
    def allow(self, client: str, limit: int) -> bool: ...

class MemoryRateLimiter:
    def __init__(self, window: float = 60.0):
        self.hits: dict[str, deque] = defaultdict(deque); self.window = window; self._lock = threading.Lock()
    def allow(self, client: str, limit: int) -> bool:
        now = time.time()
        with self._lock:
            q = self.hits[client]
            while q and now - q[0] > self.window: q.popleft()
            if len(q) >= limit: return False
            q.append(now)
            if len(self.hits) > 50_000:      # bound memory: forget idle clients
                for k in [k for k, v in self.hits.items() if not v or now - v[-1] > self.window]: del self.hits[k]
            return True

class RedisRateLimiter:
    def __init__(self, client, window: int = 60):
        self.r = client; self.window = window
    def allow(self, client: str, limit: int) -> bool:
        key = f"redactd:rl:{client}:{int(time.time() // self.window)}"
        with self.r.pipeline() as p:
            p.incr(key); p.expire(key, self.window * 2); n, _ = p.execute()
        return int(n) <= limit

def make_limiter() -> RateLimiter:
    if settings.redis_url:
        import redis
        return RedisRateLimiter(redis.Redis.from_url(settings.redis_url))
    return MemoryRateLimiter()
