"""Async jobs for large documents. Two stores behind one interface:

  MemoryJobStore  single API instance (default)
  RedisJobStore   several instances (REDIS_URL set); results live in Redis memory only, with a TTL

Contract (both stores): results are delivered ONCE by take() and then deleted. A finished result that is not
collected expires JOB_TTL_S after it FINISHED (not after the job was created: a 1 MB Thorough scan can take longer
than the collection window). A job still running after JOB_MAX_RUN_S is abandoned. peek() is non-destructive and never returns the result: it feeds the progress stream.
Job payloads hold spans (offsets and types), never the document text.
"""
from __future__ import annotations
import json, threading, time, uuid
from typing import Protocol
from .config import settings

PUBLIC = ("status", "stage", "pct", "error")

class JobStore(Protocol):
    def create(self) -> str: ...
    def update(self, jid: str, **kw) -> None: ...
    def peek(self, jid: str) -> dict | None: ...
    def take(self, jid: str) -> dict | None: ...

class MemoryJobStore:
    def __init__(self, ttl: float | None = None, max_run: float | None = None):
        self._jobs: dict[str, dict] = {}; self._lock = threading.Lock()
        self.ttl = ttl or settings.job_ttl_s; self.max_run = max_run or settings.job_max_run_s

    def create(self) -> str:
        jid = uuid.uuid4().hex
        with self._lock:
            self._gc()
            self._jobs[jid] = {"status": "queued", "stage": "Queued", "pct": 0, "created": time.time()}
        return jid

    def update(self, jid: str, **kw):
        with self._lock:
            if jid in self._jobs:
                self._jobs[jid].update(kw)
                if kw.get("status") in ("done", "error"): self._jobs[jid]["finished"] = time.time()

    def peek(self, jid: str):
        with self._lock:
            j = self._jobs.get(jid)
            return {k: j[k] for k in PUBLIC if k in j} if j else None

    def take(self, jid: str):
        """Return job state; if finished, remove it (results are delivered once)."""
        with self._lock:
            j = self._jobs.get(jid)
            if j and j["status"] in ("done", "error"): del self._jobs[jid]
            return {k: v for k, v in j.items() if k not in ("created", "finished")} if j else None

    def _gc(self):
        now = time.time()
        def expired(v):
            return now - v["finished"] > self.ttl if "finished" in v else now - v["created"] > self.max_run
        for k in [k for k, v in self._jobs.items() if expired(v)]: del self._jobs[k]

class RedisJobStore:
    """Same contract on Redis. One hash per job; take() uses a transaction so only one caller gets the result."""
    def __init__(self, client, ttl: float | None = None, max_run: float | None = None):
        self.r = client; self.ttl = int(ttl or settings.job_ttl_s); self.max_run = int(max_run or settings.job_max_run_s)
    def _k(self, jid): return f"redactd:job:{jid}"

    def create(self) -> str:
        jid = uuid.uuid4().hex
        self.r.hset(self._k(jid), mapping={"status": "queued", "stage": "Queued", "pct": "0"}); self.r.expire(self._k(jid), self.max_run)
        return jid

    def update(self, jid: str, **kw):
        if not self.r.exists(self._k(jid)): return
        self.r.hset(self._k(jid), mapping={k: json.dumps(v) if k == "result" else str(v) for k, v in kw.items()})
        if kw.get("status") in ("done", "error"): self.r.expire(self._k(jid), self.ttl)   # collection window starts now

    @staticmethod
    def _decode(h: dict) -> dict:
        out = {}
        for k, v in h.items():
            k = k.decode() if isinstance(k, bytes) else k; v = v.decode() if isinstance(v, bytes) else v
            out[k] = json.loads(v) if k == "result" else float(v) if k == "pct" else v
        return out

    def peek(self, jid: str):
        h = self.r.hgetall(self._k(jid))
        if not h: return None
        j = self._decode(h)
        return {k: j[k] for k in PUBLIC if k in j}

    def take(self, jid: str):
        key = self._k(jid)
        with self.r.pipeline() as p:
            while True:
                try:
                    p.watch(key); h = p.hgetall(key)
                    if not h: p.unwatch(); return None
                    j = self._decode(h)
                    if j.get("status") not in ("done", "error"): p.unwatch(); return j
                    p.multi(); p.delete(key); p.execute(); return j
                except Exception as e:  # noqa: BLE001
                    if type(e).__name__ != "WatchError": raise

def make_store() -> JobStore:
    if settings.redis_url:
        import redis
        return RedisJobStore(redis.Redis.from_url(settings.redis_url))
    return MemoryJobStore()

jobs: JobStore = make_store()
