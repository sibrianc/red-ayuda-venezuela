"""add directory_entries (public services directory)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "directory_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("source_slug", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("address_public", sa.String(length=300), nullable=True),
        sa.Column("phone_public", sa.String(length=120), nullable=True),
        sa.Column("operator", sa.String(length=200), nullable=True),
        sa.Column("emergency", sa.Boolean(), nullable=False),
        sa.Column("capacity_text", sa.String(length=120), nullable=True),
        sa.Column("service_status", sa.String(length=20), nullable=False),
        sa.Column("in_region", sa.Boolean(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("attribution", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_slug", "external_id", name="uq_directory_entries_origin"),
    )
    with op.batch_alter_table("directory_entries", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_directory_entries_public_id"), ["public_id"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_source_slug"), ["source_slug"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_external_id"), ["external_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_category"), ["category"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_emergency"), ["emergency"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_service_status"), ["service_status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_directory_entries_in_region"), ["in_region"], unique=False
        )


def downgrade():
    with op.batch_alter_table("directory_entries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_directory_entries_in_region"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_service_status"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_emergency"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_category"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_external_id"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_source_slug"))
        batch_op.drop_index(batch_op.f("ix_directory_entries_public_id"))
    op.drop_table("directory_entries")
