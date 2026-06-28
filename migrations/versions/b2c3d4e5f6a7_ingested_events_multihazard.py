"""add multi-hazard columns to ingested_events (GDACS support)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ingested_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hazard_code", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("severity_value", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("severity_text", sa.String(length=240), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(length=120), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_ingested_events_hazard_code"), ["hazard_code"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_country"), ["country"], unique=False
        )


def downgrade():
    with op.batch_alter_table("ingested_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingested_events_country"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_hazard_code"))
        batch_op.drop_column("country")
        batch_op.drop_column("severity_text")
        batch_op.drop_column("severity_value")
        batch_op.drop_column("hazard_code")
