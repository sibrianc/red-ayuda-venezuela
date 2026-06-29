"""add incidents (priority situational points)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("source_slug", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("address_public", sa.String(length=300), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("situation_note", sa.String(length=500), nullable=True),
        sa.Column("source_name", sa.String(length=160), nullable=True),
        sa.Column("attribution", sa.String(length=240), nullable=True),
        sa.Column("in_region", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_slug", "external_id", name="uq_incidents_origin"),
    )
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_incidents_public_id"), ["public_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_incidents_source_slug"), ["source_slug"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_external_id"), ["external_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_severity"), ["severity"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_in_region"), ["in_region"], unique=False)
        batch_op.create_index(batch_op.f("ix_incidents_occurred_at"), ["occurred_at"], unique=False)


def downgrade():
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_incidents_occurred_at"))
        batch_op.drop_index(batch_op.f("ix_incidents_in_region"))
        batch_op.drop_index(batch_op.f("ix_incidents_status"))
        batch_op.drop_index(batch_op.f("ix_incidents_severity"))
        batch_op.drop_index(batch_op.f("ix_incidents_category"))
        batch_op.drop_index(batch_op.f("ix_incidents_external_id"))
        batch_op.drop_index(batch_op.f("ix_incidents_source_slug"))
        batch_op.drop_index(batch_op.f("ix_incidents_public_id"))
    op.drop_table("incidents")
