import os
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

@dataclass(frozen=True)
class Settings:
    openmed_dir: str = os.getenv("OPENMED_DIR", os.path.join(ROOT, "browser/models/openmed-small"))
    gliner_dir: str = os.getenv("GLINER_DIR", os.path.join(ROOT, "browser/models/gliner"))
    model_threads: int = int(os.getenv("MODEL_THREADS", "0"))          # 0 = ONNX Runtime default
    max_concurrent_runs: int = int(os.getenv("MAX_CONCURRENT_RUNS", "2"))
    max_chars: int = int(os.getenv("MAX_CHARS", "1000000"))
    sync_limit_chars: int = int(os.getenv("SYNC_LIMIT_CHARS", "200000"))  # bigger docs must use /v1/jobs
    preload: str = os.getenv("PRELOAD_MODES", "thorough")               # warm models at startup
    allowed_origins: list[str] = field(default_factory=lambda: os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(ROOT, 'apps/api/redactd.db')}")
    rate_per_minute: int = int(os.getenv("RATE_PER_MINUTE", "60"))
    job_ttl_s: int = int(os.getenv("JOB_TTL_S", "600"))
    ip_salt: str = os.getenv("IP_SALT", "dev-salt-change-me")

settings = Settings()
