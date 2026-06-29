"""add person match_key and corroboration

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-29

Clave de deduplicación/verificación entre fuentes para PersonRecord.
"""
from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("person_records") as batch:
        batch.add_column(sa.Column("match_key", sa.String(length=160), nullable=True))
        batch.add_column(
            sa.Column("corroboration", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_index("ix_person_records_match_key", ["match_key"])


def downgrade():
    with op.batch_alter_table("person_records") as batch:
        batch.drop_index("ix_person_records_match_key")
        batch.drop_column("corroboration")
        batch.drop_column("match_key")
