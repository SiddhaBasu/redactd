"""Usage metering only. Document text, spans and values are NEVER stored."""
import hashlib, time
from sqlalchemy import create_engine, Column, Integer, String, Float, Index
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

def init_db():
    Base.metadata.create_all(engine)

def client_id(raw: str) -> str:
    return hashlib.sha256((settings.ip_salt + raw).encode()).hexdigest()[:16]

def record(client: str, endpoint: str, mode: str, chars: int, findings: int, ms: float):
    with Session() as s:
        s.add(UsageEvent(client=client, endpoint=endpoint, mode=mode, chars=chars, findings=findings, ms=ms))
        s.commit()
