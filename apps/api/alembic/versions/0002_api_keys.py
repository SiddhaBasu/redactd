"""api_keys: SHA-256 hashes only, with per-key quotas

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = "0002"; down_revision = "0001"; branch_labels = None; depends_on = None

def upgrade():
    if "api_keys" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("api_keys",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("prefix", sa.String(12), nullable=False), sa.Column("name", sa.String(80), nullable=False),
        sa.Column("rate_per_minute", sa.Integer, nullable=True), sa.Column("monthly_chars", sa.Integer, nullable=True),
        sa.Column("created", sa.Float, nullable=False), sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_table("api_keys")
