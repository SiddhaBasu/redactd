"""In-memory async jobs for large documents. Results are held in memory only, deleted on first read or after TTL.
For multiple API instances, swap this for Redis (same interface)."""
import threading, time, uuid
from .config import settings

class JobStore:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        jid = uuid.uuid4().hex
        with self._lock:
            self._gc()
            self._jobs[jid] = {"status": "queued", "created": time.time()}
        return jid

    def update(self, jid: str, **kw):
        with self._lock:
            if jid in self._jobs: self._jobs[jid].update(kw)

    def take(self, jid: str):
        """Return job state; if finished, remove it (results are delivered once)."""
        with self._lock:
            j = self._jobs.get(jid)
            if j and j["status"] in ("done", "error"):
                del self._jobs[jid]
            return j

    def _gc(self):
        now = time.time()
        for k in [k for k, v in self._jobs.items() if now - v["created"] > settings.job_ttl_s]:
            del self._jobs[k]

jobs = JobStore()
