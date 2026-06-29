"""add incident verification and provenance fields

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-29

Separa el estado operativo de la verificación. Permite publicar daños satelitales
como candidatos sin afirmar que hay personas atrapadas.
"""

from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("incidents") as batch:
        batch.add_column(
            sa.Column(
                "verification_status",
                sa.String(length=30),
                nullable=False,
                server_default="unverified",
            )
        )
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("source_date", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("confidence", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column(
                "location_precision",
                sa.String(length=30),
                nullable=False,
                server_default="approximate",
            )
        )
        batch.add_column(sa.Column("area_radius_m", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "people_trapped_status",
                sa.String(length=30),
                nullable=False,
                server_default="unknown",
            )
        )
        batch.add_column(sa.Column("people_trapped_count", sa.Integer(), nullable=True))
        batch.create_index("ix_incidents_verification_status", ["verification_status"])
        batch.create_index("ix_incidents_source_date", ["source_date"])
        batch.create_index("ix_incidents_people_trapped_status", ["people_trapped_status"])


def downgrade():
    with op.batch_alter_table("incidents") as batch:
        batch.drop_index("ix_incidents_people_trapped_status")
        batch.drop_index("ix_incidents_source_date")
        batch.drop_index("ix_incidents_verification_status")
        batch.drop_column("people_trapped_count")
        batch.drop_column("people_trapped_status")
        batch.drop_column("area_radius_m")
        batch.drop_column("location_precision")
        batch.drop_column("confidence")
        batch.drop_column("source_date")
        batch.drop_column("source_url")
        batch.drop_column("verification_status")
