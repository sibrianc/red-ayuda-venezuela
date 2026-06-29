"""add person_records (published Person Finder / PFIF records)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "person_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("source_slug", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=240), nullable=False),
        sa.Column("given_name", sa.String(length=120), nullable=True),
        sa.Column("family_name", sa.String(length=120), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=20), nullable=True),
        sa.Column("last_known_location", sa.String(length=300), nullable=True),
        sa.Column("home_location", sa.String(length=300), nullable=True),
        sa.Column("person_status", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_minor", sa.Boolean(), nullable=False),
        sa.Column("attribution", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_slug", "external_id", name="uq_person_records_origin"),
    )
    with op.batch_alter_table("person_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_person_records_public_id"), ["public_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_person_records_source_slug"), ["source_slug"], unique=False)
        batch_op.create_index(batch_op.f("ix_person_records_external_id"), ["external_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_person_records_person_status"), ["person_status"], unique=False)
        batch_op.create_index(batch_op.f("ix_person_records_is_minor"), ["is_minor"], unique=False)


def downgrade():
    with op.batch_alter_table("person_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_person_records_is_minor"))
        batch_op.drop_index(batch_op.f("ix_person_records_person_status"))
        batch_op.drop_index(batch_op.f("ix_person_records_external_id"))
        batch_op.drop_index(batch_op.f("ix_person_records_source_slug"))
        batch_op.drop_index(batch_op.f("ix_person_records_public_id"))
    op.drop_table("person_records")
