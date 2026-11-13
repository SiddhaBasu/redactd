"""Alembic environment. Run from apps/api:  DATABASE_URL=... alembic upgrade head"""
import os, sys
from alembic import context
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings
from app.db import Base, engine

target_metadata = Base.metadata

def run_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()

def run_online():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

run_offline() if context.is_offline_mode() else run_online()
