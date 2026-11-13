"""Usage metering and API keys. Document text, spans and values are NEVER stored.

Tables (schema managed by Alembic, see apps/api/alembic):
  usage_events  one row per request: salted client hash, endpoint, mode, character count, finding count, duration
  api_keys      SHA-256 hash of each key (the key itself is shown once at creation and never stored), name, quotas
"""
import hashlib, secrets, time
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Index, func
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
Session = sessionmaker(engine)
Base = declarative_base()

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(Integer, primary_key=True)
    ts = Column(Float, nullable=False, default=time.time)
    client = Column(String(16), nullable=False)      # salted hash of IP / API key, not reversible
    endpoint = Column(String(32), nullable=False)
    mode = Column(String(16), nullable=False)
    chars = Column(Integer, nullable=False)
    findings = Column(Integer, nullable=False)
    ms = Column(Float, nullable=False)
    __table_args__ = (Index("ix_usage_client_ts", "client", "ts"),)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    key_hash = Column(String(64), nullable=False, unique=True)   # sha256 hex of the key; the key is never stored
    prefix = Column(String(12), nullable=False)                  # first characters, to recognise a key in a list
    name = Column(String(80), nullable=False)
    rate_per_minute = Column(Integer, nullable=True)             # None -> settings.rate_per_minute
    monthly_chars = Column(Integer, nullable=True)               # None -> unlimited
    created = Column(Float, nullable=False, default=time.time)
    revoked = Column(Boolean, nullable=False, default=False)

def init_db():
    """Create tables when they do not exist (dev / tests). Production runs `alembic upgrade head`."""
    Base.metadata.create_all(engine)

def client_id(raw: str) -> str:
    return hashlib.sha256((settings.ip_salt + raw).encode()).hexdigest()[:16]

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def create_api_key(name: str, rate_per_minute: int | None = None, monthly_chars: int | None = None) -> str:
    """Returns the key. This is the only time it exists in clear text."""
    key = "rk_" + secrets.token_urlsafe(32)
    with Session() as s:
        s.add(ApiKey(key_hash=hash_key(key), prefix=key[:8], name=name, rate_per_minute=rate_per_minute, monthly_chars=monthly_chars)); s.commit()
    return key

def find_api_key(key: str):
    with Session() as s:
        k = s.query(ApiKey).filter_by(key_hash=hash_key(key), revoked=False).first()
        return None if k is None else {"id": k.id, "rate_per_minute": k.rate_per_minute, "monthly_chars": k.monthly_chars}

def chars_this_month(client: str) -> int:
    t = time.gmtime(); start = time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0)) - time.timezone
    with Session() as s:
        return int(s.query(func.coalesce(func.sum(UsageEvent.chars), 0)).filter(UsageEvent.client == client, UsageEvent.ts >= start).scalar() or 0)

def record(client: str, endpoint: str, mode: str, chars: int, findings: int, ms: float):
    with Session() as s:
        s.add(UsageEvent(client=client, endpoint=endpoint, mode=mode, chars=chars, findings=findings, ms=ms))
        s.commit()
