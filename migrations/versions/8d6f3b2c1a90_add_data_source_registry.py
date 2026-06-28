"""add data source registry

Revision ID: 8d6f3b2c1a90
Revises: 17aafec3f9cb
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa


revision = "8d6f3b2c1a90"
down_revision = "17aafec3f9cb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("owner_name", sa.String(length=160), nullable=False),
        sa.Column("homepage_url", sa.String(length=500), nullable=False),
        sa.Column("documentation_url", sa.String(length=500), nullable=True),
        sa.Column(
            "source_kind",
            sa.Enum(
                "authoritative",
                "humanitarian",
                "partner",
                "research",
                "community",
                "referral",
                name="datasourcekind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "access_method",
            sa.Enum(
                "api",
                "feed",
                "public_document",
                "partner_export",
                "manual_import",
                "referral_only",
                name="datasourceaccess",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "authorization_status",
            sa.Enum(
                "proposed",
                "evaluating",
                "authorized_staging",
                "active",
                "suspended",
                "retired",
                name="datasourcestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("license_or_permission", sa.Text(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("categories", sa.Text(), nullable=False),
        sa.Column("contains_personal_data", sa.Boolean(), nullable=False),
        sa.Column(
            "maximum_data_class",
            sa.Enum(
                "P0",
                "P1",
                "R1",
                "R2",
                "S1",
                name="dataclassification",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("frequency_minutes", sa.Integer(), nullable=True),
        sa.Column("rate_limit_notes", sa.String(length=500), nullable=True),
        sa.Column("retention_policy", sa.Text(), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=80), nullable=True),
        sa.Column("secret_env_var", sa.String(length=120), nullable=True),
        sa.Column("internal_owner", sa.String(length=160), nullable=False),
        sa.Column("authorization_notes", sa.Text(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "frequency_minutes IS NULL OR frequency_minutes >= 1",
            name="ck_data_sources_frequency_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_data_sources_authorization_status"),
            ["authorization_status"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_data_sources_maximum_data_class"),
            ["maximum_data_class"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_data_sources_access_method"), ["access_method"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_data_sources_slug"), ["slug"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_data_sources_source_kind"), ["source_kind"], unique=False
        )


def downgrade():
    with op.batch_alter_table("data_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_data_sources_source_kind"))
        batch_op.drop_index(batch_op.f("ix_data_sources_slug"))
        batch_op.drop_index(batch_op.f("ix_data_sources_maximum_data_class"))
        batch_op.drop_index(batch_op.f("ix_data_sources_access_method"))
        batch_op.drop_index(batch_op.f("ix_data_sources_authorization_status"))
    op.drop_table("data_sources")
