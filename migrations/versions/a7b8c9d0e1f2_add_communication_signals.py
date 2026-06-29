"""add communication_signals (no-comms zone alerts)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "communication_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("zone_label", sa.String(length=160), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("public_note", sa.Text(), nullable=True),
        sa.Column("reporter_contact_private", sa.String(length=160), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("communication_signals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_communication_signals_public_id"), ["public_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_communication_signals_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_communication_signals_source"), ["source"], unique=False)


def downgrade():
    with op.batch_alter_table("communication_signals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_communication_signals_source"))
        batch_op.drop_index(batch_op.f("ix_communication_signals_status"))
        batch_op.drop_index(batch_op.f("ix_communication_signals_public_id"))
    op.drop_table("communication_signals")
