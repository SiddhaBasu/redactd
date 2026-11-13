"""usage_events: metering only (no content columns exist, by design)

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = "0001"; down_revision = None; branch_labels = None; depends_on = None

def upgrade():
    if "usage_events" in sa.inspect(op.get_bind()).get_table_names(): return   # created by an older build via create_all
    op.create_table("usage_events",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("ts", sa.Float, nullable=False),
        sa.Column("client", sa.String(16), nullable=False), sa.Column("endpoint", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False), sa.Column("chars", sa.Integer, nullable=False),
        sa.Column("findings", sa.Integer, nullable=False), sa.Column("ms", sa.Float, nullable=False))
    op.create_index("ix_usage_client_ts", "usage_events", ["client", "ts"])

def downgrade():
    op.drop_index("ix_usage_client_ts", "usage_events"); op.drop_table("usage_events")
