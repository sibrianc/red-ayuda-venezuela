"""add situation_metrics (aggregate headline figures)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "situation_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("attribution", sa.String(length=240), nullable=True),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("situation_metrics", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_situation_metrics_metric_key"), ["metric_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_situation_metrics_verification_status"), ["verification_status"], unique=False)
        batch_op.create_index(batch_op.f("ix_situation_metrics_as_of"), ["as_of"], unique=False)


def downgrade():
    with op.batch_alter_table("situation_metrics", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_situation_metrics_as_of"))
        batch_op.drop_index(batch_op.f("ix_situation_metrics_verification_status"))
        batch_op.drop_index(batch_op.f("ix_situation_metrics_metric_key"))
    op.drop_table("situation_metrics")
