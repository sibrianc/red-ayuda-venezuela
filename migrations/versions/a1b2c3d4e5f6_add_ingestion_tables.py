"""add ingestion tables (source_records, ingested_events)

Revision ID: a1b2c3d4e5f6
Revises: 8d6f3b2c1a90
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "8d6f3b2c1a90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_slug", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("detail_url", sa.String(length=500), nullable=True),
        sa.Column("schema_version", sa.String(length=80), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_slug", "external_id", name="uq_source_records_origin"),
    )
    with op.batch_alter_table("source_records", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_source_records_source_slug"), ["source_slug"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_source_records_external_id"), ["external_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_source_records_content_hash"), ["content_hash"], unique=False
        )

    op.create_table(
        "ingested_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("source_slug", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=True),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("place", sa.String(length=240), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("depth_km", sa.Float(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_level", sa.String(length=20), nullable=True),
        sa.Column("tsunami", sa.Boolean(), nullable=False),
        sa.Column("felt_reports", sa.Integer(), nullable=True),
        sa.Column("significance", sa.Integer(), nullable=True),
        sa.Column("in_region", sa.Boolean(), nullable=False),
        sa.Column("detail_url", sa.String(length=500), nullable=True),
        sa.Column("attribution", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_ingested_events_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_ingested_events_longitude_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_slug", "external_id", name="uq_ingested_events_origin"),
    )
    with op.batch_alter_table("ingested_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_ingested_events_public_id"), ["public_id"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_source_slug"), ["source_slug"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_external_id"), ["external_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_event_type"), ["event_type"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_magnitude"), ["magnitude"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_occurred_at"), ["occurred_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_alert_level"), ["alert_level"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_significance"), ["significance"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_ingested_events_in_region"), ["in_region"], unique=False
        )


def downgrade():
    with op.batch_alter_table("ingested_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingested_events_in_region"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_significance"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_alert_level"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_occurred_at"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_magnitude"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_event_type"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_external_id"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_source_slug"))
        batch_op.drop_index(batch_op.f("ix_ingested_events_public_id"))
    op.drop_table("ingested_events")

    with op.batch_alter_table("source_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_source_records_content_hash"))
        batch_op.drop_index(batch_op.f("ix_source_records_external_id"))
        batch_op.drop_index(batch_op.f("ix_source_records_source_slug"))
    op.drop_table("source_records")
