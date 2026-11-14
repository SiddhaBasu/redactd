import os
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

@dataclass(frozen=True)
class Settings:
    openmed_dir: str = os.getenv("OPENMED_DIR") or os.path.join(ROOT, "browser/models/openmed-small")
    gliner_dir: str = os.getenv("GLINER_DIR", os.path.join(ROOT, "browser/models/gliner"))
    distilled_dir: str = os.getenv("DISTILLED_DIR", os.path.join(ROOT, "browser/models/redactd-small"))
    model_threads: int = int(os.getenv("MODEL_THREADS", "0"))          # 0 = ONNX Runtime default
    max_concurrent_runs: int = int(os.getenv("MAX_CONCURRENT_RUNS", "2"))
    max_chars: int = int(os.getenv("MAX_CHARS", "1000000"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", "10000000"))  # binary formats (docx/pdf) before extraction
    sync_limit_chars: int = int(os.getenv("SYNC_LIMIT_CHARS", "200000"))  # bigger docs must use /v1/jobs
    preload: str = os.getenv("PRELOAD_MODES", "thorough")               # warm models at startup
    allowed_origins: list[str] = field(default_factory=lambda: os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
    # e.g. ^https://redactd-[a-z0-9-]+\.vercel\.app$ so Vercel preview deployments can call the API
    allowed_origin_regex: str = os.getenv("ALLOWED_ORIGIN_REGEX", "")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(ROOT, 'apps/api/redactd.db')}")
    redis_url: str = os.getenv("REDIS_URL", "")                        # set to share jobs + rate limits across instances
    rate_per_minute: int = int(os.getenv("RATE_PER_MINUTE", "60"))      # default for API keys without their own quota
    anon_rate_per_minute: int = int(os.getenv("ANON_RATE_PER_MINUTE", "20"))  # callers without an API key
    require_api_key: bool = os.getenv("REQUIRE_API_KEY", "0") == "1"
    job_ttl_s: int = int(os.getenv("JOB_TTL_S", "600"))             # how long a FINISHED job's result waits to be collected
    job_max_run_s: int = int(os.getenv("JOB_MAX_RUN_S", "3600"))    # how long a job may run before it is abandoned
    ip_salt: str = os.getenv("IP_SALT", "dev-salt-change-me")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    otel_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")   # traces are exported only when this is set

settings = Settings()
